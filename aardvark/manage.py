#ensure absolute import for python3
from __future__ import absolute_import

import json
import os
try:
    import queue as Queue # Queue renamed to queue in py3
except ModuleNotFoundError:
    import Queue
import re
import threading

import better_exceptions # noqa
from bunch import Bunch
from distutils.spawn import find_executable
from flask import current_app
from flask_script import Manager, Command, Option
from swag_client.backend import SWAGManager
from swag_client.exceptions import InvalidSWAGDataException
from swag_client.util import parse_swag_config_options

from aardvark import create_app, db
from aardvark.updater import AccountToUpdate

try:               # Python 2
    raw_input
except NameError:  # Python 3
    raw_input = input

try:               # Python 2
    unicode
except NameError:  # Python 3
    unicode = str

manager = Manager(create_app)

ACCOUNT_QUEUE = Queue.Queue()
DB_LOCK = threading.Lock()
QUEUE_LOCK = threading.Lock()
UPDATE_DONE = False

SWAG_REPO_URL = 'https://github.com/Netflix-Skunkworks/swag-client'

LOCALDB = 'sqlite'

# Configuration default values.
DEFAULT_LOCALDB_FILENAME = 'aardvark.db'
DEFAULT_SWAG_BUCKET = 'swag-data'
DEFAULT_AARDVARK_ROLE = 'Aardvark'
DEFAULT_NUM_THREADS = 5  # testing shows problems with more than 6 threads


class UpdateAccountThread(threading.Thread):
    global ACCOUNT_QUEUE, DB_LOCK, QUEUE_LOCK, UPDATE_DONE

    def __init__(self, thread_ID):
        self.thread_ID = thread_ID
        threading.Thread.__init__(self)
        self.app = current_app._get_current_object()

    def run(self):
        while not UPDATE_DONE:

            QUEUE_LOCK.acquire()

            if not ACCOUNT_QUEUE.empty():
                (account_num, role_name, arns) = ACCOUNT_QUEUE.get()

                self.app.logger.info("Thread #{} updating account {} with {} arns".format(
                                     self.thread_ID, account_num, 'all' if arns[0] == 'all' else len(arns)))

                QUEUE_LOCK.release()

                account = AccountToUpdate(self.app, account_num, role_name, arns)
                ret_code, aa_data = account.update_account()

                if ret_code != 0:  # retrieve wasn't successful, put back on queue
                    QUEUE_LOCK.acquire()
                    ACCOUNT_QUEUE.put((account_num, role_name, arns))
                    QUEUE_LOCK.release()

                self.app.logger.info("Thread #{} persisting data for account {}".format(self.thread_ID, account_num))

                DB_LOCK.acquire()
                persist_aa_data(self.app, aa_data)
                DB_LOCK.release()

                self.app.logger.info("Thread #{} FINISHED persisting data for account {}".format(self.thread_ID, account_num))
            else:
                QUEUE_LOCK.release()


def persist_aa_data(app, aa_data):
    """
    Reads access advisor JSON file & persists to our database
    """
    from aardvark.model import AWSIAMObject, AdvisorData

    with app.app_context():
        if not aa_data:
            app.logger.warn('Cannot persist Access Advisor Data as no data was collected.')
            return

        arn_cache = {}
        for arn, data in aa_data.items():
            if arn in arn_cache:
                item = arn_cache[arn]
            else:
                item = AWSIAMObject.get_or_create(arn)
                arn_cache[arn] = item
            for service in data:
                AdvisorData.create_or_update(item.id,
                                             service['LastAuthenticated'],
                                             service['ServiceName'],
                                             service['ServiceNamespace'],
                                             service.get('LastAuthenticatedEntity'),
                                             service['TotalAuthenticatedEntities'])
        db.session.commit()


@manager.command
def drop_db():
    """ Drops the database. """
    db.drop_all()


@manager.command
def create_db():
    """ Creates the database. """
    db.create_all()


