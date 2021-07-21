import logging
import os

from dynaconf import Dynaconf, Validator

cwd_path = os.path.join(os.getcwd(), "settings.yaml")

settings = Dynaconf(
    envvar_prefix="AARDVARK",
    settings_files=[
        "settings.yaml",
        ".secrets.yaml",
        cwd_path,
        "/etc/aardvark/settings.yaml",
    ],
    env_switcher="AARDVARK_ENV",
    environments=True,
    validators=[
        Validator('AWS_ARN_PARTITION', default='aws'),
        Validator('AWS_REGION', default='us-east-1'),
        Validator('AWS_ARN_PARTITION', default='aws'),
        Validator('SQLALCHEMY_DATABASE_URI', default='sqlite:///aardvark.db'),
        Validator('UPDATER_NUM_THREADS', default=1),
    ],
)

log = logging.getLogger(__name__)


def create_config(
    aardvark_role: str = "",
    swag_bucket: str = "",
    swag_filter: str = "",
    swag_service_enabled_requirement: str = "",
    arn_partition: str = "",
    sqlalchemy_database_uri: str = "",
    sqlalchemy_track_modifications: bool = False,
    num_threads: int = 5,
    region: str = "",
    filename: str = "settings.yaml",
    environment: str = "default",
):
    if aardvark_role:
        settings.set("aws_rolename", aardvark_role)
    if arn_partition:
        settings.set("aws_arn_partition", arn_partition)
    if region:
        settings.set("aws_region", region)
    if swag_bucket:
        settings.set("swag.bucket", swag_bucket)
    if swag_filter:
        settings.set("swag.filter", swag_filter)
    if swag_service_enabled_requirement:
        settings.set(
            "swag.service_enabled_requirement", swag_service_enabled_requirement
        )
    if sqlalchemy_database_uri:
        settings.set("sqlalchemy_database_uri", sqlalchemy_database_uri)
    if sqlalchemy_track_modifications:
        settings.set("sqlalchemy_track_modifications", sqlalchemy_track_modifications)
    if num_threads:
        settings.set("updater_num_threads", num_threads)
    write_config(filename, environment=environment)


def find_legacy_config():
    """Search for config.py in order of preference and return path if it exists, else None"""
    CONFIG_PATHS = [
        os.path.join(os.getcwd(), "config.py"),
        "/etc/aardvark/config.py",
        "/apps/aardvark/config.py",
    ]
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None


def convert_config(
    filename: str,
    write: bool = False,
    output_filename: str = "settings.yaml",
    environment: str = "default",
):
    """Convert a pre-1.0 config to a YAML config file"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("aardvark.config.legacy", filename)
    old_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_config)

    try:
        settings.set("aws_rolename", old_config.ROLENAME)
    except AttributeError:
        pass

    try:
        settings.set("aws_region", old_config.REGION)
    except AttributeError:
        pass

    try:
        settings.set("aws_arn_partition", old_config.ARN_PARTITION)
    except AttributeError:
        pass

    try:
        settings.set("sqlalchemy_database_uri", old_config.SQLALCHEMY_DATABASE_URI)
    except AttributeError:
        pass

    try:
        settings.set(
            "sqlalchemy_track_modifications", old_config.SQLALCHEMY_TRACK_MODIFICATIONS
        )
    except AttributeError:
        pass

    try:
        settings.set("swag.bucket", old_config.SWAG_BUCKET)
    except AttributeError:
        pass

    try:
        settings.set("swag.opts", old_config.SWAG_OPTS)
    except AttributeError:
        pass

    try:
        settings.set("swag.filter", old_config.SWAG_FILTER)
    except AttributeError:
        pass

    try:
        settings.set(
            "swag.service_enabled_requirement",
            old_config.SWAG_SERVICE_ENABLED_REQUIREMENT,
        )
    except AttributeError:
        pass

    try:
        settings.set("updater_failing_arns", old_config.FAILING_ARNS)
    except AttributeError:
        pass

    try:
        settings.set("updater_num_threads", old_config.NUM_THREADS)
    except AttributeError:
        pass

    if write:
        write_config(output_filename, environment=environment)


def open_config(filepath: str):
    settings.load_file(filepath)


def write_config(filename: str = "settings.yaml", environment: str = "default"):
    from dynaconf import loaders
    from dynaconf.utils.boxing import DynaBox

    data = settings.as_dict()
    log.info("writing config file to %s", filename)
    loaders.write(filename, DynaBox(data).to_dict(), env=environment)
