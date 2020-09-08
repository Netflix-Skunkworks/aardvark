import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call

from moto import mock_iam

from aardvark.exceptions import RetrieverException


def test_register_retriever(runner, mock_config, mock_retriever):
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


def test_get_swag_accounts():
    pass


def test_queue_all_accounts():
    pass


def test_queue_accounts():
    pass


def test_run():
    pass
