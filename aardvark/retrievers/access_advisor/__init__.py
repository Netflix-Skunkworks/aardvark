import asyncio
import logging
from typing import Any, Dict

from asgiref.sync import sync_to_async
import confuse
from cloudaux.aws.decorators import rate_limited
from cloudaux.aws.sts import boto3_cached_conn

from aardvark.retrievers import RetrieverPlugin

log = logging.getLogger("aardvark")


class AccessAdvisorRetriever(RetrieverPlugin):
    def __init__(self, alternative_config: confuse.Configuration = None):
        super().__init__(alternative_config=alternative_config)

    # @rate_limited()
    async def _generate_service_last_accessed_details(self, iam_client, arn):
        """ Wrapping the actual AWS API calls for rate limiting protection. """
        result = await sync_to_async(iam_client.generate_service_last_accessed_details)(Arn=arn)
        return result["JobId"]

    # @rate_limited()
    async def _get_service_last_accessed_details(self, iam_client, job_id):
        """ Wrapping the actual AWS API calls for rate limiting protection. """
        return await sync_to_async(iam_client.get_service_last_accessed_details)(JobId=job_id)

    @staticmethod
    def _get_account_from_arn(arn: str) -> str:
        return arn.split(":")[4]

    async def run(self, arn: str, data: Dict[str, Any]) -> Dict[str, Any]:
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
        result = await self._get_service_last_accessed_details(iam_client, job_id)
        return result
        # TODO: merge `result` with `data` and return
