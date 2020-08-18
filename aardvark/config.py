import configparser

import pkg_resources

# TODO(psanders): Allow for configurable config path
config: configparser.ConfigParser = configparser.ConfigParser()
config_file_path: str = "/".join(["config.ini"])
config_path: str = pkg_resources.resource_filename("aardvark", config_file_path)
config.read(config_path)
print(config_path)

try:
    print("trying to get the updater config")
    UPDATER_CONFIG: configparser.SectionProxy = config["updater"]
except Exception:
    exit(-1)


try:
    print("trying to get the aardvark config")
    AARDVARK_CONFIG: configparser.SectionProxy = config["aardvark"]
except Exception:
    exit(-1)


def get_config(component: str) -> configparser.SectionProxy:
    """
    Returns a different config set based on the provided environment.
    This is used for testing.
    """
    return config[component]


def get_config_from_file(filepath: str, component: str) -> configparser.SectionProxy:
    """
    This returns an entirely different configuration value, and utilizes the environemnt provided
    as an index into that configuration file. This is used via the CLI.
    """
    alternative_config = configparser.ConfigParser()
    alternative_config.read(filepath)
    return alternative_config[component]
