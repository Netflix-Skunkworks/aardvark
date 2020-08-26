import asyncio
import logging
import re
from copy import copy
from typing import List, Dict

import confuse
from asgiref.sync import sync_to_async
from cloudaux.aws.iam import list_roles, list_users
from cloudaux.aws.sts import boto3_cached_conn
from swag_client import InvalidSWAGDataException
from swag_client.backend import SWAGManager
from swag_client.util import parse_swag_config_options

from aardvark.plugins import AardvarkPlugin
from aardvark.retrievers import RetrieverPlugin
from aardvark.retrievers.access_advisor import AccessAdvisorRetriever

log = logging.getLogger("aardvark")


class RetrieverRunner(AardvarkPlugin):
    retrievers: List[RetrieverPlugin]
    account_queue: asyncio.Queue
    arn_queue: asyncio.Queue
    tasks: List[asyncio.Future]
    num_workers: int
    swag: SWAGManager
    swag_config: confuse.ConfigView

    def __init__(self, alternative_config: confuse.Configuration = None, alternative_arn_queue: asyncio.Queue = None, alternative_account_queue: asyncio.Queue = None):
        super().__init__(alternative_config)
        self.tasks = []
        self.retrievers = []
        self.num_workers = self.config["updater"]["num_threads"].as_number()
        self.swag_config = self.config["swag"]
        swag_opts = parse_swag_config_options(self.swag_config["opts"].get())
        self.swag = SWAGManager(**swag_opts)

    def register_retriever(self, r: RetrieverPlugin):
        """Add a retriever instance to be called during the run process."""
        self.retrievers.append(r)

    async def _run_retrievers(self, name: str):
        """Run all registered retrievers."""
        log.debug(f"creating {name}")
        while True:
            arn = await self.arn_queue.get()
            log.debug(f"{name} retrieving data for {arn}")
            data = {}
            # Iterate through retrievers, passing the results from the previous to the next.
            for r in self.retrievers:
                data = await r.run(arn, data)
            # TODO: store results
            self.arn_queue.task_done()

    async def _get_arns_for_account(self, account: str):
        """Retrieve ARNs for roles, users, policies, and groups in an account and add them to the ARN queue."""
        conn_details: Dict[str, str] = {
            "account_number": account,
            "assume_role": self.config["aws"]["rolename"].as_str(),
            "session_name": "aardvark",
            "region": self.config["aws"]["region"].as_str() or "us-east-1",
            "arn_partition": self.config["aws"]["arn_partition"].as_str() or "aws",
        }
        client = await sync_to_async(boto3_cached_conn)("iam", service_type="client", **conn_details)

        for role in await sync_to_async(list_roles)(**conn_details):
            await self.arn_queue.put(role["Arn"])

        for user in await sync_to_async(list_users)(**conn_details):
            await self.arn_queue.put(user["Arn"])

        for page in await sync_to_async(client.get_paginator("list_policies").paginate)(Scope="Local"):
            for policy in page["Policies"]:
                await self.arn_queue.put(policy["Arn"])

        for page in await sync_to_async(client.get_paginator("list_groups").paginate)():
            for group in page["Groups"]:
                await self.arn_queue.put(group["Arn"])

    async def _run_arn_lookup(self, name: str):
        log.debug(f"creating {name}")
        while True:
            account = await self.account_queue.get()
            log.debug(f"{name} retrieving ARNs for {account}")
            await self._get_arns_for_account(account)
            self.account_queue.task_done()

    async def _get_swag_accounts(self) -> List[Dict]:
        all_accounts: List[str] = []
        try:
            all_accounts: List[Dict] = self.swag.get_all(
                self.swag_config["filter"].get()
            )
            swag_service = self.swag_config["service_enabled_requirement"].get()
            if swag_service:
                all_accounts = await sync_to_async(self.swag.get_service_enabled)(
                    swag_service, accounts_list=all_accounts
                )
        except (KeyError, InvalidSWAGDataException) as e:
            log.error(
                "Account names passed but SWAG not configured or unavailable: {}".format(
                    e
                )
            )

        return all_accounts

    async def _queue_all_accounts(self):
        for account in await self._get_swag_accounts():
            await self.account_queue.put(account["id"])

    async def _queue_accounts(self, account_names: List[str]):
        accounts = copy(account_names)
        for account in accounts:
            if re.match(r"\d{12}", account):
                accounts.remove(account)
                await self.account_queue.put(account)

        all_accounts = await self._get_swag_accounts()

        # TODO(psanders): Consider refactoring. This could be expensive for organizations
        #  with many accounts and many aliases.
        for account in all_accounts:
            # Check if the account name matches one we want. If so, queue it and carry on.
            if account.get("name") in accounts:
                await self.account_queue.put(account["id"])
                continue
            # Now check the account's aliases to see if one matches.
            alias_key = "aliases" if account["schemaVersion"] == "2" else "alias"
            for alias in account.get(alias_key, []):
                if alias in accounts:
                    await self.account_queue.put(account["id"])
                    continue

    def cancel(self):
        log.info("Stopping runner tasks")
        for task in self.tasks:
            task.cancel()
            log.info(f"Task {task} canceled")

    async def run(self, accounts: List[str] = None, arns: List[str] = None):
        self.register_retriever(AccessAdvisorRetriever())
        log.debug("starting retriever")

        self.arn_queue = asyncio.Queue()
        self.account_queue = asyncio.Queue()

        lookup_accounts = True
        if arns:
            for arn in arns:
                await self.arn_queue.put(arn)
            lookup_accounts = False

        # We only need to do account lookups if ARNs were not provided.
        if lookup_accounts:
            if accounts:
                await self._queue_accounts(accounts)
            else:
                await self._queue_all_accounts()

            for i in range(self.num_workers):
                name = f"arn-lookup-worker-{i}"
                task = asyncio.create_task(self._run_arn_lookup(name))
                self.tasks.append(task)

        for i in range(self.num_workers):
            name = f"retriever-worker-{i}"
            task = asyncio.create_task(self._run_retrievers(name))
            self.tasks.append(task)

        await self.account_queue.join()
        await self.arn_queue.join()

        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)
