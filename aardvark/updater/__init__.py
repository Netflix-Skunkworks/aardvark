import time
from cloudaux.aws.iam import list_roles, list_users
from cloudaux.aws.sts import boto3_cached_conn


class AccountToUpdate(object):
    def __init__(self, current_app, account_number, role_name, arns_list):
        self.current_app = current_app
        self.account_number = account_number
        self.role_name = role_name
        self.arn_list = arns_list
        self.conn_details = {
            'account_number': account_number,
            'assume_role': role_name,
            'session_name': 'aardvark',
            'region': self.current_app.config.get('REGION') or 'us-east-1'
        }
        self.max_access_advisor_job_wait = 5 * 60  # Wait 5 minutes before giving up on jobs

    def update_account(self):
        """
        Updates Access Advisor data for a given AWS account.
        1) Gets list of IAM Role ARNs in target account.
        2) Gets IAM credentials in target account.
        3) Calls GenerateServiceLastAccessedDetails for each role
        4) Calls GetServiceLastAccessedDetails for each role to retrieve data

        :return: Return code and JSON Access Advisor data for given account
        """
        arns = self._get_arns()

        if not arns:
            self.current_app.logger.warn("Zero ARNs collected. Exiting")
            exit(-1)

        client = self._get_client()
        try:
            details = self._call_access_advisor(client, list(arns))
        except Exception:
            self.current_app.logger.exception('Failed to call access advisor')
            return 255, None
        else:
            return 0, details

    def _get_arns(self):
        """
        Gets a list of all Role ARNs in a given account, optionally limited by
        class property ARN filter
        :return: list of role ARNs
        """
        client = boto3_cached_conn(
            'iam', service_type='client', **self.conn_details)

        account_arns = set()

        for role in list_roles(**self.conn_details):
            account_arns.add(role['Arn'])

        for user in list_users(**self.conn_details):
            account_arns.add(user['Arn'])

        for page in client.get_paginator('list_policies').paginate(Scope='Local'):
            for policy in page['Policies']:
                account_arns.add(policy['Arn'])

        for page in client.get_paginator('list_groups').paginate():
            for group in page['Groups']:
                account_arns.add(group['Arn'])

        result_arns = set()
        for arn in self.arn_list:
            if arn.lower() == 'all':
                return account_arns

            if arn not in account_arns:
                self.current_app.logger.warn("Provided ARN {arn} not found in account.".format(arn=arn))
                continue

            result_arns.add(arn)

        return list(result_arns)

    def _get_client(self):
        """
        Assumes into the target account and obtains IAM client

        :return: boto3 IAM client in target account & role
        """
        client = boto3_cached_conn(
            'iam', account_number=self.account_number, assume_role=self.role_name)
        return client

    def _call_access_advisor(self, iam, arns):
        jobs = self._generate_service_last_accessed_details(iam, arns)
        details = self._get_service_last_accessed_details(iam, jobs)
        return details

    @staticmethod
    def _generate_service_last_accessed_details(iam, arns):
        jobs = {}
        for role_arn in arns:
            job_id = iam.generate_service_last_accessed_details(Arn=role_arn)['JobId']
            jobs[job_id] = role_arn
        return jobs

    def _get_service_last_accessed_details(self, iam, jobs):
        access_details = {}
        job_queue = list(jobs.keys())
        start_time = time.time()
        while job_queue:
            now = time.time()
            if now - start_time > self.max_access_advisor_job_wait:
                # We ran out of time, some jobs are unfinished
                self._log_unfinished_jobs(job_queue, jobs)
                break
            job_id = job_queue.pop()
            role_arn = jobs[job_id]
            details = iam.get_service_last_accessed_details(JobId=job_id)
            if details['JobStatus'] == 'IN_PROGRESS':
                job_queue.append(job_id)
                if not job_queue:  # We're hanging on the last job, let's hang back for a bit
                    time.sleep(1)
                continue
            if details['JobStatus'] != 'COMPLETED':
                self.current_app.logger.error(
                    "Job {job_id} finished with unexpected status {status} for ARN {arn}.".format(
                        job_id=job_id,
                        status=details['JobStatus'],
                        arn=role_arn,
                ))
                continue
            access_details[role_arn] = details['ServicesLastAccessed']
            for detail in access_details[role_arn]:
                last_auth = detail.get('LastAuthenticated')
                if last_auth:
                    last_auth = time.mktime(last_auth.timetuple())
                else:
                    last_auth = 0
                detail['LastAuthenticated'] = last_auth
        return access_details

    def _log_unfinished_jobs(self, job_queue, job_details):
        for job_id in job_queue:
            role_arn = job_details[job_id]
            self.current_app.logger.error("Job {job_id} for ARN {arn} didn't finish".format(
                job_id=job_id,
                arn=role_arn,
            ))