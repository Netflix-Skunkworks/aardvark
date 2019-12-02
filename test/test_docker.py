'''
Test cases for docker container creation.
'''

#adding for py3 support
from __future__ import absolute_import

import logging
import os
import random
import re
import shutil
import tempfile

import unittest

import pexpect


# Configure logging. Troubleshooting the pexpect interactions in
# particular needs a lot of tracing.
FILENAME = os.path.split(__file__)[-1]
shandler = logging.StreamHandler()
sformatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
shandler.setFormatter(sformatter)
logger = logging.getLogger()
logger.setLevel(logging.WARNING)
# logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
logger.addHandler(shandler)

# These need to be removed from the test run environment if present
# before configuring the environment for the pexpect call to the make
# process.
BUILD_CONTROL_ENV_VARIABLES = [
    'AARDVARK_ROLE',
    'AARDVARK_DB_URI',
    'SWAG_BUCKET',
    'AARDVARK_IMAGES_TAG'
    ]

# We'll copy the docker directory contents to the temporary working
# directory each time.
DOCKER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    "docker"
    )

# An index of possible docker images and their pseudo-artifacts.
# TODO: Preserved for reference purposes; the DOCKER_IMAGES variable
# isn't used as of this commenting.
DOCKER_IMAGES = {
    'aardvark-base': 'aardvark-base-docker-build',
    'aardvark-data-volume': 'aardvark-data-docker-build',
    'aardvark-data-volume': 'aardvark-data-docker-run',
    'aardvark-apiserver': 'aardvark-apiserver-docker-build',
    'aardvark-collector': 'aardvark-collector-docker-build',
    }

# The subdirectory of the working directory where pseudo-artifacts
# are created.
ARTIFACT_DIRECTORY = 'artifacts'

# A few constants that are checked when testing container
# config settings.
CONTAINER_CONFIG_PATH = '/etc/aardvark/config.py'

EXPECTED_SQLITE_DB_URI = 'sqlite:////usr/share/aardvark-data/aardvark.db'
EXPECTED_SQL_TRACK_MODS = False

# Making targets can take some time, and depends on network connection
# speed. Set the NETWORK_SPEED_FACTOR environment variable to increase
# if necessary.
PEXPECT_TIMEOUTS = {
    'default': 30,
    'container_command': 2,
    'aardvark': 30,
    'aardvark-all': 240,
    'aardvark-base': 180,
    'aardvark-sqlite': 300,
    }
NETWORK_SPEED_FACTOR = 1.0

# The key that will uniquely identify a docker construct of the
# indicated type.
UID_KEY = {
    'image': 'id',
    'container': 'id',
    'volume': 'name'
    }

