import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call

from swag_client.exceptions import InvalidSWAGDataException

from aardvark.exceptions import RetrieverException
from aardvark.retrievers.runner import RetrieverRunner


def test_register_retriever(runner, mock_retriever):
    runner.register_retriever(mock_retriever)
    assert len(runner.retrievers) == 1
    assert runner.retrievers[0].name == "retriever_stub"


@pytest.mark.asyncio
async def test_run_retrievers(runner, mock_retriever):
    runner.register_retriever(mock_retriever)
    result = await runner._run_retrievers("abc123")
    assert result
    assert result["arn"] == "abc123"
    assert result["retriever_stub"]["success"]


@pytest.mark.asyncio
async def test_run_retrievers_failure(runner, mock_failing_retriever):
    runner.register_retriever(mock_failing_retriever)
    with pytest.raises(RetrieverException):
        await runner._run_retrievers("abc123")


@pytest.mark.asyncio
async def test_retriever_loop(runner, mock_retriever):
    runner.register_retriever(mock_retriever)
    arn_queue = asyncio.Queue()
    await arn_queue.put("abc123")
    assert not arn_queue.empty()
    runner.arn_queue = arn_queue
    results_queue = asyncio.Queue()
    runner.results_queue = results_queue
    task = asyncio.create_task(runner._retriever_loop(""))
    await arn_queue.join()
    task.cancel()
    result = await runner.results_queue.get()
    assert result
    assert result["arn"] == "abc123"
    assert result["retriever_stub"]["success"]


@pytest.mark.asyncio
async def test_retriever_loop_failure(runner, mock_failing_retriever):
    runner.register_retriever(mock_failing_retriever)
    arn_queue = asyncio.Queue()
    await arn_queue.put("abc123")
    assert not arn_queue.empty()
    runner.arn_queue = arn_queue
    results_queue = asyncio.Queue()
    runner.results_queue = results_queue
    task = asyncio.create_task(runner._retriever_loop(""))
    await arn_queue.join()
    task.cancel()
    assert len(runner.failed_arns) == 1
    assert runner.failed_arns[0] == "abc123"
    assert runner.results_queue.empty()


@pytest.mark.asyncio
async def test_results_loop(runner, mock_retriever):
    runner.register_retriever(mock_retriever)
    results_queue = asyncio.Queue()
    await results_queue.put({"arn": "abc123", "access_advisor": {"access": "advised"}})
    runner.results_queue = results_queue
    expected = {"abc123": {"access": "advised"}}
    with patch("aardvark.retrievers.runner.sap") as sap:
        sap.store_role_data = MagicMock()
        task = asyncio.create_task(runner._results_loop(""))
        await runner.results_queue.join()
        task.cancel()
        sap.store_role_data.assert_called()
        sap.store_role_data.assert_called_with(expected)


@patch("aardvark.retrievers.runner.boto3_cached_conn")
@patch(
    "aardvark.retrievers.runner.list_roles",
    return_value=[{"Arn": "role1"}, {"Arn": "role2"}],
)
@patch(
    "aardvark.retrievers.runner.list_users",
    return_value=[{"Arn": "user1"}, {"Arn": "user2"}],
)
@pytest.mark.asyncio
async def test_get_arns_for_account(
    mock_list_users, mock_list_roles, mock_boto3_cached_conn, runner
):
    paginator = MagicMock()
    paginator.paginate.side_effect = (
        [{"Policies": [{"Arn": "policy1"}]}, {"Policies": [{"Arn": "policy2"}]}],
        [{"Groups": [{"Arn": "group1"}]}, {"Groups": [{"Arn": "group2"}]}],
    )
    mock_iam_client = MagicMock()
    mock_iam_client.get_paginator.return_value = paginator
    mock_boto3_cached_conn.return_value = mock_iam_client
    runner.arn_queue = asyncio.Queue()
    await runner._get_arns_for_account("012345678901")
    assert not runner.arn_queue.empty()
    expected = [
        "role1",
        "role2",
        "user1",
        "user2",
        "policy1",
        "policy2",
        "group1",
        "group2",
    ]
    for arn in expected:
        assert runner.arn_queue.get_nowait() == arn


@patch("aardvark.retrievers.runner.RetrieverRunner._get_arns_for_account")
@pytest.mark.asyncio
async def test_arn_lookup_loop(mock_get_arns_for_account, runner):
    account_queue = asyncio.Queue()
    account_queue.put_nowait("123456789012")
    account_queue.put_nowait("223456789012")
    runner.account_queue = account_queue
    task = asyncio.create_task(runner._arn_lookup_loop(""))
    await account_queue.join()
    task.cancel()
    assert mock_get_arns_for_account.call_args_list == [
        call("123456789012"),
        call("223456789012"),
    ]


@pytest.mark.asyncio
async def test_get_swag_accounts(mock_config):
    mock_config["swag"]["opts"] = {}
    mock_config["swag"]["filter"] = "mock swag filter"
    mock_config["swag"]["service_enabled_requirement"] = "glowcloud"
    swag_response = {"foo": "bar"}
    runner = RetrieverRunner(alternative_config=mock_config)
    runner.swag = MagicMock()
    runner.swag.get_all.return_value = swag_response
    runner.swag.get_service_enabled.return_value = swag_response
    result = await runner._get_swag_accounts()
    assert result == swag_response
    runner.swag.get_all.assert_called_with("mock swag filter")
    runner.swag.get_service_enabled.assert_called_with(
        "glowcloud", accounts_list={"foo": "bar"}
    )


