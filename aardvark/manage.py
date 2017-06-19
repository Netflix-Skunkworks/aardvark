import json
import os
import Queue
import re
import threading

import better_exceptions # noqa
from bunch import Bunch
from distutils.spawn import find_executable
from flask import current_app
from flask_script import Manager, Command, Option
from swag_client import InvalidSWAGDataException
from swag_client.swag import get_all_accounts

from aardvark import create_app, db
from aardvark.updater import AccountToUpdate

manager = Manager(create_app)

ACCOUNT_QUEUE = Queue.Queue()
DB_LOCK = threading.Lock()
QUEUE_LOCK = threading.Lock()
UPDATE_DONE = False


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

            else:
                QUEUE_LOCK.release()


def persist_aa_data(app, aa_data):
    """
    Reads access advisor JSON file & persists to our database
    """
    from aardvark.model import AWSIAMObject, AdvisorData

    aa = json.loads(aa_data)

    with app.app_context():
        arn_cache = {}
        for arn, data in aa.items():
            if arn in arn_cache:
                item = arn_cache[arn]
            else:
                item = AWSIAMObject.get_or_create(arn)
                arn_cache[arn] = item
            for service in data:
                AdvisorData.create_or_update(item.id,
                                             service['lastAuthenticated'],
                                             service['serviceName'],
                                             service['serviceNamespace'],
                                             service['lastAuthenticatedEntity'],
                                             service['totalAuthenticatedEntities'])
        db.session.commit()


@manager.command
def drop_db():
    """ Drops the database. """
    db.drop_all()


@manager.command
def create_db():
    """ Creates the database. """
    db.create_all()


@manager.command
def config():
    """
    Creates a config file.

    SWAG_BUCKET = '...'
    SWAG_FILTER = '...'
    ROLENAME = '<ASSUME_ROLE_HERE>'
    REGION = 'us-east-1'
    NUM_THREADS = 5
    SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost:5432/db' or
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tmp/aardvark.db'
    PHANTOMJS = '/usr/local/bin/phantomjs'
    """
    print('\nAardvark can use SWAG to look up accounts. https://github.com/Netflix-Skunkworks/swag-client')
    use_swag = raw_input('Do you use SWAG to track accounts? [yN]: ')
    if len(use_swag) > 0 and 'yes'.startswith(use_swag.lower()):
        bucket = raw_input('SWAG_BUCKET: ')
        use_swag = True
    else:
        use_swag = False

    role_name = raw_input('ROLENAME: ')
    default_db_uri = 'sqlite:///{path}/aardvark.db'.format(path=os.getcwd())
    db_uri = raw_input('DATABASE [{default}]: '.format(default=default_db_uri)) or default_db_uri
    num_threads = raw_input('# Threads [5]: ') or 5  # testing shows problems with more than 6 threads
    phantom = find_executable('phantomjs') or raw_input('Path to phantomjs: ')

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
        if use_swag:
            filedata.write('SWAG_BUCKET = "{bucket}"\n'.format(bucket=bucket))
            filedata.write('SWAG_FILTER = {"ours": True}\n')
        filedata.write('ROLENAME = "{role}"\n'.format(role=role_name))
        filedata.write('REGION = "us-east-1"\n')
        filedata.write('SQLALCHEMY_DATABASE_URI = "{uri}"\n'.format(uri=db_uri))
        filedata.write('PHANTOMJS = "{phantom}"\n'.format(phantom=phantom))
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

    accounts = {}

    try:
        current_app.logger.info('getting bucket {}'.format(
                                current_app.config.get('SWAG_BUCKET')))

        swag_filter = current_app.config.get('SWAG_FILTER') or {'ours': True}

        accounts = get_all_accounts(bucket=current_app.config.get('SWAG_BUCKET'),
                                    **swag_filter).get('accounts')

    except (KeyError, InvalidSWAGDataException, Exception) as e:
        current_app.logger.error('Account names passed but SWAG not configured or unavailable: {}'.format(e))

    if 'all' in account_names:
        return [account['metadata'].get('account_number', None) for account in accounts]

    lookup = {account['name']: Bunch(account) for account in accounts}
    for account in accounts:
        for alias in account['alias']:
            lookup[alias] = Bunch(account)

    for name in account_names:
        if name not in lookup:
            current_app.logger.warn('Could not find an account named %s'
                                    % name)
            continue

        account_number = lookup[name]['metadata'].get('account_number', None)
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
