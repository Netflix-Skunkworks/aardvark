from aardvark import db
import datetime
from flask import current_app
from sqlalchemy import BigInteger, Column, Integer, Text, TIMESTAMP
import sqlalchemy.exc
from aardvark.utils.sqla_regex import String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKey


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
        try:
            item = AdvisorData.query.filter(AdvisorData.item_id == item_id).filter(AdvisorData.serviceNamespace ==
                                                                                   serviceNamespace).scalar()
        except sqlalchemy.exc.SQLAlchemyError as e:
            current_app.logger.error('Database error: {}'.format(e.message))

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
