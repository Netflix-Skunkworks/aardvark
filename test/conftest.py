import confuse
import pytest

import aardvark.configuration


@pytest.fixture(scope="function")
def temp_config_file(tmpdir_factory):
    config_path = tmpdir_factory.mktemp("aardvark").join("config.yaml")
    return str(config_path)


@pytest.fixture(scope="function", autouse=True)
def patch_config(monkeypatch):
    # Monkeypatch the actual config object so we don't poison it for future tests
    monkeypatch.setattr(
        aardvark.configuration, "CONFIG", confuse.Configuration("aardvark-test")
    )


@pytest.fixture(scope="function", autouse=True)
def mock_config():
    config = confuse.Configuration("aardvark-test")
    config["updater"]["num_threads"] = 1
    config["swag"]["opts"] = {}
    config["swag"]["filter"] = ""
    config["swag"]["service_enabled_requirement"] = ""
    return config
