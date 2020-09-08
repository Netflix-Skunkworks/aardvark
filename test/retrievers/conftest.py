import os
import pytest
from typing import Any, Dict

import confuse

from aardvark.retrievers import RetrieverPlugin
from aardvark.retrievers.runner import RetrieverRunner


class RetrieverStub(RetrieverPlugin):
    def __init__(self, alternative_config: confuse.Configuration = None):
        super().__init__("retriever_stub", alternative_config=alternative_config)

    async def run(self, arn: str, data: Dict[str, Any]) -> Dict[str, Any]:
        data["retriever_stub"] = {"success": True}
        return data


class FailingRetriever(RetrieverPlugin):
    def __init__(self, alternative_config: confuse.Configuration = None):
        super().__init__("retriever_stub", alternative_config=alternative_config)

    async def run(self, arn: str, data: Dict[str, Any]) -> Dict[str, Any]:
        raise Exception("Oh no! Retriever failed")


@pytest.fixture(scope="function")
def mock_retriever(mock_config):
    return RetrieverStub(alternative_config=mock_config)


@pytest.fixture(scope="function")
def mock_failing_retriever(mock_config):
    return FailingRetriever(alternative_config=mock_config)


@pytest.fixture(scope="function")
def runner(mock_config):
    return RetrieverRunner(alternative_config=mock_config)


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
