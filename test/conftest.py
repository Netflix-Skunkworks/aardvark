import pytest
from flask_sqlalchemy import SQLAlchemy


@pytest.fixture(scope="function")
def app_config():
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
def mock_database(monkeypatch, app_config):
    from aardvark import db
    mock_db = SQLAlchemy(model_class=db.Model)

    from aardvark import create_app
    app = create_app(config_override=app_config)
    with app.app_context():
        mock_db.create_all()
        yield mock_db
        mock_db.drop_all()
