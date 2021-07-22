from sqlalchemy import TIMESTAMP, BigInteger, Column, ForeignKey, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from aardvark.utils.sqla_regex import String

Base = declarative_base()


class AdvisorData(Base):
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
    item_id = Column(
        Integer, ForeignKey("aws_iam_object.id"), nullable=False, index=True
    )
    lastAuthenticated = Column(BigInteger)
    serviceName = Column(String(128), index=True)
    serviceNamespace = Column(String(64), index=True)
    lastAuthenticatedEntity = Column(Text)
    totalAuthenticatedEntities = Column(Integer)


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


class ActionData(Base):
    """
    Models action-specific data from sources other than Access Advisor,
    such as CloudTrail.
    """

    __tablename__ = "action_data"
    id = Column(Integer, primary_key=True)
    item_id = Column(
        Integer, ForeignKey("aws_iam_object.id"), nullable=False, index=True
    )
    lastAuthenticated = Column(BigInteger)
    serviceName = Column(String(128), index=True)
    serviceNamespace = Column(String(64), index=True)