# A message for unittest.skipIf.
SKIP_NO_IMAGES_TAG_MSG = (
    "Remove aardvark-*:latest images and the aardvark-data volume as desired"
    " and set the RUN_AARDVARK_DOCKER_TESTS_NO_IMAGES_TAG environment variable"
    " to 1 to enable tests that don't set the AARDVARK_IMAGES_TAG."
    )


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def sqlite_db_uri(path):
    '''Return the default db_uri value at runtime.'''
    return 'sqlite:///{}/aardvark.db'.format(path)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def copy_recipes(src, dest):
    '''Copy Make- and Dockerfiles from src to dest'''
    [
        shutil.copyfile(os.path.join(src, f), os.path.join(dest, f))
        for f in os.listdir(src)
        if (f.startswith("Dockerfile") or f.startswith("Makefile"))
        ]


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def interact(
        spawn,
        command,
        response_filter=None,
        timeout=PEXPECT_TIMEOUTS['container_command']
        ):  # pylint: disable=bad-continuation
    '''Send command to spawn and return filtered response.'''

    def default_response_filter(response):
        '''Define a default method for the response filter.'''
        return response

    if not response_filter:
        response_filter = default_response_filter

    shell_prompt = r'root@\w+:[\S]+# '
    expect_prompt = [shell_prompt, pexpect.EOF, pexpect.TIMEOUT]

    eof_position = expect_prompt.index(pexpect.EOF)
    timeout_position = expect_prompt.index(pexpect.TIMEOUT)

    eof_msg_template = 'unexpected EOF in pexpect connection to {}'
    responses = []
    result = None

    logger.info('COMMAND:\t%s', command)
    spawn.sendline(command)

    # Read until we time out, indicating no more lines are pending;
    # watch for the response that has our command echoed on one line
    # and our response on the next.
    while(True):

        prompt_index = spawn.expect(expect_prompt, timeout=timeout)

        import json
        if prompt_index < timeout_position:
            responses.append(
                spawn.before.decode('utf-8').replace('\r\n', '\n')
                )
            # print '--------'
            logger.debug('    BEFORE: %s', json.dumps(responses[-1]))
            logger.debug(
                '    AFTER: %s',
                json.dumps(spawn.after.decode("utf-8").replace('\r\n', '\n'))
                )
            if command and responses[-1].startswith(command + '\n'):
                result = response_filter(
                    responses[-1].replace(command + '\n', '', 1).strip()
                    )
                logger.info("    result found: %s", result)
            # print '--------\n'

        elif prompt_index == timeout_position:
            logger.debug('    TIMEOUT')
            break

        elif prompt_index == eof_position:
            raise RuntimeError(eof_msg_template.format(command))

    logger.debug('Responses:\n%s', '\n'.join(responses))
    logger.debug('')

    return result


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TestDockerBase(unittest.TestCase):
    '''Base class for docker container construction test cases.'''

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def setUpClass(cls):
        '''Test case class common fixture setup.'''

        # These will record the constructs at class start; we'll log
        # any discrepancy at class termination.
        cls.constructs = {'original': {}, 'current': {}}

        for construct_type in ['image', 'container', 'volume']:
            cls.constructs['original'][construct_type] = (
                cls.get_docker_constructs(construct_type)
                )
            cls.constructs['current'][construct_type] = list(
                cls.constructs['original'][construct_type]
                )

        cls.tmpdir = tempfile.mkdtemp()

        cls.original_working_dir = os.getcwd()
        os.chdir(cls.tmpdir)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def tearDownClass(cls):
        '''Test case class common fixture teardown.'''

        os.chdir(cls.original_working_dir)
        cls.clean_tmpdir()
        os.rmdir(cls.tmpdir)

        cls.warn_on_hanging_constructs()

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def warn_on_hanging_constructs(cls):
        '''Log warnings for undeleted docker constructs created by tests.'''

        construct_fields = {
            'container': ['id', 'name'],
            'image': ['id', 'name', 'tag'],
            'volume': ['name'],
            }

        hanging_constructs = {}

        for construct_type in construct_fields.keys():

            hanging_constructs[construct_type] = [
                c for c in cls.constructs['current'][construct_type]
                if c[UID_KEY[construct_type]] not in [
                    x[UID_KEY[construct_type]]
                    for x in cls.constructs['original'][construct_type]
                    ]
                ]

            for construct in hanging_constructs[construct_type]:
                logger.warning(
                    'a failed test case left behind %s:\t%s',
                    construct_type,
                    '\t'.join([
                        construct[field]
                        for field in construct_fields[construct_type]
                        ])
                    )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def clean_tmpdir(cls):
        '''Remove all content from cls.tmpdir.'''

        for root, dirs, files in os.walk(cls.tmpdir, topdown=False):

            for name in files:

                path = os.path.join(root, name)
                os.remove(path)

            for name in dirs:

                path = os.path.join(root, name)
                if os.path.islink(path):
                    os.remove(path)
                else:
                    os.rmdir(path)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def setUp(self):
        '''Test case common fixture setup.'''

        self.clean_tmpdir()

        # This copies the Makefile and the Dockerfiles.
        copy_recipes(DOCKER_PATH, self.tmpdir)

        # We track to make sure we don't disturb any files that were
        # present in the working directory.
        self.initial_contents = os.listdir(self.tmpdir)

        # If true, we will stop containers and delete images created
        # during each test case.
        self.delete_artifacts = True

        # A (almost certainly) unique string for unique test case
        # artifact names.
        self.testcase_tag = (
            'test{:08X}'.format(random.randrange(16 ** 8)).lower()
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def tearDown(self):
        '''Test case common fixture teardown.'''

        logger.info("======= tearDown: %s", self.delete_artifacts)

        self.log_docker_constructs()

        new_containers = self.new_constructs('container')
        new_images = self.new_constructs('image')
        new_volumes = self.new_constructs('volume')

        if self.delete_artifacts:
            # Every case should clean up its docker images and containers.

            for container in new_containers:
                # These should have been launched with the --rm flag,
                # so they should be removed once stopped.
                logger.info("REMOVING %s", container['id'])
                pexpect.run('docker stop {}'.format(container['id']))

            for image in new_images:
                logger.info("REMOVING %s", image['id'])
                pexpect.run('docker rmi {}'.format(image['id']))

            for volume in new_volumes:
                logger.info("REMOVING %s", volume['name'])
                pexpect.run('docker volume rm {}'.format(volume['name']))

        else:
            # We'll leave behind any new docker constructs, so we need
            # to update the "original docker volumes".
            self.constructs['current']['container'].extend(new_containers)
            self.constructs['current']['image'].extend(new_images)
            self.constructs['current']['volume'].extend(new_volumes)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def log_docker_constructs(self, **kwargs):
        '''Log docker construct status.'''

        def log_listing(caption, records, *fields):
            '''Helper method for log message construction.'''

            return '{}:\n    '.format(caption) + '\n    '.join([
                '\t'.join(
                    [record[field] for field in fields]
                    ) for record in records
                ])

        construct_fields = {
            'container': ['id', 'name'],
            'image': ['id', 'name', 'tag'],
            'volume': ['name'],
            }

        for construct_type in construct_fields.keys():

            logger.info("------------%ss:", construct_type)
            logger.info(log_listing(
                'Original',
                self.constructs['original'][construct_type],
                *construct_fields[construct_type]
                ))
            logger.info(log_listing(
                'Current',
                self.get_docker_constructs(construct_type),
                *construct_fields[construct_type]
                ))
            logger.info(log_listing(
                'New',
                self.new_constructs(construct_type),
                *construct_fields[construct_type]
                ))

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @classmethod
    def get_docker_constructs(cls, construct_type, *expected_constructs):
        '''Get a list of images, containers or volumes.'''
        return {
            'image': cls.get_docker_image_list,
            'container': cls.get_docker_container_list,
            'volume': cls.get_docker_volume_list
            }[construct_type](*expected_constructs)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @staticmethod
    def get_docker_image_list(*expected_images):
        '''Get the output from "docker image ls" for specified image names.'''

        image_listing_pattern = (
            r'(?P<name>[^\s]+)\s+'
            r'(?P<tag>[^\s]+)\s+'
            r'(?P<id>[0-9a-f]+)\s+'
            r'(?P<created>.+ago)\s+'
            r'(?P<size>[^\s]+)'
            r'\s*$'
            )
        image_listing_re = re.compile(image_listing_pattern)

        docker_images_response = pexpect.run('docker image ls')

        image_list = []
        expected_image_nametag_pairs = [
            (x.split(':') + ['latest'])[0:2] for x in expected_images
            ] if expected_images else None

        docker_images_response_l = docker_images_response.decode('utf-8').split('\n')

        for line in docker_images_response_l:
            match = image_listing_re.match(line)
            if (
                    match and (
                        not expected_images or [
                            match.groupdict()['name'], match.groupdict()['tag']
                            ] in expected_image_nametag_pairs
                        )
                    ):
                image_list.append(match.groupdict())

        return image_list

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @staticmethod
    def get_docker_container_list(*expected_containers):
        '''Get the output from "docker ps -a" for specified container names.'''

        container_listing_pattern = (
            r'(?P<id>[0-9a-f]+)\s+'
            r'(?P<image>[^\s]+)\s+'
            r'(?P<command>"[^"]+")\s+'
            r'(?P<created>.+ago)\s+'
            r'(?P<status>(Created|Exited.*ago|Up \d+ \S+))\s+'
            r'(?P<ports>[^\s]+)?\s+'
            r'(?P<name>[a-z]+_[a-z]+)'
            # r'\s*$'
            )
        container_listing_re = re.compile(container_listing_pattern)

        docker_containers_response = pexpect.run('docker ps -a')

        container_list = []
        # expected_container_nametag_pairs = [
        #     (x.split(':') + ['latest'])[0:2] for x in expected_containers
        #     ] if expected_containers else []

        docker_containers_response_l = docker_containers_response.decode('utf-8').split('\n')

        for line in docker_containers_response_l:
            match = container_listing_re.match(line)
            if match:
                container_list.append(match.groupdict())

        return container_list

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @staticmethod
    def get_docker_volume_list(*expected_volumes):
        '''Get the output from "docker volume ls" for specified volumes.'''

        volume_listing_pattern = (
            r'(?P<driver>\S+)\s+'
            r'(?P<name>\S+)'
            # r'\s*$'
            )
        volume_listing_re = re.compile(volume_listing_pattern)

        docker_volumes_response = pexpect.run('docker volume ls')

        docker_volumes_response_l = docker_volumes_response.decode('utf-8').split('\n')

        volume_list = []

        for line in docker_volumes_response_l:
            match = volume_listing_re.match(line)
            if match:
                volume_list.append(match.groupdict())

        return volume_list

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def require_filenames_in_directory(self, patterns=None, directory='.'):
        '''Check that filenames are found in the indicated directory.

        Each pattern in the list of patterns must match exactly one
        file in the indicated directory.

        '''

        failure_string_template = (
            'Unexpected or missing filename match result in {}'
            ' for pattern r\'{}\':\n{}\n'
            'Directory contents:\n{}'
            )

        if patterns:
            self.assertTrue(os.path.exists(directory))
            all_filenames = os.listdir(directory)
            for pattern in patterns:
                matching_files = [
                    x for x in all_filenames
                    if re.match(pattern, x)
                    ]
                self.assertTrue(
                    len(matching_files) == 1,
                    failure_string_template.format(
                        directory,
                        pattern,
                        matching_files,
                        os.listdir(directory)
                        )
                    )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def new_constructs(self, construct_type):
        '''Get a list of images, containers or volumes not already recorded.'''
        return [
            c for c in self.get_docker_constructs(construct_type)
            if c[UID_KEY[construct_type]] not in [
                o[UID_KEY[construct_type]]
                for o in self.constructs['original'][construct_type]
                ]
            ]

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def get_container_details(self, image):
        '''Run a docker container shell and retrieve several details.'''

        # (detail name, command, result filter) for extracting details
        # from container command lines.
        shell_commands = (
            ('pwd', 'pwd', None),
            ('config_file', 'ls {}'.format(CONTAINER_CONFIG_PATH), None),
            ('config_contents', 'cat {}'.format(CONTAINER_CONFIG_PATH), None),
            )

        command = "docker run --rm -it {} bash".format(image)
        logger.info('IMAGE: %s', image)
        logger.info('CONTAINER LAUNCH COMMAND: %s', command)
        spawn = pexpect.spawn(command)

        container_details = {}

        for field, shell_command, response_filter in shell_commands:
            container_details[field] = interact(
                spawn, shell_command, response_filter
                )

        # Exit the container.
        spawn.sendcontrol('d')

        # "Expand" the config records if we found a config file.
        if container_details['config_file'] == CONTAINER_CONFIG_PATH:
            try:
                exec(container_details['config_contents'], container_details)
            except SyntaxError:
                pass
            # The '__builtins__' are noise:
            if '__builtins__' in container_details:
                del container_details['__builtins__']

        return container_details

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def check_container_details(self, image, expected_details=None):
        '''Validate docker container details.'''

        # A helper method to retrieve container details of interest,
        # necessary for configuration items that aren't simple config
        # file values; e.g. "SWAG_BUCKET".
        # As written, this won't allow tests to catch *missing*
        # entries if the *expected* value is None.
        def get_detail_value(data, detail):
            '''A helper method to retrieve container details of interest.'''

            def default_get_detail_value_method(data):
                '''Define a default method for get_detail_value.'''
                return data.get(detail)

            method = {
                'SWAG_BUCKET': lambda data: (
                    data.get('SWAG_OPTS') or {}
                    ).get('swag.bucket_name')
                }.get(detail)

            if method is None:
                method = default_get_detail_value_method

            return method(data)

        image_name, image_tag = image.split(':')

        expected_details = expected_details or {}
        assert '_common' in expected_details

        expected_container_details = dict(expected_details['_common'])
        if image_name in expected_details:
            expected_container_details.update(expected_details[image_name])

        container_details = self.get_container_details(image)

        clean_comparison = {
            'image': image,
            'missing': {},
            'incorrect': {}
            }
        comparison = {
            'image': image,
            'missing': {},
            'incorrect': {}
            }

        for k, v in expected_container_details.items():

            logger.info(' -- checking configuration item %s...', k)
            logger.info('    expected: %s', v)

            actual = get_detail_value(container_details, k)

            # if k not in container_details:
            # TODO: Note that this fails if we're *expecting* None.
            if actual is None:
                comparison['missing'][k] = v
                logger.info('    actual: -')

            elif actual != v:
                comparison['incorrect'][k] = {
                    'expected': v,
                    'actual': actual
                    }
                logger.info(comparison['incorrect'][k])

            else:
                logger.info('    actual:   %s', actual)

        logger.info("comparing %s", image)
        logger.info(comparison)
        logger.info('')
        self.assertEqual(comparison, clean_comparison)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def case_worker(
            self,
            target,
            expected_artifacts=None,
            expected_docker_images=None,
            expected_details=None,
            expect_aardvark=True,
            add_env=None,
            set_images_tag=True,
            ):
        '''Carry out common test steps.
        '''

        logger.info(' -' * 8 + ' working case: %s' + ' -' * 8, target)

        # Unless we finish without a failure Exception, tell tearDown
        # not to clean up artifacts. We reset this below.
        self.delete_artifacts = False

        # A unique string to add to certain test case artifact names
        # to avoid clobbering/colliding.
        if set_images_tag:
            images_tag = self.testcase_tag
            logger.info('Test case images tag is %s', images_tag)
        else:
            images_tag = 'latest'
            logger.info('Default test case images tag will be "latest"')

        expected_artifacts = expected_artifacts or []
        expected_docker_images = expected_docker_images or []
        tagged_expected_docker_images = [
            x + ':{}'.format(images_tag)
            for x in expected_docker_images
            ]

        # expected_details is a two level dict so a straightforward
        # dict update isn't possible.
        expected_details = expected_details or {}
        expected_details['_common'] = expected_details.get('_common') or {}
        expected_details['_common']['config_file'] = CONTAINER_CONFIG_PATH

        # Environment variables to add to the pexpect interaction with
        # containers.
        add_env = dict(add_env or {})
        if set_images_tag:
            add_env = dict(add_env, AARDVARK_IMAGES_TAG=images_tag)

        # Fetch the default environment settings so we can update
        # those with specific case settings.
        spawn_env = dict(
            map(
                lambda x: x.strip().split('=', 1),
                pexpect.run('env').strip().decode("utf-8").split("\n")
                )
            )

        # Remove any build control variables we inherit from the test
        # environment - we want complete control over which are
        # visible to the make process in the pexpect call.
        spawn_env = {
            k: v for (k, v) in spawn_env.items()
            if k not in BUILD_CONTROL_ENV_VARIABLES
        }

        command = 'make {}'.format(target)
        logger.info('COMMAND: %s', command)

        # TODO: A sort of halfhearted attempt at adjusting for network
        # conditions. Need some kind of not-too-slow way to check for
        # network speed, say a sample download or something.
        (result, exitstatus) = pexpect.run(
            command,
            timeout=(
                PEXPECT_TIMEOUTS.get(target) or PEXPECT_TIMEOUTS['default'] *
                NETWORK_SPEED_FACTOR
                ),
            withexitstatus=True,
            env=dict(spawn_env, **add_env)
            )

        self.assertEqual(
            exitstatus, 0,
            'command "{}" exited with exit status {}'.format(
                command, exitstatus
                )
            )

        # Sanity check - we didn't delete the Makefile or any of the
        # Dockerfiles.
        self.assertEqual(
            [x for x in self.initial_contents if x not in os.listdir('.')],
            []
            )

        if expected_docker_images:
            self.assertCountEqual(
                [
                    [x['name'], x['tag']]
                    for x in self.get_docker_image_list(
                        *tagged_expected_docker_images
                        )
                    ],
                [x.split(':') for x in tagged_expected_docker_images]
                )

        for image in tagged_expected_docker_images:
            self.check_container_details(image, expected_details)

        if expect_aardvark:
            self.require_filenames_in_directory([r'aardvark$'])

        if expected_artifacts:
            self.require_filenames_in_directory(
                expected_artifacts,
                directory=ARTIFACT_DIRECTORY
                )

        # We made it through, tell tearDown we can clean up artifacts.
        self.delete_artifacts = True


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TestDockerContainerConstruction(TestDockerBase):
    '''Test cases for docker container construction.'''

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_make_aardvark(self):
        '''Test "make aardvark".'''

        self.case_worker(
            target='aardvark',
            expect_aardvark=True,
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_make_aardvark_base(self):
        '''Test "make aardvark-base".'''

        self.case_worker(
            target='aardvark-base',
            expected_docker_images=[
                'aardvark-base'
                ],
            expected_details={
                '_common': {
                    'pwd': '/etc/aardvark',
                    'NUM_THREADS': 5,
                    'ROLENAME': 'Aardvark',
                    'SQLALCHEMY_DATABASE_URI': EXPECTED_SQLITE_DB_URI,
                    'SQLALCHEMY_TRACK_MODIFICATIONS': EXPECTED_SQL_TRACK_MODS,
                    }
                },
            expected_artifacts=[
                'aardvark-base-docker-build'
                ],
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_make_aardvark_base_set_env_variables(self):
        '''Test "make aardvark-base" with build time environment variables.'''

        aardvark_db_uri = 'blort://blah.bleh.bloo/bing/bang/bong'
        aardvark_role = 'llama'
        swag_bucket = 'ponponpon'

        self.case_worker(
            target='aardvark-base',
            expected_docker_images=[
                'aardvark-base'
                ],
            expected_details={
                '_common': {
                    'pwd': '/etc/aardvark',
                    'NUM_THREADS': 5,
                    'ROLENAME': aardvark_role,
                    'SQLALCHEMY_DATABASE_URI': aardvark_db_uri,
                    'SQLALCHEMY_TRACK_MODIFICATIONS': EXPECTED_SQL_TRACK_MODS,
                    'SWAG_BUCKET': swag_bucket,
                    }
                },
            expected_artifacts=[
                'aardvark-base-docker-build'
                ],
            add_env={
                'AARDVARK_DB_URI': aardvark_db_uri,
                'AARDVARK_ROLE': aardvark_role,
                'SWAG_BUCKET': swag_bucket,
                }
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_make_aardvark_all(self):
        '''Test "make aardvark-all".'''

        self.case_worker(
            target='aardvark-all',
            expected_docker_images=[
                'aardvark-base',
                'aardvark-collector',
                'aardvark-apiserver',
                ],
            expected_details={
                '_common': {
                    'pwd': '/usr/share/aardvark-data',
                    'NUM_THREADS': 5,
                    'ROLENAME': 'Aardvark',
                    'SQLALCHEMY_DATABASE_URI': EXPECTED_SQLITE_DB_URI,
                    'SQLALCHEMY_TRACK_MODIFICATIONS': EXPECTED_SQL_TRACK_MODS,
                    },
                'aardvark-base': {
                    'pwd': '/etc/aardvark',
                    },
                },
            expected_artifacts=[
                'aardvark-base-docker-build',
                'aardvark-apiserver-docker-build',
                'aardvark-collector-docker-build',
                ],
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @unittest.skipIf(
        not os.environ.get('RUN_AARDVARK_DOCKER_TESTS_NO_IMAGES_TAG'),
        SKIP_NO_IMAGES_TAG_MSG
        )
    def test_make_aardvark_all_no_images_tag(self):
        '''Test "make aardvark-all" without specifying the images tag.'''

        self.case_worker(
            target='aardvark-all',
            expected_docker_images=[
                'aardvark-base',
                'aardvark-collector',
                'aardvark-apiserver',
                ],
            expected_details={
                '_common': {
                    'pwd': '/usr/share/aardvark-data',
                    'NUM_THREADS': 5,
                    'ROLENAME': 'Aardvark',
                    'SQLALCHEMY_DATABASE_URI': EXPECTED_SQLITE_DB_URI,
                    'SQLALCHEMY_TRACK_MODIFICATIONS': EXPECTED_SQL_TRACK_MODS,
                    },
                'aardvark-base': {
                    'pwd': '/etc/aardvark',
                    },
                },
            expected_artifacts=[
                'aardvark-base-docker-build',
                'aardvark-apiserver-docker-build',
                'aardvark-collector-docker-build',
                ],
            set_images_tag=False
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def test_make_aardvark_sqlite(self):
        '''Test "make aardvark-sqlite".'''

        self.case_worker(
            target='aardvark-sqlite',
            expected_docker_images=[
                'aardvark-base',
                'aardvark-data-init',
                'aardvark-collector',
                'aardvark-apiserver',
                ],
            expected_details={
                '_common': {
                    'pwd': '/usr/share/aardvark-data',
                    'NUM_THREADS': 5,
                    'ROLENAME': 'Aardvark',
                    'SQLALCHEMY_DATABASE_URI': EXPECTED_SQLITE_DB_URI,
                    'SQLALCHEMY_TRACK_MODIFICATIONS': EXPECTED_SQL_TRACK_MODS,
                    },
                'aardvark-base': {
                    'pwd': '/etc/aardvark',
                    },
                },
            expected_artifacts=[
                'aardvark-base-docker-build',
                'aardvark-data-docker-build',
                'aardvark-data-docker-run',
                'aardvark-apiserver-docker-build',
                'aardvark-collector-docker-build',
                ],
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @unittest.skipIf(
        not os.environ.get('RUN_AARDVARK_DOCKER_TESTS_NO_IMAGES_TAG'),
        SKIP_NO_IMAGES_TAG_MSG
        )
    def test_make_aardvark_sqlite_no_images_tag(self):
        '''Test "make aardvark-sqlite" without specifying the images tag.'''

        self.case_worker(
            target='aardvark-sqlite',
            expected_docker_images=[
                'aardvark-base',
                'aardvark-data-init',
                'aardvark-collector',
                'aardvark-apiserver',
                ],
            expected_details={
                '_common': {
                    'pwd': '/usr/share/aardvark-data',
                    'NUM_THREADS': 5,
                    'ROLENAME': 'Aardvark',
                    'SQLALCHEMY_DATABASE_URI': EXPECTED_SQLITE_DB_URI,
                    'SQLALCHEMY_TRACK_MODIFICATIONS': EXPECTED_SQL_TRACK_MODS,
                    },
                'aardvark-base': {
                    'pwd': '/etc/aardvark',
                    },
                },
            expected_artifacts=[
                'aardvark-base-docker-build',
                'aardvark-data-docker-build',
                'aardvark-data-docker-run',
                'aardvark-apiserver-docker-build',
                'aardvark-collector-docker-build',
                ],
            set_images_tag=False
            )


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Define test suites.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
load_case = unittest.TestLoader().loadTestsFromTestCase
all_suites = {
    'testdockercontainerconstruction': load_case(
        TestDockerContainerConstruction
        ),
    }

master_suite = unittest.TestSuite(all_suites.values())

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    unittest.main()
