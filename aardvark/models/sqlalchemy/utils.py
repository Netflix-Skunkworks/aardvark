from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from aardvark.config import UPDATER_CONFIG

engine = create_engine(UPDATER_CONFIG.get("sqlalchemy_uri"))
db_session = scoped_session(
    sessionmaker(autocommit=True, autoflush=True, bind=engine)
)
Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    from aardvark.models.sqlalchemy import action_data, advisor_data, aws_iam_object

    Base.metadata.create_all(bind=engine)


def teardown_db():
    from aardvark.models.sqlalchemy import action_data, advisor_data, aws_iam_object

    Base.metadata.drop_all(bind=engine)