import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aardvark.exceptions import AccessAdvisorException
from aardvark.retrievers.access_advisor import AccessAdvisorRetriever


def test_generate_service_last_accessed_details(mock_config, event_loop):
    iam_client = MagicMock()
    iam_client.generate_service_last_accessed_details.return_value = {"JobId": "abc123"}
    aar = AccessAdvisorRetriever(alternative_config=mock_config)
    job_id = event_loop.run_until_complete(
        aar._generate_service_last_accessed_details(iam_client, "abc123")
    )
    assert job_id == "abc123"


def test_get_service_last_accessed_details(mock_config, event_loop):
    iam_client = MagicMock()
    iam_client.get_service_last_accessed_details.side_effect = [
        {"JobStatus": "IN_PROGRESS"},
        {"JobStatus": "IN_PROGRESS"},
        {
            "JobStatus": "COMPLETED",
            "ServicesLastAccessed": [
                {
                    "ServiceName": "AWS Lambda",
                    "LastAuthenticated": datetime.datetime(
                        2020, 4, 12, 15, 30, tzinfo=datetime.timezone.utc
                    ),
                    "ServiceNamespace": "lambda",
                    "LastAuthenticatedEntity": "arn:aws:iam::123456789012:user/admin",
                    "TotalAuthenticatedEntities": 6,
                },
            ],
        },
    ]
    aar = AccessAdvisorRetriever(alternative_config=mock_config)
    aa_data = event_loop.run_until_complete(
        aar._get_service_last_accessed_details(iam_client, "abc123")
    )
    assert aa_data["ServicesLastAccessed"][0]["ServiceName"] == "AWS Lambda"
    assert (
        aa_data["ServicesLastAccessed"][0]["LastAuthenticatedEntity"]
        == "arn:aws:iam::123456789012:user/admin"
    )


def test_get_service_last_accessed_details_failure(mock_config, event_loop):
    iam_client = MagicMock()
    iam_client.get_service_last_accessed_details.side_effect = [
        {"JobStatus": "IN_PROGRESS"},
        {"JobStatus": "FAILED", "Error": "Oh no!"},
    ]
    aar = AccessAdvisorRetriever(alternative_config=mock_config)
    with pytest.raises(AccessAdvisorException):
        aa_data = event_loop.run_until_complete(
            aar._get_service_last_accessed_details(iam_client, "abc123")
        )


@pytest.mark.parametrize(
    "arn,expected",
    [
        ("arn:aws:iam::123456789012:role/roleName", "123456789012"),  # Role ARN
        (
            "arn:aws:iam::123456789012:role/thisIsAPath/roleName",
            "123456789012",
        ),  # Role ARN with path
        ("arn:aws:iam::223456789012:policy/policyName", "223456789012"),  # Policy ARN
        ("arn:aws:iam::323456789012:user/userName", "323456789012"),  # User ARN
    ],
)
def test_get_account_from_arn(arn, expected):
    result = AccessAdvisorRetriever._get_account_from_arn(arn)
    assert result == expected


@pytest.mark.parametrize(
    "service_last_accessed,expected",
    [
        (
            # datetime object for LastAuthenticated
            {
                "ServiceName": "AWS Lambda",
                "LastAuthenticated": datetime.datetime(
                    2020, 4, 12, 15, 30, tzinfo=datetime.timezone.utc
                ),
                "ServiceNamespace": "lambda",
                "LastAuthenticatedEntity": "arn:aws:iam::123456789012:user/admin",
                "TotalAuthenticatedEntities": 6,
            },
            {
                "ServiceName": "AWS Lambda",
                "LastAuthenticated": 1586705400000,
                "ServiceNamespace": "lambda",
                "LastAuthenticatedEntity": "arn:aws:iam::123456789012:user/admin",
                "TotalAuthenticatedEntities": 6,
            },
        ),
        (
            # empty string for LastAuthenticated
            {
                "ServiceName": "AWS Lambda",
                "LastAuthenticated": "",
                "ServiceNamespace": "lambda",
                "LastAuthenticatedEntity": "",
                "TotalAuthenticatedEntities": 0,
            },
            {
                "ServiceName": "AWS Lambda",
                "LastAuthenticated": 0,
                "ServiceNamespace": "lambda",
                "LastAuthenticatedEntity": "",
                "TotalAuthenticatedEntities": 0,
            },
        ),
    ],
)
def test_transform_result(service_last_accessed, expected):
    result = AccessAdvisorRetriever._transform_result(service_last_accessed)
    assert result == expected


@pytest.mark.parametrize(
    "arn,data,expected",
    [
        # Empty input data
        (
            "arn:aws:iam::123456789012:user/admin",
            {},
            {
                "access_advisor": [
                    {
                        "LastAuthenticated": 1586705400000,
                        "LastAuthenticatedEntity": "arn:aws:iam::123456789012:user/admin",
                        "ServiceName": "AWS Lambda",
                        "ServiceNamespace": "lambda",
                        "TotalAuthenticatedEntities": 6,
                    }
                ]
            },
        ),
        # Non-empty input data
        (
            "arn:aws:iam::123456789012:user/admin",
            {"data_from_other_retrievers": "hello"},
            {
                "access_advisor": [
                    {
                        "LastAuthenticated": 1586705400000,
                        "LastAuthenticatedEntity": "arn:aws:iam::123456789012:user/admin",
                        "ServiceName": "AWS Lambda",
                        "ServiceNamespace": "lambda",
                        "TotalAuthenticatedEntities": 6,
                    }
                ],
                "data_from_other_retrievers": "hello",
            },
        ),
    ],
)
@patch("aardvark.retrievers.access_advisor.boto3_cached_conn")
def test_run(mock_boto3_cached_conn, mock_config, event_loop, arn, data, expected):
    mock_iam_client = MagicMock()
    mock_iam_client.generate_service_last_accessed_details.return_value = {
        "JobId": "abc123"
    }
    mock_iam_client.get_service_last_accessed_details.return_value = {
        "JobStatus": "COMPLETED",
        "ServicesLastAccessed": [
            {
                "ServiceName": "AWS Lambda",
                "LastAuthenticated": datetime.datetime(
                    2020, 4, 12, 15, 30, tzinfo=datetime.timezone.utc
                ),
                "ServiceNamespace": "lambda",
                "LastAuthenticatedEntity": "arn:aws:iam::123456789012:user/admin",
                "TotalAuthenticatedEntities": 6,
            },
        ],
    }
    mock_boto3_cached_conn.return_value = mock_iam_client
    aar = AccessAdvisorRetriever(alternative_config=mock_config)
    result = event_loop.run_until_complete(
        aar.run("arn:aws:iam::123456789012:user/admin", data)
    )
    assert result["access_advisor"]
    assert result == expected


@pytest.mark.parametrize("arn,data,expected", [("arn", {}, {})])
@patch("aardvark.retrievers.access_advisor.boto3_cached_conn")
def test_run_missing_arn(
    mock_boto3_cached_conn, mock_config, event_loop, arn, data, expected
):
    mock_iam_client = MagicMock()
    mock_iam_client.exceptions.NoSuchEntityException = Exception
    mock_iam_client.generate_service_last_accessed_details.side_effect = (
        mock_iam_client.exceptions.NoSuchEntityException()
    )
    mock_boto3_cached_conn.return_value = mock_iam_client
    aar = AccessAdvisorRetriever(alternative_config=mock_config)
    result = event_loop.run_until_complete(
        aar.run("arn:aws:iam::123456789012:user/admin", {})
    )
    assert result == expected
