import datetime
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

import confuse
from sqlalchemy import create_engine, engine
from sqlalchemy import func as sa_func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker, Session

from aardvark.exceptions import CombineException, DatabaseException
from aardvark.persistence import PersistencePlugin
from aardvark.persistence.sqlalchemy.models import AdvisorData, AWSIAMObject, Base

log = logging.getLogger("aardvark")
session_type = Union[scoped_session, Session]


class SQLAlchemyPersistence(PersistencePlugin):
    sa_engine: engine = None
    session_factory: sessionmaker = None

    def __init__(
        self, alternative_config: confuse.Configuration = None, initialize: bool = True
    ):
        super().__init__(alternative_config=alternative_config)
        if initialize:
            self.init_db()

    def init_db(self):
        self.sa_engine = create_engine(self.config["sqlalchemy"]["database_uri"].get())
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.sa_engine,
            expire_on_commit=False,
        )
        session = self._create_session()
        Base.query = session.query_property()

        Base.metadata.create_all(bind=self.sa_engine)

    def _create_session(self) -> scoped_session:
        return scoped_session(self.session_factory)

    def teardown_db(self):
        Base.metadata.drop_all(bind=self.sa_engine)

    def create_iam_object(
        self, arn: str, last_updated: datetime.datetime
    ) -> AWSIAMObject:
        with self.session_scope() as session:
            item = AWSIAMObject(arn=arn, lastUpdated=last_updated)
            session.add(item)
        return item

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session: session_type = self._create_session()
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
        access_advisor_data.pop("page")
        access_advisor_data.pop("count")
        access_advisor_data.pop("total")
        usage: Dict[str, Dict] = dict()
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
            if isinstance(last_authenticated, int):
                dt_last_authenticated = datetime.datetime.fromtimestamp(
                    last_authenticated / 1e3
                )
            elif isinstance(last_authenticated, str):
                dt_last_authenticated = datetime.datetime.strptime(
                    last_authenticated, "%Y-%m-%d %H:%M:%S.%f"
                )
            else:
                dt_last_authenticated = last_authenticated

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
        session: session_type = None,
    ) -> Dict[str, Any]:
        offset = (page - 1) * count if page else 0
        limit = count
        session = session or self._create_session()
        # default unfiltered query
        query = session.query(AWSIAMObject)

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
            items = session.query(AWSIAMObject).offset(offset).limit(limit).all()

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
        item_id: int,
        last_authenticated: int,
        service_name: str,
        service_namespace: str,
        last_authenticated_entity: str,
        total_authenticated_entities: int,
        session: session_type = None,
    ):
        session = session or self._create_session()
        service_name = service_name[:128]
        service_namespace = service_namespace[:64]
        item = None
        try:
            item = (
                session.query(AdvisorData)
                .filter(AdvisorData.item_id == item_id)
                .filter(AdvisorData.serviceNamespace == service_namespace)
                .scalar()
            )
        except SQLAlchemyError as e:
            log.error(
                f"Database error: {e} item_id: {item_id} serviceNamespace: {service_namespace}"
            )

        if not item:
            item = AdvisorData(
                item_id=item_id,
                lastAuthenticated=last_authenticated,
                serviceName=service_name,
                serviceNamespace=service_namespace,
                lastAuthenticatedEntity=last_authenticated_entity,
                totalAuthenticatedEntities=total_authenticated_entities,
            )
            try:
                session.add(item)
            except SQLAlchemyError as e:
                log.error(f"failed to add AdvisorData item to session: {e}")
                raise
            return

        # sqlite will return a string for item.lastAuthenticated, so we parse that into a datetime
        if isinstance(item.lastAuthenticated, str):
            ts = datetime.datetime.strptime(
                item.lastAuthenticated, "%Y-%m-%d %H:%M:%S.%f"
            )
        else:
            ts = item.lastAuthenticated

        if last_authenticated > ts:
            item.lastAuthenticated = last_authenticated
            try:
                session.add(item)
            except SQLAlchemyError as e:
                log.error(f"failed to add AdvisorData item to session: {e}")
                raise

        elif last_authenticated < ts:
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
            if last_authenticated == 0:
                log.warning(
                    "Previously seen object not accessed in the past 365 days "
                    "(got null lastAuthenticated from AA). Setting to 0. "
                    f"Object {item.item_id} service {item.serviceName} previous timestamp {item.lastAuthenticated}"
                )
                item.lastAuthenticated = 0
                try:
                    session.add(item)
                except SQLAlchemyError as e:
                    log.error(f"failed to add AdvisorData item to session: {e}")
                    raise
            else:
                log.error(
                    f"Received an older time than previously seen for object {item.item_id} service {item.serviceName} ({last_authenticated} < {item.lastAuthenticated})!"
                )

    def get_or_create_iam_object(self, arn: str):
        with self.session_scope() as session:
            try:
                item = (
                    session.query(AWSIAMObject).filter(AWSIAMObject.arn == arn).scalar()
                )
            except SQLAlchemyError as e:
                log.error(f"failed to retrieve IAM object: {e}")
                raise

            added = False
            if not item:
                item = AWSIAMObject(arn=arn, lastUpdated=datetime.datetime.utcnow())
                added = True
            else:
                item.lastUpdated = datetime.datetime.utcnow()

            try:
                session.add(item)
            except SQLAlchemyError as e:
                log.error(f"failed to add AWSIAMObject item to session: {e}")
                raise

            # we only need a refresh if the object was created
            if added:
                try:
                    session.commit()
                    session.refresh(item)
                except SQLAlchemyError as e:
                    log.error(f"failed to create IAM object: {e}")
                    raise
            return item
