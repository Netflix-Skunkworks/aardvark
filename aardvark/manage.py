import asyncio
import click
import logging
import os
import queue
import threading
from typing import List

from aardvark import create_app, init_logging
from aardvark.exceptions import AardvarkException
from aardvark.config import create_config, convert_config, find_legacy_config
from aardvark.persistence.sqlalchemy import SQLAlchemyPersistence
from aardvark.retrievers.runner import RetrieverRunner

APP = None
log = logging.getLogger("aardvark")

ACCOUNT_QUEUE = queue.Queue()
QUEUE_LOCK = threading.Lock()
UPDATE_DONE = False

SWAG_REPO_URL = "https://github.com/Netflix-Skunkworks/swag-client"

LOCALDB = "sqlite"
DEFAULT_LOCALDB_FILENAME = "aardvark.db"

# Configuration default values.
DEFAULT_SWAG_BUCKET = "swag-data"
DEFAULT_AARDVARK_ROLE = "Aardvark"
DEFAULT_NUM_THREADS = 5


def get_app():
    global APP
    if not APP:
        APP = create_app()
    return APP


@click.group()
def cli():
    init_logging()


# All of these default to None rather than the corresponding DEFAULT_* values
# so we can tell whether they were passed or not. We don't prompt for any of
# the options that were passed as parameters.
@cli.command("config")
@click.option("--aardvark-role", "-a", type=str)
@click.option("--swag-bucket", "-b", type=str)
@click.option("--db-uri", "-d", type=str)
@click.option("--num-threads", type=int)
@click.option("--no-prompt", is_flag=True, default=False)
def config(aardvark_role, swag_bucket, db_uri, num_threads, no_prompt):
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
    default_db_uri = f"{LOCALDB}:///{os.getcwd()}/{DEFAULT_LOCALDB_FILENAME}"
    default_save_file = "settings.local.yaml"

    if no_prompt:  # Just take the parameters as currently constituted.
        aardvark_role = aardvark_role or DEFAULT_AARDVARK_ROLE
        num_threads = num_threads or DEFAULT_NUM_THREADS
        db_uri = db_uri or default_db_uri

        # If a swag bucket was specified we set write_swag here so it gets
        # written out to the config file below.
        bucket = swag_bucket or DEFAULT_SWAG_BUCKET
        save_file = default_save_file
    else:
        # This is essentially the same "param, or input, or default"
        # structure as the additional parameters below.
        if swag_bucket:
            bucket = swag_bucket
        else:
            print(f"\nAardvark can use SWAG to look up accounts. See {SWAG_REPO_URL}")
            use_swag = input("Do you use SWAG to track accounts? [yN]: ")
            if len(use_swag) > 0 and "yes".startswith(use_swag.lower()):
                bucket_prompt = f"SWAG bucket [{DEFAULT_SWAG_BUCKET}]: "
                bucket = input(bucket_prompt) or DEFAULT_SWAG_BUCKET
            else:
                bucket = ""

        aardvark_role_prompt = f"Role Name [{DEFAULT_AARDVARK_ROLE}]: "
        db_uri_prompt = f"Database URI [{default_db_uri}]: "
        num_threads_prompt = f"Worker Count [{DEFAULT_NUM_THREADS}]: "
        save_file_prompt = f"Config file location [{default_save_file}]: "

        aardvark_role = (
                aardvark_role or input(aardvark_role_prompt) or DEFAULT_AARDVARK_ROLE
        )
        db_uri = db_uri or input(db_uri_prompt) or default_db_uri
        num_threads = (
                num_threads or input(num_threads_prompt) or DEFAULT_NUM_THREADS
        )
        save_file = input(save_file_prompt) or default_save_file

    create_config(
        aardvark_role=aardvark_role,
        swag_bucket=bucket or "",
        swag_filter="",
        swag_service_enabled_requirement="",
        sqlalchemy_database_uri=db_uri,
        sqlalchemy_track_modifications=False,
        num_threads=num_threads,
        region="us-east-1",
        filename=save_file,
    )


@cli.command("update")
@click.option("--account", "-a", type=str, default=[], multiple=True)
@click.option("--arn", "-r", type=str, default=[], multiple=True)
def update(account: List[str], arn: List[str]):
    """
    Asks AWS for new Access Advisor information.
    """
    accounts = list(account)
    arns = list(arn)
    r = RetrieverRunner()
    try:
        asyncio.run(r.run(accounts=accounts, arns=arns))
    except KeyboardInterrupt:
        r.cancel()
    except AardvarkException as e:
        log.error(e)
        exit(1)


@cli.command("drop_db")
def drop_db():
    """Drops the database."""
    SQLAlchemyPersistence().teardown_db()


@cli.command("create_db")
def create_db():
    """Creates the database."""
    SQLAlchemyPersistence().init_db()


@cli.command("migrate_config")
@click.option("--environment", "-e", type=str, default="default")
@click.option("--config-file", "-c", type=str)
@click.option("--write/--no-write", type=bool, default=True)
@click.option("--output-file", "-o", type=str, default="settings.yaml")
def migrate_config(environment, config_file, write, output_file):
    if not config_file:
        config_file = find_legacy_config()
    convert_config(
        config_file,
        write=write,
        output_filename=output_file,
        environment=environment,
    )


if __name__ == "__main__":
    cli()
