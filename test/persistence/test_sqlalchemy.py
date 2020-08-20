import confuse
import datetime
import pytest

from sqlalchemy.exc import OperationalError

from aardvark.plugins import AardvarkPlugin
from aardvark.persistence import PersistencePlugin
from aardvark.persistence.sqlalchemy import SQLAlchemyPersistence

TEST_CONFIG = confuse.Configuration("aardvark_test", __name__)
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
def temp_sqlite_db_config(tmpdir_factory):
    db_path = tmpdir_factory.mktemp("aardvark").join("aardvark.db")
    db_uri = f"sqlite:///{db_path}"
    custom_config = confuse.Configuration("aardvark_test", __name__, read=False)
    custom_config["sqlalchemy"]["database_uri"] = db_uri
    return custom_config


def test_sqlalchemypersistence():
    sap = SQLAlchemyPersistence()
    assert isinstance(sap, AardvarkPlugin)
    assert isinstance(sap, PersistencePlugin)
    assert sap.config
    assert isinstance(sap.config, confuse.Configuration)


def test_sqlalchemypersistence_custom_config():
    custom_config = confuse.Configuration("aardvark", __name__)
    custom_config["test_key"] = "test_value"
    sap = SQLAlchemyPersistence(alternative_config=custom_config, initialize=False)
    assert isinstance(sap, AardvarkPlugin)
    assert isinstance(sap, PersistencePlugin)
    assert sap.config
    assert isinstance(sap.config, confuse.Configuration)
    assert sap.config["test_key"].get() == "test_value"


def test_init_db(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config, initialize=False)
    sap.init_db()
    assert sap.sa_engine
    assert sap.db_session
    from aardvark.persistence.sqlalchemy.models import AdvisorData, AWSIAMObject
    with sap.session_scope() as session:
        session.query(AdvisorData).all()
        session.query(AWSIAMObject).all()


def test_teardown_db(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config, initialize=False)
    sap.init_db()
    sap.teardown_db()
    from aardvark.persistence.sqlalchemy.models import AdvisorData, AWSIAMObject
    with sap.session_scope() as session:
        with pytest.raises(OperationalError):
            session.query(AdvisorData).all()
            session.query(AWSIAMObject).all()


def test_create_iam_object(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config)
    iam_object = sap.create_iam_object("arn:aws:iam::123456789012:role/SpongebobSquarepants", datetime.datetime.now())
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
            session=session
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
            session=session
        )


def test_get_or_create_iam_object(temp_sqlite_db_config):
    sap = SQLAlchemyPersistence(alternative_config=temp_sqlite_db_config)

    # create a new IAM object
    new_object = sap.get_or_create_iam_object("arn:aws:iam::123456789012:role/SquidwardTentacles")
    assert new_object.id
    assert new_object.arn == "arn:aws:iam::123456789012:role/SquidwardTentacles"
    object_id = new_object.id
    object_arn = new_object.arn

    # make the same call and make sure we get the same entry we created before
    retrieved_object = sap.get_or_create_iam_object("arn:aws:iam::123456789012:role/SquidwardTentacles")
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