@pytest.mark.asyncio
async def test_get_swag_accounts_failure(mock_config):
    mock_config["swag"]["opts"] = {}
    mock_config["swag"]["filter"] = "mock swag filter"
    mock_config["swag"]["service_enabled_requirement"] = "glowcloud"
    swag_response = {"foo": "bar"}
    runner = RetrieverRunner(alternative_config=mock_config)
    runner.swag = MagicMock()
    runner.swag.get_all.side_effect = InvalidSWAGDataException
    runner.swag.get_service_enabled.return_value = swag_response
    with pytest.raises(RetrieverException):
        await runner._get_swag_accounts()


@pytest.mark.asyncio
async def test_queue_all_accounts(runner):
    expected_account_ids = ["123456789012", "223456789012", "323456789012"]
    account_queue = asyncio.Queue()
    runner.account_queue = account_queue
    runner._get_swag_accounts = AsyncMock()
    runner._get_swag_accounts.return_value = [
        {"id": account_id} for account_id in expected_account_ids
    ]
    await runner._queue_all_accounts()
    for account_id in expected_account_ids:
        assert account_queue.get_nowait() == account_id
    assert account_queue.empty()


@pytest.mark.asyncio
async def test_queue_accounts(runner):
    swag_accounts = [
        {
            "schemaVersion": "2",
            "id": "123456789012",
            "name": "test",
        },
        {
            "schemaVersion": "2",
            "id": "223456789012",
            "name": "staging",
            "aliases": ["stage"],
        },
        {
            "schemaVersion": "2",
            "id": "323456789012",
            "name": "prod",
        },
    ]
    expected_account_ids = ["423456789012", "123456789012", "223456789012"]
    account_queue = asyncio.Queue()
    runner.account_queue = account_queue
    runner._get_swag_accounts = AsyncMock()
    runner._get_swag_accounts.return_value = swag_accounts
    await runner._queue_accounts(["test", "stage", "423456789012"])
    for account_id in expected_account_ids:
        assert account_queue.get_nowait() == account_id
    assert account_queue.empty()


@pytest.mark.asyncio
async def test_queue_arns(runner):
    arn_queue = asyncio.Queue()
    runner.arn_queue = arn_queue
    arns = ["arn1", "arn2"]
    await runner._queue_arns(arns)
    for arn in arns:
        assert arn_queue.get_nowait() == arn


@pytest.mark.asyncio
async def test_run(mock_config):
    runner = RetrieverRunner(alternative_config=mock_config)
    runner._queue_accounts = AsyncMock()
    runner._queue_arns = AsyncMock()
    runner._queue_all_accounts = AsyncMock()
    runner._arn_lookup_loop = AsyncMock()
    runner._retriever_loop = AsyncMock()
    runner._results_loop = AsyncMock()
    await runner.run()
    runner._queue_accounts.assert_not_called()
    runner._queue_arns.assert_not_called()
    runner._queue_all_accounts.assert_called()
    runner._arn_lookup_loop.assert_called_with("arn-lookup-worker-0")
    runner._retriever_loop.assert_called_with("retriever-worker-0")
    runner._results_loop.assert_called_with("results-worker-0")
    assert len(runner.tasks) == 3


@pytest.mark.asyncio
async def test_run_with_accounts(mock_config):
    runner = RetrieverRunner(alternative_config=mock_config)
    runner._queue_accounts = AsyncMock()
    runner._queue_arns = AsyncMock()
    runner._queue_all_accounts = AsyncMock()
    runner._arn_lookup_loop = AsyncMock()
    runner._retriever_loop = AsyncMock()
    runner._results_loop = AsyncMock()
    await runner.run(accounts=["test", "prod"])
    runner._queue_accounts.assert_called_with(["test", "prod"])
    runner._queue_arns.assert_not_called()
    runner._queue_all_accounts.assert_not_called()
    runner._arn_lookup_loop.assert_called_with("arn-lookup-worker-0")
    runner._retriever_loop.assert_called_with("retriever-worker-0")
    runner._results_loop.assert_called_with("results-worker-0")
    assert len(runner.tasks) == 3


@pytest.mark.asyncio
async def test_run_with_arns(mock_config):
    runner = RetrieverRunner(alternative_config=mock_config)
    runner._queue_accounts = AsyncMock()
    runner._queue_arns = AsyncMock()
    runner._queue_all_accounts = AsyncMock()
    runner._arn_lookup_loop = AsyncMock()
    runner._retriever_loop = AsyncMock()
    runner._results_loop = AsyncMock()
    await runner.run(arns=["arn1", "arn2"])
    runner._queue_accounts.assert_not_called()
    runner._queue_arns.assert_called_with(["arn1", "arn2"])
    runner._queue_all_accounts.assert_not_called()
    runner._arn_lookup_loop.assert_not_called()
    runner._retriever_loop.assert_called_with("retriever-worker-0")
    runner._results_loop.assert_called_with("results-worker-0")
    assert len(runner.tasks) == 2
