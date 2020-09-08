import asyncio
import datetime
import logging
import time
from typing import Any, Dict, List, Union

from asgiref.sync import sync_to_async
import confuse
from cloudaux.aws.sts import boto3_cached_conn

from aardvark.exceptions import AccessAdvisorException
from aardvark.retrievers import RetrieverPlugin

log = logging.getLogger("aardvark")


class AccessAdvisorRetriever(RetrieverPlugin):
    def __init__(self, alternative_config: confuse.Configuration = None):
        super().__init__("access_advisor", alternative_config=alternative_config)

    async def _generate_service_last_accessed_details(self, iam_client, arn):
        """ Wrapping the actual AWS API calls for rate limiting protection. """
        result = await sync_to_async(iam_client.generate_service_last_accessed_details)(
            Arn=arn
        )
        return result["JobId"]

    async def _get_service_last_accessed_details(self, iam_client, job_id):
        """ Wrapping the actual AWS API calls for rate limiting protection. """
        attempts = 0
        while attempts < 10:
            details = await sync_to_async(iam_client.get_service_last_accessed_details)(
                JobId=job_id
            )
            job_status = details.get("JobStatus")
            if job_status == "COMPLETED":
                return details
            elif job_status == "IN_PROGRESS":
                # backoff sleep and try again
                await asyncio.sleep(2 ** attempts)
                continue
            else:
                error = details.get("Error") or "no error details provided"
                raise AccessAdvisorException(f"Access Advisor job failed: {error}")

    @staticmethod
    def _get_account_from_arn(arn: str) -> str:
        return arn.split(":")[4]

    @staticmethod
    def _transform_result(
        service_last_accessed: Dict[str, Union[str, int, datetime.datetime]]
    ) -> Dict[str, Union[str, int]]:
        last_authenticated = service_last_accessed.get("LastAuthenticated")

        # Convert from datetime to timestamp
        if last_authenticated:
            last_authenticated = int(time.mktime(last_authenticated.utctimetuple()) * 1000)
        else:
            last_authenticated = 0

        service_last_accessed["LastAuthenticated"] = last_authenticated
        return service_last_accessed

    async def run(self, arn: str, data: Dict[str, Any]) -> Dict[str, Any]:
        log.debug(f"running {self} for {arn}")
        account = self._get_account_from_arn(arn)
        conn_details: Dict[str, str] = {
            "account_number": account,
            "assume_role": self.config["aws"]["rolename"].as_str(),
            "session_name": "aardvark",
            "region": self.config["aws"]["region"].as_str() or "us-east-1",
            "arn_partition": self.config["aws"]["arn_partition"].as_str() or "aws",
        }
        iam_client = await sync_to_async(boto3_cached_conn)("iam", **conn_details)
        try:
            job_id = await self._generate_service_last_accessed_details(iam_client, arn)
        except iam_client.exceptions.NoSuchEntityException as e:
            log.info(f"ARN {arn} no longer exists in AWS IAM")
            return data

        aa_details = await self._get_service_last_accessed_details(iam_client, job_id)
        result = map(self._transform_result, aa_details["ServicesLastAccessed"])
        data["access_advisor"] = list(result)
        return data
