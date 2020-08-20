import configparser
import confuse

CONFIG: confuse.Configuration = confuse.Configuration("aardvark", __name__)
print(f"configuration directory is {CONFIG.config_dir()}")


def create_config(
    aardvark_role: str = "",
    swag_bucket: str = "",
    swag_filter: str = "",
    swag_service_enabled_requirement: str = "",
    arn_partition: str = "",
    sqlalchemy_database_uri: str = "",
    sqlalchemy_track_modifications: bool = False,
    num_threads: int = 5,
    no_prompt: bool = False,
    region: str = "",
    filename: str = "generated.yaml",
):
    if aardvark_role:
        CONFIG["aws"]["rolename"] = aardvark_role
    if swag_bucket:
        CONFIG["bucket"]["swag_bucket"] = swag_bucket
    if swag_filter:
        CONFIG["filter"]["swag_filter"] = swag_filter
    if swag_service_enabled_requirement:
        CONFIG["service_enabled_requirement"][
            "swag_service_enabled_requirement"
        ] = swag_service_enabled_requirement
    if sqlalchemy_database_uri:
        CONFIG["sqlalchemy"]["sqlalchemy_database_uri"] = sqlalchemy_database_uri
    if sqlalchemy_track_modifications:
        CONFIG["sqlalchemy"]["sqlalchemy_track_modifications"] = sqlalchemy_track_modifications
    if num_threads:
        CONFIG["updater"]["num_threads"] = num_threads
    if arn_partition:
        CONFIG["aws"]["arn_partition"] = arn_partition
    if region:
        CONFIG["aws"]["region"] = region
    with open(filename, "w") as f:
        f.write(CONFIG.dump(full=False))


def get_config(component: str) -> configparser.SectionProxy:
    """
    Returns a different config set based on the provided environment.
    This is used for testing.
    """
    return CONFIG[component]


def get_config_from_file(filepath: str, component: str) -> configparser.SectionProxy:
    """
    This returns an entirely different configuration value, and utilizes the environemnt provided
    as an index into that configuration file. This is used via the CLI.
    """
    alternative_config = configparser.ConfigParser()
    alternative_config.read(filepath)
    return alternative_config[component]


def open_config(filepath: str):
    CONFIG.read(filepath)
