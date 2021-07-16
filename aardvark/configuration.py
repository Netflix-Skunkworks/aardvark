import logging
import os

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="AARDVARK",
    settings_files=['config.yaml', '.secrets.yaml'],
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
    filename: str = "generated.yaml",
):
    if aardvark_role:
        settings["aws"]["rolename"] = aardvark_role
    if arn_partition:
        settings["aws"]["arn_partition"] = arn_partition
    if region:
        settings["aws"]["region"] = region
    if swag_bucket:
        settings["swag"]["bucket"] = swag_bucket
    if swag_filter:
        settings["swag"]["filter"] = swag_filter
    if swag_service_enabled_requirement:
        settings["swag"]["service_enabled_requirement"] = swag_service_enabled_requirement
    if sqlalchemy_database_uri:
        settings["sqlalchemy"]["database_uri"] = sqlalchemy_database_uri
    if sqlalchemy_track_modifications:
        settings["sqlalchemy"]["track_modifications"] = sqlalchemy_track_modifications
    if num_threads:
        settings["updater"]["num_threads"] = num_threads
    write_config(filename)


def find_legacy_config():
    """Search for config.py in order of preference and return path if it exists, else None"""
    CONFIG_PATHS = [os.path.join(os.getcwd(), 'config.py'),
                    '/etc/aardvark/config.py',
                    '/apps/aardvark/config.py']
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None


def convert_config(filename: str, write: bool = False, output_filename: str = ""):
    """Convert a pre-1.0 config to a YAML config file"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("aardvark.config.legacy", filename)
    old_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_config)

    try:
        settings["aws"]["rolename"] = old_config.ROLENAME
    except AttributeError:
        pass

    try:
        settings["aws"]["region"] = old_config.REGION
    except AttributeError:
        pass

    try:
        settings["aws"]["arn_partition"] = old_config.ARN_PARTITION
    except AttributeError:
        pass

    try:
        settings["sqlalchemy"]["database_uri"] = old_config.SQLALCHEMY_DATABASE_URI
    except AttributeError:
        pass

    try:
        settings["sqlalchemy"]["track_modifications"] = old_config.SQLALCHEMY_TRACK_MODIFICATIONS
    except AttributeError:
        pass

    try:
        settings["swag"]["bucket"] = old_config.SWAG_BUCKET
    except AttributeError:
        pass

    try:
        settings["swag"]["opts"] = old_config.SWAG_OPTS
    except AttributeError:
        pass

    try:
        settings["swag"]["filter"] = old_config.SWAG_FILTER
    except AttributeError:
        pass

    try:
        settings["swag"]["service_enabled_requirement"] = old_config.SWAG_SERVICE_ENABLED_REQUIREMENT
    except AttributeError:
        pass

    try:
        settings["updater"]["failing_arns"] = old_config.FAILING_ARNS
    except AttributeError:
        pass

    try:
        settings["updater"]["num_threads"] = old_config.NUM_THREADS
    except AttributeError:
        pass

    try:
        settings["logging"] = old_config.LOG_CFG
    except AttributeError:
        pass

    if write:
        write_config(output_filename)


def open_config(filepath: str):
    settings.load_file(filepath)


def write_config(filename: str):
    from dynaconf import loaders
    from dynaconf import settings as dcsettings
    from dynaconf.utils.boxing import DynaBox

    if not filename:
        filename = "config.yaml"
    log.info("writing config file to %s", filename)
    data = dcsettings.as_dict()
    loaders.write(filename, DynaBox(data).to_dict())


# legacy_config_file = find_legacy_config()
# if legacy_config_file:
#     log.warning("legacy configuration file detected: %s", legacy_config_file)
#     convert_config(legacy_config_file, write=True)
