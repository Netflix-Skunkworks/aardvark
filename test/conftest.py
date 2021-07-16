import pytest
from dynaconf.utils import DynaconfDict

import aardvark.configuration


@pytest.fixture
def temp_config_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    return str(config_path)


@pytest.fixture(autouse=True)
def patch_config(monkeypatch, tmp_path):
    db_path = tmp_path / "aardvark-test.db"
    db_uri = f"sqlite:///{db_path}"
    log_path = tmp_path / "aardvark-test.log"

    config = DynaconfDict(
        {
            "sqlalchemy": {
                "database_uri": str(db_uri)
            },
            "logging": {
                "handlers": {
                    "file": {
                        "filename": str(log_path)
                    }
                }
            },
            "updater": {
                "num_threads": 1
            },
            "swag": {
                "opts": {}
            },
            "aws": {
                "rolename": "test",
                "region": "test",
                "arn_partition": "test",
            },
        }
    )

    # Monkeypatch the actual config object so we don't poison it for future tests
    monkeypatch.setattr(aardvark.configuration, "settings", config)
    yield config


@pytest.fixture
def mock_config(patch_config):
    patch_config["updater"]["num_threads"] = 1
    patch_config["swag"]["opts"] = {}
    patch_config["swag"]["filter"] = ""
    patch_config["swag"]["service_enabled_requirement"] = ""
    return patch_config
