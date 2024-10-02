from __future__ import annotations

import datetime

from flask import current_app
from sqlalchemy import BigInteger, Column, Integer, Text, TIMESTAMP
import sqlalchemy.exc
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKey

from aardvark.app import db
from aardvark.utils.sqla_regex import String


class AWSIAMObject(db.Model):
    """
    Meant to model AWS IAM Object Access Advisor.
    """
    __tablename__ = "aws_iam_object"
    id = Column(Integer, primary_key=True)
    arn = Column(String(2048), nullable=True, index=True, unique=True)
    lastUpdated = Column(TIMESTAMP)
    usage = relationship("AdvisorData", backref="item", cascade="all, delete, delete-orphan",
                         foreign_keys="AdvisorData.item_id")

    @staticmethod
    def get_or_create(arn):
        item = AWSIAMObject.query.filter(AWSIAMObject.arn == arn).scalar()

        added = False
        try:
            item = AWSIAMObject.query.filter(AWSIAMObject.arn == arn).scalar()
        except sqlalchemy.exc.SQLAlchemyException as e:
            current_app.logger.error('Database exception: {}'.format(e.message))

        if not item:
            item = AWSIAMObject(arn=arn, lastUpdated=datetime.datetime.utcnow())
            added = True
        else:
            item.lastUpdated = datetime.datetime.utcnow()
        db.session.add(item)

        # we only need a refresh if the object was created
        if added:
            db.session.commit()
            db.session.refresh(item)
        return item


class AdvisorData(db.Model):
    """
    Models certain IAM Access Advisor Data fields.

    {
      "totalAuthenticatedEntities": 1,
      "lastAuthenticatedEntity": "arn:aws:iam::XXXXXXXX:role/name",
      "serviceName": "Amazon Simple Systems Manager",
      "lastAuthenticated": 1489176000000,
      "serviceNamespace": "ssm"
    }
    """
    __tablename__ = "advisor_data"
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("aws_iam_object.id"), nullable=False, index=True)
    lastAuthenticated = Column(BigInteger)
    serviceName = Column(String(128), index=True)
    serviceNamespace = Column(String(64), index=True)
    lastAuthenticatedEntity = Column(Text)
    totalAuthenticatedEntities = Column(Integer)

    @staticmethod
    def create_or_update(item_id, lastAuthenticated, serviceName, serviceNamespace, lastAuthenticatedEntity,
                         totalAuthenticatedEntities):
        # Truncate service name and namespace to make sure they fit in our DB fields
        serviceName = serviceName[:128]
        serviceNamespace = serviceNamespace[:64]

        # Query the database for an existing entry that matches this item ID and service namespace. If there is none,
        # instantiate an empty AdvisorData
        item: AdvisorData | None = None
        try:
            item = db.session.query(AdvisorData).filter(
                AdvisorData.item_id == item_id,
                AdvisorData.serviceNamespace == serviceNamespace,
            ).scalar()
        except sqlalchemy.exc.SQLAlchemyError as e:
            current_app.logger.error(
                'Database error: %s item_id: %s serviceNamespace: %s',
                str(e),
                item_id,
                serviceNamespace
            )

        if not item:
            item = AdvisorData()

        # Save existing lastAuthenticated timestamp for later comparison
        existingLastAuthenticated = item.lastAuthenticated or 0

        # Set all fields to the provided values. SQLAlchemy will only mark the model instance as modified if the actual
        # values have changed, so this will be a no-op if the values are all the same.
        item.item_id = item_id
        item.lastAuthenticated = lastAuthenticated
        item.lastAuthenticatedEntity = lastAuthenticatedEntity
        item.serviceName = serviceName
        item.serviceNamespace = serviceNamespace
        item.totalAuthenticatedEntities = totalAuthenticatedEntities

        # When there is no AA data about a service, the lastAuthenticated key is missing from the returned dictionary.
        # This is perfectly valid, either because the service in question was not accessed in the past 365 days or
        # the entity granting  access to it was created recently enough that no AA data is available yet (it can take
        # up to 4 hours for this to happen).
        #
        # When this happens, the AccountToUpdate._get_job_results() method will set lastAuthenticated to 0. Usually
        # we don't want to persist such an entity, with one exception: there's already a recorded, non-zero
        # lastAuthenticated timestamp persisted for this item. That means the service was accessed at some point in
        # time, but now more than 365 passed since the last access, so AA no longer returns a timestamp for it.
        if lastAuthenticated < existingLastAuthenticated:
            if lastAuthenticated == 0:
                current_app.logger.info(
                    'Previously seen object not accessed in the past 365 days (got null lastAuthenticated from AA). '
                    'Setting to 0. Object %s service %s previous timestamp %d',
                    item.item_id,
                    item.serviceName,
                    item.lastAuthenticated
                )
            else:
                current_app.logger.warning(
                    "Received an older time than previously seen for object %s service %s (%d < %d)!",
                    item.item_id,
                    item.serviceName,
                    lastAuthenticated,
                    existingLastAuthenticated
                )
                item.lastAuthenticated = existingLastAuthenticated

        # Add the updated item to the session so it gets committed with everything else
        db.session.add(item)