# All of these default to None rather than the corresponding DEFAULT_* values
# so we can tell whether they were passed or not. We don't prompt for any of
# the options that were passed as parameters.
@manager.option('-a', '--aardvark-role', dest='aardvark_role_param', type=unicode)
@manager.option('-b', '--swag-bucket', dest='bucket_param', type=unicode)
@manager.option('-d', '--db-uri', dest='db_uri_param', type=unicode)
@manager.option('--num-threads', dest='num_threads_param', type=int)
@manager.option('--no-prompt', dest='no_prompt', action='store_true', default=False)
def config(aardvark_role_param, bucket_param, db_uri_param, num_threads_param, no_prompt):
    """
    Creates a config.py configuration file from user input or default values.

    If all configurable values are specified by parameters, user input
    is not needed and will not be prompted.

    If the no-prompt flag is not set, user input will be prompted for
    each of the configurable values not specified by parameters.

    If the no-prompt flag is set, no user input will be collected and
    the configuration file will be populated with option-specified values
    or defaults.

    The resulting configuration file defines the following parameters.
    Configurable parameters are shown in <angle braces>.

    SWAG_OPTS = {'swag.type': 's3', 'swag.bucket_name': <bucket>}
    SWAG_FILTER = None
    SWAG_SERVICE_ENABLED_REQUIREMENT = None
    ROLENAME = <aardvark_role>
    REGION = "us-east-1"
    SQLALCHEMY_DATABASE_URI = <db_uri>
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    NUM_THREADS = <num_threads>
    LOG_CFG = {...}
    """
    # We don't set these until runtime.
    default_db_uri = '{localdb}:///{path}/{filename}'.format(
        localdb=LOCALDB, path=os.getcwd(), filename=DEFAULT_LOCALDB_FILENAME
        )

    if no_prompt:  # Just take the parameters as currently constituted.
        aardvark_role = aardvark_role_param or DEFAULT_AARDVARK_ROLE
        num_threads = num_threads_param or DEFAULT_NUM_THREADS
        db_uri = db_uri_param or default_db_uri

        # If a swag bucket was specified we set write_swag here so it gets
        # written out to the config file below.
        write_swag = bool(bucket_param)
        bucket = bucket_param or DEFAULT_SWAG_BUCKET

    else:
        # This is essentially the same "param, or input, or default"
        # structure as the additional parameters below.
        if bucket_param:
            bucket = bucket_param
            write_swag = True
        else:
            print('\nAardvark can use SWAG to look up accounts. See {repo_url}'.format(repo_url=SWAG_REPO_URL))
            use_swag = raw_input('Do you use SWAG to track accounts? [yN]: ')
            if len(use_swag) > 0 and 'yes'.startswith(use_swag.lower()):
                bucket_prompt = 'SWAG_BUCKET [{default}]: '.format(default=DEFAULT_SWAG_BUCKET)
                bucket = raw_input(bucket_prompt) or DEFAULT_SWAG_BUCKET
                write_swag = True
            else:
                write_swag = False

        aardvark_role_prompt = 'ROLENAME [{default}]: '.format(default=DEFAULT_AARDVARK_ROLE)
        db_uri_prompt = 'DATABASE URI [{default}]: '.format(default=default_db_uri)
        num_threads_prompt = '# THREADS [{default}]: '.format(default=DEFAULT_NUM_THREADS)

        aardvark_role = aardvark_role_param or raw_input(aardvark_role_prompt) or DEFAULT_AARDVARK_ROLE
        db_uri = db_uri_param or raw_input(db_uri_prompt) or default_db_uri
        num_threads = num_threads_param or raw_input(num_threads_prompt) or DEFAULT_NUM_THREADS

    log = """LOG_CFG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': 'aardvark.log',
            'maxBytes': 10485760,
            'backupCount': 100,
            'encoding': 'utf8'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'aardvark': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG'
        }
    }
}"""

    with open('config.py', 'w') as filedata:
        print('\n>> Writing to config.py')
        filedata.write('# Autogenerated config file\n')
        if write_swag:
            filedata.write("SWAG_OPTS = {{'swag.type': 's3', 'swag.bucket_name': '{bucket}'}}\n".format(bucket=bucket))
            filedata.write("SWAG_FILTER = None\n")
            filedata.write("SWAG_SERVICE_ENABLED_REQUIREMENT = None\n")
        filedata.write('ROLENAME = "{role}"\n'.format(role=aardvark_role))
        filedata.write('REGION = "us-east-1"\n')
        filedata.write('ARN_PARTITION = "aws"\n')
        filedata.write('SQLALCHEMY_DATABASE_URI = "{uri}"\n'.format(uri=db_uri))
        filedata.write('SQLALCHEMY_TRACK_MODIFICATIONS = False\n')
        filedata.write('NUM_THREADS = {num_threads}\n'.format(num_threads=num_threads))
        filedata.write(log)


