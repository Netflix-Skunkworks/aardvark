import pytest
from dynaconf import Dynaconf

import aardvark.config
from aardvark.config import settings
from aardvark import init_logging


init_logging()

@pytest.fixture(scope="session", autouse=True)
def set_test_settings():
    settings.configure(FORCE_ENV_FOR_DYNACONF="testing")


@pytest.fixture
def temp_config_file(tmp_path):
    config_path = tmp_path / "settings.yaml"
    return str(config_path)


@pytest.fixture(autouse=True, scope="function")
def patch_config(monkeypatch, tmp_path):
    db_path = tmp_path / "aardvark-test.db"
    db_uri = f"sqlite:///{db_path}"

    config = Dynaconf(
        envvar_prefix="AARDVARK",
        settings_files=[
            "test/settings.yaml",
        ],
        environments=True,
    )
    config.configure(FORCE_ENV_FOR_DYNACONF="testing")
    config.set("sqlalchemy_database_uri", db_uri)

    # Monkeypatch the actual config object so we don't poison it for future tests
    monkeypatch.setattr(aardvark.config, "settings", config)
    yield config
