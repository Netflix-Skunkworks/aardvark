import pytest
from flask_sqlalchemy import SQLAlchemy


@pytest.fixture(scope="function")
def app_config():
    """Return a Flask configuration object for testing. The returned configuration is intended to be a good base for
    testing and can be customized for specific testing needs.
    """
    from flask import Config
    c = Config('.')
    c.from_mapping({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "DEBUG": False,
        "LOG_CFG": {'version': 1, 'handlers': []},  # silence logging
    })
    return c


@pytest.fixture(scope="function")
def mock_database(app_config):
    """Yield an instance of flask_sqlalchemy.SQLAlchemy associated with the base model class used in aardvark.model.
    This is almost certainly not safe for parallel/multi-threaded use.
    """
    from aardvark.app import db
    mock_db = SQLAlchemy(model_class=db.Model)

    from aardvark.app import create_app
    app = create_app(config_override=app_config)
    with app.app_context():
        mock_db.create_all()
        yield mock_db
        mock_db.drop_all()