@manager.option('-a', '--accounts', dest='accounts', type=unicode, default='all')
@manager.option('-r', '--arns', dest='arns', type=unicode, default='all')
def update(accounts, arns):
    """
    Asks AWS for new Access Advisor information.
    """
    accounts = _prep_accounts(accounts)
    arns = arns.split(',')
    app = create_app()

    global ACCOUNT_QUEUE, QUEUE_LOCK, UPDATE_DONE

    role_name = app.config.get('ROLENAME')
    num_threads = app.config.get('NUM_THREADS') or 5

    if num_threads > 6:
        current_app.logger.warn('Greater than 6 threads seems to cause problems')

    QUEUE_LOCK.acquire()
    for account_number in accounts:
        ACCOUNT_QUEUE.put((account_number, role_name, arns))
    QUEUE_LOCK.release()

    threads = []
    for thread_num in range(num_threads):
        thread = UpdateAccountThread(thread_num + 1)
        thread.start()
        threads.append(thread)

    while not ACCOUNT_QUEUE.empty():
        pass
    UPDATE_DONE = True


def _prep_accounts(account_names):
    """
    Convert CLI provided account names into list of accounts from SWAG.
    Considers account aliases as well as account names.
    Returns a list of account numbers
    """
    matching_accounts = list()
    account_names = account_names.split(',')
    account_names = {name.lower().strip() for name in account_names}

    # create a new copy of the account_names list so we can remove accounts as needed
    for account in list(account_names):
        if re.match('\d{12}', account):
            account_names.remove(account)
            matching_accounts.append(account)

    if not account_names:
        return matching_accounts

    try:
        current_app.logger.info('getting bucket {}'.format(
                                current_app.config.get('SWAG_BUCKET')))

        swag = SWAGManager(**parse_swag_config_options(current_app.config.get('SWAG_OPTS')))

        all_accounts = swag.get_all(current_app.config.get('SWAG_FILTER'))

        service_enabled_requirement = current_app.config.get('SWAG_SERVICE_ENABLED_REQUIREMENT', None)
        if service_enabled_requirement:
            all_accounts = swag.get_service_enabled(service_enabled_requirement, accounts_list=all_accounts)

    except (KeyError, InvalidSWAGDataException, Exception) as e:
        current_app.logger.error('Account names passed but SWAG not configured or unavailable: {}'.format(e))

    if 'all' in account_names:
        return [account['id'] for account in all_accounts]

    lookup = {account['name']: Bunch(account) for account in all_accounts}

    for account in all_accounts:
        # get the right key, depending on whether we're using swag v1 or v2
        alias_key = 'aliases' if account['schemaVersion'] == '2' else 'alias'
        for alias in account[alias_key]:
            lookup[alias] = Bunch(account)

    for name in account_names:
        if name not in lookup:
            current_app.logger.warn('Could not find an account named %s'
                                    % name)
            continue

        account_number = lookup[name].get('id', None)
        if account_number:
            matching_accounts.append(account_number)

    return matching_accounts


class GunicornServer(Command):
    """
    This is the main GunicornServer server, it runs the flask app with gunicorn and
    uses any configuration options passed to it.
    You can pass all standard gunicorn flags to this command as if you were
    running gunicorn itself.
    For example:
    aardvark start_api -w 4 -b 127.0.0.0:8002
    Will start gunicorn with 4 workers bound to 127.0.0.0:8002
    """
    description = 'Run the app within Gunicorn'

    def get_options(self):
        options = []
        try:
            from gunicorn.config import make_settings
        except ImportError:
            # Gunicorn does not yet support Windows.
            # See issue #524. https://github.com/benoitc/gunicorn/issues/524
            # For dev on Windows, make this an optional import.
            print('Could not import gunicorn, skipping.')
            return options

        settings = make_settings()
        for setting, klass in settings.items():
            if klass.cli:
                if klass.action:
                    if klass.action == 'store_const':
                        options.append(Option(*klass.cli, const=klass.const, action=klass.action))
                    else:
                        options.append(Option(*klass.cli, action=klass.action))
                else:
                    options.append(Option(*klass.cli))
        return options

    def run(self, *args, **kwargs):
        from gunicorn.app.wsgiapp import WSGIApplication

        app = WSGIApplication()

        app.app_uri = 'aardvark:create_app()'
        return app.run()


def main():
    manager.add_command("start_api", GunicornServer())
    manager.run()


if __name__ == '__main__':
    manager.add_command("start_api", GunicornServer())
    manager.run()
