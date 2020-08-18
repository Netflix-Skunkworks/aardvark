import configparser

from aardvark.config import AARDVARK_CONFIG


class AardvarkPlugin:
    def __init__(self, alternate_config: configparser.SectionProxy = None):
        if alternate_config:
            self.config = alternate_config
        else:
            self.config = AARDVARK_CONFIG
