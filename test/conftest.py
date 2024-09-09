import pytest
from flask_sqlalchemy import SQLAlchemy


@pytest.fixture(scope="function")
def flask_config():
    from flask import Config
    c = Config('.')
    c.from_mapping({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "DEBUG": False,
    })
    return c


@pytest.fixture(scope="function")
def database(monkeypatch, flask_config):
    from aardvark import db
    mock_db = SQLAlchemy(model_class=db.Model)

    from aardvark import create_app
    app = create_app(config_override=flask_config)
    with app.app_context():
        mock_db.create_all()
        yield mock_db
        mock_db.drop_all()
