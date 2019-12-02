#ensure absolute import for python3
from __future__ import absolute_import

import datetime

from flask import current_app
from sqlalchemy import BigInteger, Column, Integer, Text, TIMESTAMP
import sqlalchemy.exc
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKey

from aardvark import db
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
        serviceName = serviceName[:128]
        serviceNamespace = serviceNamespace[:64]
        item = None
        try:
            item = AdvisorData.query.filter(AdvisorData.item_id == item_id).filter(AdvisorData.serviceNamespace ==
                                                                                   serviceNamespace).scalar()
        except sqlalchemy.exc.SQLAlchemyError as e:
            current_app.logger.error('Database error: {} item_id: {} serviceNamespace: {}'.format(e.args[0], item_id,
                                     serviceNamespace)) #exception.messsage not supported in py3 e.args[0] replacement

        if not item:
            item = AdvisorData(item_id=item_id,
                               lastAuthenticated=lastAuthenticated,
                               serviceName=serviceName,
                               serviceNamespace=serviceNamespace,
                               lastAuthenticatedEntity=lastAuthenticatedEntity,
                               totalAuthenticatedEntities=totalAuthenticatedEntities)
            db.session.add(item)
            return

        if lastAuthenticated > item.lastAuthenticated:
            item.lastAuthenticated = lastAuthenticated
            db.session.add(item)

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
                current_app.logger.warn('Previously seen object not accessed in the past 365 days '
                                        '(got null lastAuthenticated from AA). Setting to 0. '
                                        'Object {} service {} previous timestamp {}'.format(item.item_id, item.serviceName, item.lastAuthenticated))
                item.lastAuthenticated = 0
                db.session.add(item)
            else:
                current_app.logger.error("Received an older time than previously seen for object {} service {} ({la} < {ila})!".format(item.item_id,
                                                                                                                                       item.serviceName,
                                                                                                                                       la=lastAuthenticated,
                                                                                                                                       ila=item.lastAuthenticated))
