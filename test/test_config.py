'''Test cases for the manage.config() function.

We test the following for the configurable parameters:
- Exactly the expected parameters appear in the config file.
- The expected parameters have the expected values in the config file.


In the event of test failures it may be helpful to examine the command
used to launch aardvark config, any responses to prompts and the
resulting configuration file. To this end, these artifacts will be
saved in locations controlled by the environment variable
SWAG_CONFIG_TEST_ARCHIVE_DIR. Set this environment variable to the
absolute path to the directory to use to archive test artifacts. The
default is '/tmp'.

By default, artifacts will only be saved in the event of test
failures. To force archiving of test artifacts regardless of test
status, set the SWAG_CONFIG_TEST_ALWAYS_ARCHIVE to 1 (or anything
truthy).

Archiving occurs in tearDown(). The config file, the command line call
to "aardvark config" and a transcript of the command line interaction
will be saved in the archive directory in files named "command.*" and
"config.py.*". The wildcard will be replaced by default with the name
of the "test_*" function that was running when the failure occcured.


The command lines used to call aardvark config in each test case will
always be archived. Set the SWAG_CONFIG_TEST_COMMAND_ARCHIVE_DIR
environment variable to the absolute path to the directory to use to
archive these commands.  The default is to use the same value as
SWAG_CONFIG_TEST_ARCHIVE_DIR. This will create a record of all the
command lines executed in execution of these test cases, in files
names "commands.[TestClassName]".

'''

#adding for py3 support
from __future__ import absolute_import

import inspect
import os
import shutil
import tempfile

import unittest

from aardvark import manage
import pexpect

# These are fast command line script interactions, eight seconds is forever.
EXPECT_TIMEOUT = 8

CONFIG_FILENAME = 'config.py'

ALWAYS_ARCHIVE = os.environ.get('SWAG_CONFIG_TEST_ALWAYS_ARCHIVE')

# Locations where we will archive test artifacts.
DEFAULT_ARTIFACT_ARCHIVE_DIR = '/tmp'
ARTIFACT_ARCHIVE_DIR = (
    os.environ.get('SWAG_CONFIG_TEST_ARCHIVE_DIR') or
    DEFAULT_ARTIFACT_ARCHIVE_DIR
    )
COMMAND_ARCHIVE_DIR = (
    os.environ.get('SWAG_CONFIG_TEST_COMMAND_ARCHIVE_DIR') or
    ARTIFACT_ARCHIVE_DIR
    )

DEFAULT_LOCALDB_FILENAME = 'aardvark.db'
DEFAULT_AARDVARK_ROLE = 'Aardvark'
DEFAULT_NUM_THREADS = 5

# Specification of option names, default values, methods of extracting
# from config file, etc. The keys here are what we use as the 'handle'
# for each configurable option throughout this test file.
CONFIG_OPTIONS = {
    'swag_bucket': {
        'short': '-b',
        'long': '--swag-bucket',
        'config_key': 'SWAG_OPTS',
        'config_prompt': r'(?i).*SWAG.*BUCKET.*:',
        'getval': lambda x: x.get('swag.bucket_name') if x else None,
        'default': manage.DEFAULT_SWAG_BUCKET
        },
    'aardvark_role': {
        'short': '-a',
        'long': '--aardvark-role',
        'config_key': 'ROLENAME',
        'config_prompt': r'(?i).*ROLE.*NAME.*:',
        'getval': lambda x: x,
        'default': manage.DEFAULT_AARDVARK_ROLE
        },
    'db_uri': {
        'short': '-d',
        'long': '--db-uri',
        'config_key': 'SQLALCHEMY_DATABASE_URI',
        'getval': lambda x: x,
        'config_prompt': r'(?i).*DATABASE.*URI.*:',
        'default': None  # need to be in tmpdir.
        },
    'num_threads': {
        'short': None,
        'long': '--num-threads',
        'config_key': 'NUM_THREADS',
        'config_prompt': r'(?i).*THREADS.*:',
        'getval': lambda x: x,
        'default': manage.DEFAULT_NUM_THREADS
        },
    }

# Syntax sugar for getting default parameters for each option. Note
# that we reset the db_uri value after we change the working directory
# in setUpClass().
DEFAULT_PARAMETERS = dict([
    (k, v['default']) for k, v in CONFIG_OPTIONS.items()
    ])
