import datetime
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, engine
from sqlalchemy import func as sa_func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker

from aardvark.exceptions import DatabaseException, CombineException
from aardvark.persistence import PersistencePlugin
from aardvark.persistence.sqlalchemy.models import AdvisorData, AWSIAMObject, Base
from aardvark.utils import Singleton

log = logging.getLogger("aardvark")


class SQLAlchemyPersistence(PersistencePlugin, metaclass=Singleton):
    sa_engine: engine = None
    db_session: scoped_session = None

    def init_db(self):
        self.sa_engine = create_engine(self.config["sqlalchemy"]["database_uri"].get())
        self.db_session = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.sa_engine,
                expire_on_commit=False,
            )
        )
        Base.query = self.db_session.query_property()

        Base.metadata.create_all(bind=self.sa_engine)

    def teardown_db(self):
        Base.metadata.drop_all(bind=self.sa_engine)

    def remove(self):
        self.db_session.remove()

    def create_iam_object(self, arn, lastUpdated):
        with self.db_session() as session:
            item = AWSIAMObject(arn=arn, lastUpdated=lastUpdated)
            session.add(item)
            session.commit()
            session.refresh(item)
        return item

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.db_session()
        try:
            yield session
            log.debug("committing SQLAlchemy DB session")
            session.commit()
        except Exception as e:
            log.debug("exception caught, rolling back session: %s", e)
            session.rollback()
            raise
        finally:
            log.debug("closing SQLAlchemy DB session")
            session.close()

    def _combine_results(self, access_advisor_data: Dict[str, Any]) -> Dict[str, Any]:
        _ = access_advisor_data.pop("page")
        _ = access_advisor_data.pop("count")
        _ = access_advisor_data.pop("total")
        usage = dict()
        for arn, services in access_advisor_data.items():
            for service in services:
                namespace = service.get("serviceNamespace")
                last_authenticated = service.get("lastAuthenticated")
                if namespace not in usage:
                    usage[namespace] = service
                else:
                    count_entities = (
                        usage[namespace]["totalAuthenticatedEntities"]
                        + service["totalAuthenticatedEntities"]
                    )
                    if last_authenticated > usage[namespace]["lastAuthenticated"]:
                        usage[namespace] = service
                    usage[namespace]["totalAuthenticatedEntities"] = count_entities

        for namespace, service in usage.items():
            last_authenticated = service["lastAuthenticated"]
            dt_last_authenticated = datetime.datetime.fromtimestamp(
                last_authenticated / 1e3
            )
            dt_starting = datetime.datetime.utcnow() - datetime.timedelta(days=90)
            usage[namespace]["USED_LAST_90_DAYS"] = dt_last_authenticated > dt_starting

        return usage

    def store_role_data(self, access_advisor_data: Dict[str, Any]):
        with self.session_scope() as session:
            if not access_advisor_data:
                log.warning(
                    "Cannot persist Access Advisor Data as no data was collected."
                )
                return

            arn_cache = {}
            for arn, data in access_advisor_data.items():
                if arn in arn_cache:
                    item = arn_cache[arn]
                else:
                    item = self.get_or_create_iam_object(arn)
                    arn_cache[arn] = item
                for service in data:
                    self.create_or_update_advisor_data(
                        item.id,
                        service["LastAuthenticated"],
                        service["ServiceName"],
                        service["ServiceNamespace"],
                        service.get("LastAuthenticatedEntity"),
                        service["TotalAuthenticatedEntities"],
                        session=session,
                    )

    def get_role_data(
        self,
        page: int = 0,
        count: int = 0,
        combine: bool = False,
        phrase: str = "",
        arns: Optional[List[str]] = None,
        regex: str = "",
    ) -> Dict[str, Any]:
        offset = (page - 1) * count if page else 0
        limit = count
        # default unfiltered query
        query = AWSIAMObject.query

        try:
            if phrase:
                query = query.filter(AWSIAMObject.arn.ilike("%" + phrase + "%"))

            if arns:
                query = query.filter(
                    sa_func.lower(AWSIAMObject.arn).in_([arn.lower() for arn in arns])
                )

            if regex:
                query = query.filter(AWSIAMObject.arn.regexp(regex))

            total = query.count()

            if offset:
                query = query.offset(offset)

            if limit:
                query = query.limit(limit)

            items = query.all()
        except Exception as e:
            raise DatabaseException("Could not retrieve roles from database: %s", e)

        if not items:
            items = AWSIAMObject.query.offset(offset).limit(limit).all()

        values = dict(page=page, total=total, count=len(items))
        for item in items:
            item_values = []
            for advisor_data in item.usage:
                item_values.append(
                    dict(
                        lastAuthenticated=advisor_data.lastAuthenticated,
                        serviceName=advisor_data.serviceName,
                        serviceNamespace=advisor_data.serviceNamespace,
                        lastAuthenticatedEntity=advisor_data.lastAuthenticatedEntity,
                        totalAuthenticatedEntities=advisor_data.totalAuthenticatedEntities,
                        lastUpdated=item.lastUpdated,
                    )
                )
            values[item.arn] = item_values

        if combine and total > len(items):
            raise CombineException(
                "Error: Please specify a count of at least {}.".format(total)
            )
        elif combine:
            return self._combine_results(values)

        return values

    def create_or_update_advisor_data(
        self,
        item_id,
        lastAuthenticated,
        serviceName,
        serviceNamespace,
        lastAuthenticatedEntity,
        totalAuthenticatedEntities,
        session=None,
    ):
        serviceName = serviceName[:128]
        serviceNamespace = serviceNamespace[:64]
        item = None
        try:
            item = (
                AdvisorData.query.filter(AdvisorData.item_id == item_id)
                .filter(AdvisorData.serviceNamespace == serviceNamespace)
                .scalar()
            )
        except SQLAlchemyError as e:
            log.error(
                "Database error: {} item_id: {} serviceNamespace: {}".format(
                    e.args[0], item_id, serviceNamespace
                )
            )  # exception.messsage not supported in py3 e.args[0] replacement

        if not item:
            item = AdvisorData(
                item_id=item_id,
                lastAuthenticated=lastAuthenticated,
                serviceName=serviceName,
                serviceNamespace=serviceNamespace,
                lastAuthenticatedEntity=lastAuthenticatedEntity,
                totalAuthenticatedEntities=totalAuthenticatedEntities,
            )
            session.add(item)
            return

        if lastAuthenticated > item.lastAuthenticated:
            item.lastAuthenticated = lastAuthenticated
            session.add(item)

        elif lastAuthenticated < item.lastAuthenticated:
            """
            lastAuthenticated is obtained by calling get_service_last_accessed_details() method of the boto3 iam client.
            When there is no AA data about a service, the lastAuthenticated key is missing from the returned dictionary.
            This is perfectly valid, either because the service in question was not accessed in the past 365 days or
            the entity granting  access to it was created recently enough that no AA data is available yet (it can take up to
            4 hours for this to happen).
            When this happens, the AccountToUpdate._get_job_results() method will set lastAuthenticated to 0.
            Usually we don't want to persist such an entity, with one exception: there's already a recorded, non-zero lastAuthenticated
            timestamp persisted for this item. That means the service was accessed at some point in time, but now more than 365 passed since
            the last access, so AA no longer returns a timestamp for it.
            """
            if lastAuthenticated == 0:
                log.warning(
                    "Previously seen object not accessed in the past 365 days "
                    "(got null lastAuthenticated from AA). Setting to 0. "
                    "Object {} service {} previous timestamp {}".format(
                        item.item_id, item.serviceName, item.lastAuthenticated
                    )
                )
                item.lastAuthenticated = 0
                session.add(item)
            else:
                log.error(
                    "Received an older time than previously seen for object {} service {} ({la} < {ila})!".format(
                        item.item_id,
                        item.serviceName,
                        la=lastAuthenticated,
                        ila=item.lastAuthenticated,
                    )
                )

    def get_or_create_iam_object(self, arn):
        with self.session_scope() as session:
            item = session.query(AWSIAMObject).filter(AWSIAMObject.arn == arn).scalar()

            added = False
            if not item:
                item = AWSIAMObject(arn=arn, lastUpdated=datetime.datetime.utcnow())
                added = True
            else:
                item.lastUpdated = datetime.datetime.utcnow()
            session.add(item)

            # we only need a refresh if the object was created
            if added:
                session.commit()
                session.refresh(item)
            return item
