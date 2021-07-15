import logging
import os

import confuse

CONFIG: confuse.Configuration = confuse.Configuration("aardvark", __name__)
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
        CONFIG["aws"]["rolename"] = aardvark_role
    if arn_partition:
        CONFIG["aws"]["arn_partition"] = arn_partition
    if region:
        CONFIG["aws"]["region"] = region
    if swag_bucket:
        CONFIG["swag"]["bucket"] = swag_bucket
    if swag_filter:
        CONFIG["swag"]["filter"] = swag_filter
    if swag_service_enabled_requirement:
        CONFIG["swag"]["service_enabled_requirement"] = swag_service_enabled_requirement
    if sqlalchemy_database_uri:
        CONFIG["sqlalchemy"]["database_uri"] = sqlalchemy_database_uri
    if sqlalchemy_track_modifications:
        CONFIG["sqlalchemy"]["track_modifications"] = sqlalchemy_track_modifications
    if num_threads:
        CONFIG["updater"]["num_threads"] = num_threads
    with open(filename, "w") as f:
        f.write(CONFIG.dump(full=False))


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
        CONFIG["aws"]["rolename"] = old_config.ROLENAME
    except AttributeError:
        pass

    try:
        CONFIG["aws"]["region"] = old_config.REGION
    except AttributeError:
        pass

    try:
        CONFIG["aws"]["arn_partition"] = old_config.ARN_PARTITION
    except AttributeError:
        pass

    try:
        CONFIG["sqlalchemy"]["database_uri"] = old_config.SQLALCHEMY_DATABASE_URI
    except AttributeError:
        pass

    try:
        CONFIG["sqlalchemy"]["track_modifications"] = old_config.SQLALCHEMY_TRACK_MODIFICATIONS
    except AttributeError:
        pass

    try:
        CONFIG["swag"]["bucket"] = old_config.SWAG_BUCKET
    except AttributeError:
        pass

    try:
        CONFIG["swag"]["opts"] = old_config.SWAG_OPTS
    except AttributeError:
        pass

    try:
        CONFIG["swag"]["filter"] = old_config.SWAG_FILTER
    except AttributeError:
        pass

    try:
        CONFIG["swag"]["service_enabled_requirement"] = old_config.SWAG_SERVICE_ENABLED_REQUIREMENT
    except AttributeError:
        pass

    try:
        CONFIG["updater"]["failing_arns"] = old_config.FAILING_ARNS
    except AttributeError:
        pass

    try:
        CONFIG["updater"]["num_threads"] = old_config.NUM_THREADS
    except AttributeError:
        pass

    try:
        CONFIG["logging"] = old_config.LOG_CFG
    except AttributeError:
        pass

    log.debug("generated config: %s", CONFIG.dump(full=False))
    if write:
        if not output_filename:
            output_filename = os.path.join(CONFIG.config_dir(), confuse.CONFIG_FILENAME)
        log.info(f"writing new configuration to {output_filename}...")
        with open(output_filename, 'w') as f:
            f.write(CONFIG.dump(full=False))


def open_config(filepath: str):
    CONFIG.read(filepath)


legacy_config_file = find_legacy_config()
if legacy_config_file:
    log.warning("legacy configuration file detected: %s", legacy_config_file)
    convert_config(legacy_config_file, write=True)
