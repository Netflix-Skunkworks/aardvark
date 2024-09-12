import os
from typing import Any

import pytest
from dynaconf import Dynaconf

from aardvark.retrievers import RetrieverPlugin
from aardvark.retrievers.runner import RetrieverRunner


class RetrieverStub(RetrieverPlugin):
    def __init__(self, alternative_config: Dynaconf = None):
        super().__init__("retriever_stub", alternative_config=alternative_config)

    async def run(self, arn: str, data: dict[str, Any]) -> dict[str, Any]:
        data["retriever_stub"] = {"success": True}
        return data


class FailingRetriever(RetrieverPlugin):
    def __init__(self, alternative_config: Dynaconf = None):
        super().__init__("retriever_stub", alternative_config=alternative_config)

    async def run(self, arn: str, data: dict[str, Any]) -> dict[str, Any]:
        raise Exception("Oh no! Retriever failed")  # noqa


@pytest.fixture
def mock_retriever():
    return RetrieverStub()


@pytest.fixture
def mock_failing_retriever():
    return FailingRetriever()


@pytest.fixture
def runner():
    return RetrieverRunner()


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
