import datetime

from flask import current_app
from sqlalchemy import Column, Integer, TIMESTAMP
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship

from aardvark.models.sqlalchemy.utils import Base, db_session
from aardvark.utils.sqla_regex import String


class AWSIAMObject(Base):
    """
    Meant to model AWS IAM Object Access Advisor.
    """

    __tablename__ = "aws_iam_object"
    id = Column(Integer, primary_key=True)
    arn = Column(String(2048), nullable=True, index=True, unique=True)
    lastUpdated = Column(TIMESTAMP)
    usage = relationship(
        "AdvisorData",
        backref="item",
        cascade="all, delete, delete-orphan",
        foreign_keys="AdvisorData.item_id",
    )
    action_usage = relationship(
        "ActionData",
        backref="item",
        cascade="all, delete, delete-orphan",
        foreign_keys="ActionData.item_id",
    )

    @staticmethod
    def read(arn):
        item = AWSIAMObject.query.filter(AWSIAMObject.arn == arn).scalar()

        try:
            item = AWSIAMObject.query.filter(AWSIAMObject.arn == arn).scalar()
        except SQLAlchemyError as e:
            current_app.logger.error("Database exception: {}".format(e.message))

        return item

    @staticmethod
    def create(arn):
        item = AWSIAMObject(arn=arn, lastUpdated=datetime.datetime.utcnow())
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        return item

    @staticmethod
    def update(*args, **kwargs):
        pass

    @staticmethod
    def delete(*args, **kwargs):
        pass

    @staticmethod
    def create_or_update(*args, **kwargs):
        pass

    @staticmethod
    def get_or_create(arn, session=None):
        session = session if session else db_session
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
