import pytest

from aardvark.retrievers import RetrieverPlugin


def test_retriever_plugin(mock_config, event_loop):
    retriever = RetrieverPlugin("test_retriever", alternative_config=mock_config)
    assert retriever.name == "test_retriever"
    assert str(retriever) == "Retriever(test_retriever)"
    with pytest.raises(NotImplementedError):
        event_loop.run_until_complete(retriever.run("arn:foo:bar", {"data": "information"}))