import datetime

import pytest
from dynaconf.utils import DynaconfDict
from sqlalchemy.exc import OperationalError

from aardvark.persistence import PersistencePlugin
from aardvark.persistence.sqlalchemy import SQLAlchemyPersistence
from aardvark.plugins import AardvarkPlugin

TIMESTAMP = datetime.datetime.now()
ADVISOR_DATA = {
    "arn:aws:iam::123456789012:role/SpongebobSquarepants": [
        {
            "LastAuthenticated": TIMESTAMP - datetime.timedelta(days=45),
            "ServiceName": "Krabby Patty",
            "ServiceNamespace": "krbpty",
            "LastAuthenticatedEntity": "arn:aws:iam::123456789012:role/SpongebobSquarepants",
            "TotalAuthenticatedEntities": 1,
        },
    ],
    "arn:aws:iam::123456789012:role/SheldonJPlankton": [
        {
            "LastAuthenticated": TIMESTAMP - datetime.timedelta(days=100),
            "ServiceName": "Chum Bucket",
            "ServiceNamespace": "chb",
            "LastAuthenticatedEntity": "arn:aws:iam::123456789012:role/SheldonJPlankton",
            "TotalAuthenticatedEntities": 1,
        },
    ],
}


@pytest.fixture(scope="function")
def temp_sqlite_db_config():
    db_uri = "sqlite:///:memory:"
    custom_config = DynaconfDict(
        {
            "sqlalchemy": {"database_uri": str(db_uri)},
        }
    )
    custom_config["sqlalchemy_database_uri"] = db_uri
    return custom_config


def test_sqlalchemypersistence():
    sap = SQLAlchemyPersistence()
    assert isinstance(sap, AardvarkPlugin)
    assert isinstance(sap, PersistencePlugin)
    assert sap.config


def test_sqlalchemypersistence_custom_config():
    custom_config = DynaconfDict({"test_key": "test_value"})
    custom_config["test_key"] = "test_value"
    sap = SQLAlchemyPersistence(alternative_config=custom_config, initialize=False)
    assert isinstance(sap, AardvarkPlugin)
    assert isinstance(sap, PersistencePlugin)
    assert sap.config
    assert sap.config["test_key"] == "test_value"


def test_init_db(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(
        alternative_config=temp_sqlite_db_config, initialize=False
    )
    sap.init_db()
    assert sap.sa_engine
    assert sap.session_factory
    from aardvark.persistence.sqlalchemy.models import AdvisorData, AWSIAMObject

    with sap.session_scope() as session:
        session.query(AdvisorData).all()
        session.query(AWSIAMObject).all()


def test_teardown_db(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(
        alternative_config=temp_sqlite_db_config, initialize=False
    )
    sap.init_db()
    sap.teardown_db()
    from aardvark.persistence.sqlalchemy.models import AdvisorData, AWSIAMObject

    with sap.session_scope() as session:
        with pytest.raises(OperationalError):
            session.query(AdvisorData).all()
            session.query(AWSIAMObject).all()


def test_create_iam_object(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config)
    iam_object = sap.create_iam_object(
        "arn:aws:iam::123456789012:role/SpongebobSquarepants", datetime.datetime.now()
    )
    assert iam_object.id
    assert iam_object.arn == "arn:aws:iam::123456789012:role/SpongebobSquarepants"


def test_create_or_update_advisor_data(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config)
    update_timestamp = datetime.datetime.now()
    original_timestamp = update_timestamp - datetime.timedelta(days=10)

    # Create advisor data record
    with sap.session_scope() as session:
        sap.create_or_update_advisor_data(
            1,
            original_timestamp,
            "Aardvark Test",
            "adv",
            "arn:aws:iam::123456789012:role/PatrickStar",
            999,
            session=session,
        )

    # Update advisor data record with new timestamp
    with sap.session_scope() as session:
        sap.create_or_update_advisor_data(
            1,
            update_timestamp,
            "Aardvark Test",
            "adv",
            "arn:aws:iam::123456789012:role/PatrickStar",
            999,
            session=session,
        )


def test_get_or_create_iam_object(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config)

    # create a new IAM object
    new_object = sap.get_or_create_iam_object(
        "arn:aws:iam::123456789012:role/SquidwardTentacles"
    )
    assert new_object.id
    assert new_object.arn == "arn:aws:iam::123456789012:role/SquidwardTentacles"
    object_id = new_object.id
    object_arn = new_object.arn

    # make the same call and make sure we get the same entry we created before
    retrieved_object = sap.get_or_create_iam_object(
        "arn:aws:iam::123456789012:role/SquidwardTentacles"
    )
    assert retrieved_object.id
    assert retrieved_object.arn == "arn:aws:iam::123456789012:role/SquidwardTentacles"
    assert retrieved_object.id == object_id
    assert retrieved_object.arn == object_arn


def test_store_role_data(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config)
    sap.store_role_data(ADVISOR_DATA)


def test_get_role_data(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config)
    sap.store_role_data(ADVISOR_DATA)
    role_data = sap.get_role_data()
    assert role_data["arn:aws:iam::123456789012:role/SpongebobSquarepants"]
    assert len(role_data["arn:aws:iam::123456789012:role/SpongebobSquarepants"]) == 1
    assert role_data["arn:aws:iam::123456789012:role/SheldonJPlankton"]
    assert len(role_data["arn:aws:iam::123456789012:role/SheldonJPlankton"]) == 1


def test_get_role_data_combine(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config)
    sap.store_role_data(ADVISOR_DATA)
    role_data = sap.get_role_data(combine=True)
    assert role_data["krbpty"]
    assert role_data["krbpty"]["USED_LAST_90_DAYS"]
    assert role_data["krbpty"]["serviceName"] == "Krabby Patty"
    assert role_data["chb"]
    assert not role_data["chb"]["USED_LAST_90_DAYS"]
    assert role_data["chb"]["serviceName"] == "Chum Bucket"