DEFAULT_PARAMETERS_NO_SWAG = dict(DEFAULT_PARAMETERS, **{'swag_bucket': None})

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Uncomment to show lower level logging statements.
# import logging
# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
# shandler = logging.StreamHandler()
# shandler.setLevel(logging.INFO)  # Pick one.
# <!-- # shandler.setLevel(logging.DEBUG)  # Pick one. -->
# formatter = logging.Formatter(
#     '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     )
# shandler.setFormatter(formatter)
# logger.addHandler(shandler)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def default_db_uri():
    '''Return the default db_uri value at runtime.'''
    return '{localdb}:///{path}/{filename}'.format(
        localdb=manage.LOCALDB,
        path=os.getcwd(),
        filename=manage.DEFAULT_LOCALDB_FILENAME
        )


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def get_config_option_string(cmdline_option_spec, short_flags=True):
    '''Construct the options string for a call to aardvark config.'''

    option_substrings = []

    for param, value in cmdline_option_spec.items():
        flag = (
            CONFIG_OPTIONS[param]['short']
            if short_flags and CONFIG_OPTIONS[param]['short']
            else CONFIG_OPTIONS[param]['long']
            )
        option_substrings.append('{} {}'.format(flag, value))

    return ' '.join(option_substrings)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def load_configfile(cmdline_option_spec):
    '''Evaluate the config values for the fields in cmdline_option_spec.'''

    all_config = {}
    with open(CONFIG_FILENAME) as in_file:
        exec(in_file.read(), all_config)
    # print all_config.keys()
    found_config = dict([
        (k, v['getval'](all_config.get(v['config_key'])))
        for (k, v) in CONFIG_OPTIONS.items()
        ])
    return found_config


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def get_expected_config(option_spec):
    '''Return a dict with the values that should be set by a config file.'''

    include_swag = ('swag_bucket' in option_spec)
    default_parameters = (
        DEFAULT_PARAMETERS if include_swag else DEFAULT_PARAMETERS_NO_SWAG
        )
    expected_config = dict(default_parameters)
    expected_config.update(option_spec)

    return expected_config


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TestConfigBase(unittest.TestCase):
    '''Base class for config test cases.'''

    # Throughout, the dicts cmdline_option_spec and config_option_spec
    # are defined with keys matching the keys in CONFIG_SPEC and the
    # values defining the value for the corresponding parameter, to be
    # delivered via a command line parameter to 'aardvark config' or
    # via entry after the appropriate prompt interactively.

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def setUpClass(cls):
        '''Test case class common fixture setup.'''

        cls.tmpdir = tempfile.mkdtemp()
        cls.original_working_dir = os.getcwd()
        os.chdir(cls.tmpdir)

        cls.commands_issued = []

        # These depend on the current working directory set above.
        CONFIG_OPTIONS['db_uri']['default'] = default_db_uri()
        DEFAULT_PARAMETERS['db_uri'] = CONFIG_OPTIONS['db_uri']['default']
        DEFAULT_PARAMETERS_NO_SWAG['db_uri'] = (
            CONFIG_OPTIONS['db_uri']['default']
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def tearDownClass(cls):
        '''Test case class common fixture teardown.'''

        os.chdir(cls.original_working_dir)
        cls.clean_tmpdir()
        os.rmdir(cls.tmpdir)

        command_archive_filename = '.'.join(['commands', cls.__name__])
        command_archive_path = os.path.join(
            COMMAND_ARCHIVE_DIR, command_archive_filename
            )

        with open(command_archive_path, 'w') as fptr:
            fptr.write('\n'.join(cls.commands_issued) + '\n')

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def clean_tmpdir(cls):
        '''Remove all content from cls.tmpdir.'''
        for root, dirs, files in os.walk(cls.tmpdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def setUp(self):
        '''Test case common fixture setup.'''
        self.clean_tmpdir()
        self.assertFalse(os.path.exists(CONFIG_FILENAME))
        self.last_transcript = []
        self.archive_case_artifacts_as = None

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def tearDown(self):
        '''Test case common fixture teardown.'''

        # Archive the last command and config file created, if indicated.
        if self.archive_case_artifacts_as:

            command_archive_path = self.archive_path(
                'command', self.archive_case_artifacts_as
                )
            config_archive_path = self.archive_path(
                CONFIG_FILENAME, self.archive_case_artifacts_as
                )

            with open(command_archive_path, 'w') as fptr:
                fptr.write(self.last_config_command + '\n')
                if self.last_transcript:
                    fptr.write(
                        '\n'.join(
                            map(lambda x: str(x), self.last_transcript)
                            ) + '\n'
                        )

            if os.path.exists(CONFIG_FILENAME):
                shutil.copyfile(CONFIG_FILENAME, config_archive_path)
            else:
                with open(config_archive_path, 'w') as fptr:
                    fptr.write(
                        '(no {} file found in {})\n'.format(
                            CONFIG_FILENAME, os.getcwd()
                            )
                        )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def archive_path(self, filename, suffix):
        '''Return the path to an archive file.'''
        archive_filename = '.'.join([filename, suffix])
        archive_path = os.path.join(ARTIFACT_ARCHIVE_DIR, archive_filename)
        return archive_path

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def call_aardvark_config(
            self,
            cmdline_option_spec=None,
            input_option_spec=None,
            prompt=True,
            short_flags=False
            ):
        '''Call aardvark config and interact as necessary.'''

        cmdline_option_spec = cmdline_option_spec or {}
        input_option_spec = input_option_spec or {}

        command = 'aardvark config' + ('' if prompt else ' --no-prompt')
        self.last_config_command = '{} {}'.format(
            command,
            get_config_option_string(
                cmdline_option_spec, short_flags=short_flags
                )
            )

        self.commands_issued.append(self.last_config_command)
        spawn_config = pexpect.spawn(self.last_config_command)

        self.conduct_config_prompt_sequence(
            spawn_config, input_option_spec
            )

        # If we didn't wrap up the session, something's amiss.
        self.assertFalse(spawn_config.isalive())

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def conduct_config_prompt_sequence(self, spawned, input_option_spec):
        '''Carry out the steps in the config prompt sequence.'''

        # The order is all that tells us which of these match in a pexpect
        # call, so we can't use a dict here.
        control_prompts = [
            (pexpect.EOF, 'eof'),
            (pexpect.TIMEOUT, 'timeout')
            ]
        config_option_prompts = [
            (v['config_prompt'], k)
            for k, v in CONFIG_OPTIONS.items()
            ]
        expect_prompts = [
            (r'(?i).*Do you use SWAG.*:', 'use_swag'),
            ]

        expect_prompts.extend(config_option_prompts)
        expect_prompts.extend(control_prompts)

        response_spec = input_option_spec
        response_spec['use_swag'] = (
            'y' if 'swag_bucket' in input_option_spec else 'N'
            )

        while spawned.isalive():

            prompt_index = spawned.expect(
                [x[0] for x in expect_prompts], timeout=EXPECT_TIMEOUT
                )
            self.last_transcript.append(spawned.after)

            prompt_received = expect_prompts[prompt_index][1]
            if prompt_received in [x[1] for x in control_prompts]:
                return

            response = response_spec.get(prompt_received)
            response = '' if response is None else response
            spawned.sendline(str(response))

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def case_worker(
            self,
            cmdline_option_spec=None,
            input_option_spec=None,
            prompt=False,
            short_flags=False,
            expect_config_file=True,
            archive_as=None
            ):
        '''Carry out common test steps.

        Parameters:

            cmdline_option_spec (dict or None):
                A dictionary specifying the options and values to pass
                to aardvark config as command line flags.

            input_option_spec (dict or None):
                A dictionary specifying the options and values to pass
                to aardvark config as prompted interactive input.

            prompt (bool, default: False):
                If False, set the --no-prompt option when calling
                aardvark config.

            short_flags (bool, default: False):
                If True, set the --short-flags  option when calling
                aardvark config.

            expect_config_file (bool, default: True):
                If True, test for the presence and correctness of a
                config file after calling aardvark config. If false,
                test for the absence of a config file.

            archive_as (str or None):
                The "unique" string to use when constructing a
                filename for archiving artifacts of this test case. If
                None, the name of the nearest calling function in the
                call stack named "test_*" will be used, if one can be
                found; otherwise a possibly non-unique string will be
                used.

        '''

        cmdline_option_spec = cmdline_option_spec or {}
        input_option_spec = input_option_spec or {}
        # Combined, for validation.
        option_spec = dict(cmdline_option_spec, **input_option_spec)

        if not archive_as:
            # Get the calling test case function's name, for
            # archiving. We'll take the first caller in the stack
            # whose name starts with 'test_'.
            caller_names = [
                inspect.getframeinfo(frame[0]).function
                for frame in inspect.stack()
                if inspect.getframeinfo(frame[0]).function.startswith('test_')
                ]
            archive_as = caller_names[0] if caller_names else 'unknown_test'

        # Turn on failed-case archive.
        self.archive_case_artifacts_as = archive_as

        self.assertFalse(os.path.exists(CONFIG_FILENAME))
        self.call_aardvark_config(
            cmdline_option_spec=cmdline_option_spec,
            input_option_spec=input_option_spec,
            prompt=prompt,
            short_flags=short_flags
            )

        if expect_config_file:
            self.assertTrue(os.path.exists(CONFIG_FILENAME))

            found_config = load_configfile(cmdline_option_spec)
            expected_config = get_expected_config(option_spec)

            self.assertCountEqual(expected_config.keys(), found_config.keys())
            for k, v in found_config.items():
                self.assertEqual((k, v), (k, expected_config[k]))

        else:
            self.assertFalse(os.path.exists(CONFIG_FILENAME))

        # Turn off failed-case archive unless we're forcing archiving.
        if not ALWAYS_ARCHIVE:
            self.archive_case_artifacts_as = None


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TestConfigNoPrompt(TestConfigBase):
    '''Test cases for config --no-prompt.'''

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_no_prompt_defaults(self):
        '''Test with no-prompt and all default arguments.'''

        self.case_worker()

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_no_prompt_all_parameters(self):
        '''Test with no-prompt and all parameters.'''

        cmdline_option_spec = {
            'swag_bucket': 'bucket_123',
            'aardvark_role': 'role_123',
            'db_uri': 'db_uri_123',
            'num_threads': 4
            }

        self.case_worker(
            cmdline_option_spec=cmdline_option_spec,
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_no_prompt_all_parameters_short(self):
        '''Test with no-prompt and short parameters.'''

        cmdline_option_spec = {
            'swag_bucket': 'bucket_123',
            'aardvark_role': 'role_123',
            'db_uri': 'db_uri_123',
            'num_threads': 4
            }

        self.case_worker(
            cmdline_option_spec=cmdline_option_spec,
            short_flags=True
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_no_prompt_no_swag(self):
        '''Test with no-prompt and all non-swag parameters.'''

        cmdline_option_spec = {
            'aardvark_role': 'role_123',
            'db_uri': 'db_uri_123',
            'num_threads': 4
            }

        self.case_worker(
            cmdline_option_spec=cmdline_option_spec,
            )


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TestConfigPrompt(TestConfigBase):
    '''Test cases for config with prompting.'''

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_prompted_defaults(self):
        '''Test with no parameters specified.'''

        self.case_worker(
            prompt=True
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_prompted_all_cmdline_parameters(self):
        '''Test with all parameters passed as options.'''

        cmdline_option_spec = {
            'swag_bucket': 'bucket_123',
            'aardvark_role': 'role_123',
            'db_uri': 'db_uri_123',
            'num_threads': 4
            }

        self.case_worker(
            cmdline_option_spec=cmdline_option_spec,
            prompt=True
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_prompted_no_swag(self):
        '''Test with all non-swag parameters interactively.'''

        input_option_spec = {
            'aardvark_role': 'role_123',
            'db_uri': 'db_uri_123',
            'num_threads': 4
            }

        self.case_worker(
            input_option_spec=input_option_spec,
            prompt=True
            )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Define test suites.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
load_case = unittest.TestLoader().loadTestsFromTestCase
all_suites = {
    'testconfignoprompt': load_case(TestConfigNoPrompt),
    'testconfigprompt': load_case(TestConfigPrompt)
    }

master_suite = unittest.TestSuite(all_suites.values())

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    unittest.main()
