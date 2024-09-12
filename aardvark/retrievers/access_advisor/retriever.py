from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from asgiref.sync import sync_to_async
from cloudaux.aws.sts import boto3_cached_conn

from aardvark.exceptions import AccessAdvisorError
from aardvark.retrievers import RetrieverPlugin

if TYPE_CHECKING:
    import datetime

    from dynaconf.utils import DynaconfDict

log = logging.getLogger("aardvark")


class AccessAdvisorRetriever(RetrieverPlugin):
    def __init__(self, alternative_config: DynaconfDict | None = None):
        super().__init__("access_advisor", alternative_config=alternative_config)

    async def _generate_service_last_accessed_details(self, iam_client, arn):
        """Call IAM API to create an Access Advisor job."""
        result = await sync_to_async(iam_client.generate_service_last_accessed_details)(Arn=arn)
        return result["JobId"]

    async def _get_service_last_accessed_details(self, iam_client, job_id):
        """Retrieve Access Advisor job results. Do an exponential backoff if the job is not complete."""
        attempts = 0
        while attempts < self.config.get("last_accessed_api_retries", 10):
            details = await sync_to_async(iam_client.get_service_last_accessed_details)(JobId=job_id)
            match details.get("JobStatus"):
                case "COMPLETED":
                    return details
                case "IN_PROGRESS":
                    # backoff sleep and try again
                    await asyncio.sleep(2**attempts)
                    continue
                case _:
                    message = f"Access Advisor job failed: {details.get('Error') or 'no error details provided'}"
                    raise AccessAdvisorError(message)
        message = "Access Advisor job failed: exceeded max retries"
        raise AccessAdvisorError(message)

    @staticmethod
    def _get_account_from_arn(arn: str) -> str:
        """Return the AWS account ID from an ARN."""
        return arn.split(":")[4]

    @staticmethod
    def _transform_result(service_last_accessed: dict[str, str | int | datetime.datetime]) -> dict[str, str | int]:
        """'Transform' Access Advisor result, which really just means convert the datetime to a timestamp."""
        last_authenticated = service_last_accessed.get("LastAuthenticated")

        # Convert from datetime to timestamp, defaulting to zero if there isn't one
        last_authenticated = int(last_authenticated.timestamp() * 1000) if last_authenticated else 0

        service_last_accessed["LastAuthenticated"] = last_authenticated
        return service_last_accessed

    async def run(self, arn: str, data: dict[str, Any]) -> dict[str, Any]:
        """Retrieve Access Advisor data for the given ARN and add the results to `data["access_advisor"]`."""
        log.debug("running %s for %s", self, arn)
        account = self._get_account_from_arn(arn)
        conn_details: dict[str, str] = {
            "account_number": account,
            "assume_role": self.config.get("aws_rolename"),
            "session_name": "aardvark",
            "region": self.config.get("aws_region", "us-east-1"),
            "arn_partition": self.config("aws_arn_partition", "aws"),
        }
        iam_client = boto3_cached_conn("iam", **conn_details)
        try:
            job_id = await self._generate_service_last_accessed_details(iam_client, arn)
        except iam_client.exceptions.NoSuchEntityException:
            log.info("ARN %s no longer exists in AWS IAM", arn)
            return data

        aa_details = await self._get_service_last_accessed_details(iam_client, job_id)
        result = map(self._transform_result, aa_details["ServicesLastAccessed"])
        data["access_advisor"] = list(result)
        return data
