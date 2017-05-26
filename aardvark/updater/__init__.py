from cloudaux.aws.iam import list_roles
from cloudaux.aws.sts import boto3_cached_conn
import requests
import json
import os
import tempfile
import urllib
import subprocess32
from subprocess32 import CalledProcessError

federation_base_url = 'https://signin.aws.amazon.com/federation'


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

    def update_account(self):
        """
        Updates Access Advisor data for a given AWS account.
        1) Gets list of IAM Role ARNs in target account.
        2) Gets IAM credentials in target account.
        3) Exchanges IAM credentials for Signin Token.
        4) Calls PhantomJS to do the dirty work.
        5) Saves PhantomJS output to our DB.

        :return: Return code and JSON Access Advisor data for given account
        """
        arns = self._get_arns()

        if not arns:
            self.current_app.logger.warn("Zero ARNs collected. Exiting")
            exit(-1)

        creds = self._get_creds()
        token = _get_signin_token(creds)
        with tempfile.NamedTemporaryFile() as f:
            ret_code = self._call_phantom(token, list(arns), f.name)
            if ret_code == 0:
                return ret_code, f.read()
            else:
                return ret_code, None

    def _get_arns(self):
        """
        Gets a list of all Role ARNs in a given account, optionally limited by
        class property ARN filter
        :return: list of role ARNs
        """
        roles = list_roles(**self.conn_details)
        account_arns = set([role['Arn'] for role in roles])
        result_arns = set()
        for arn in self.arn_list:
            if arn.lower() == 'all':
                return account_arns

            if arn not in account_arns:
                self.current_app.logger.warn("Provided ARN {arn} not found in account.".format(arn=arn))
                continue

            result_arns.add(arn)

        return list(result_arns)

    def _get_creds(self):
        """
        Assumes into the target account and obtains Access Key, Secret Key, and Token

        :return: URL-encoded dictionary containing Access Key, Secret Key, and Token
        """
        client, credentials = boto3_cached_conn(
            'iam', account_number=self.account_number, assume_role=self.role_name, return_credentials=True)

        creds = json.dumps(dict(
            sessionId=credentials['AccessKeyId'],
            sessionKey=credentials['SecretAccessKey'],
            sessionToken=credentials['SessionToken']
        ))
        creds = urllib.quote(creds, safe='')
        return creds

    def _call_phantom(self, token, arns, output_file):
        """
        shells out to phantomjs.
        - Writes ARNs to a file that phantomjs will read as an input.
        - Phantomjs exchanges the token for session cookies.
        - Phantomjs then navigates to the IAM page and executes JavaScript
        to call GenerateServiceLastAccessedDetails for each ARN.
        - Every 10 seconds, Phantomjs calls GetServiceLastAccessedDetails
        - Phantom saves output to a file that is used by `persist()`

        :return: Exit code from phantomjs subprocess32
        """

        path = os.path.dirname(__file__)
        console_js = os.path.join(path, 'awsconsole.js')

        with tempfile.NamedTemporaryFile() as f:
            json.dump(arns, f)
            f.seek(0)
            try:
                p = subprocess32.Popen([
                    self.current_app.config.get('PHANTOMJS'),
                    console_js,
                    token,
                    f.name,
                    output_file],
                    stdout=subprocess32.PIPE, stderr=subprocess32.STDOUT)
                output, errs = p.communicate(timeout=1200)  # 20 mins
                self.current_app.logger.debug('Phantom Output: \n{}'.format(output))
                self.current_app.logger.debug('Phantom Errors: \n{}'.format(errs))
            except subprocess32.TimeoutExpired:
                self.current_app.logger.error('PhantomJS timed out')
                return 1  # return code 1 for timeout
            except CalledProcessError:
                self.current_app.logger.error('PhantomJS exited: {}'
                                              ''.format(p.returncode))
                return p.returncode
            else:
                self.current_app.logger.info('PhantomJS exited: 0')
                return 0


def _get_signin_token(creds):
    """
    Exchanges credentials dictionary for a signin token.

    1) Creates URL using credentials dictionary.
    2) Sends a GET request to that URL and parses the response looking for
    a signin token.

    :return: Signin Token
    """
    url = '{base}?Action=getSigninToken&Session={creds}'
    url = url.format(base=federation_base_url, creds=creds)
    return requests.get(url).json()['SigninToken']
