import confuse

from aardvark.configuration import CONFIG


class AardvarkPlugin:
    def __init__(self, alternate_config: confuse.Configuration = None):
        if alternate_config:
            self.config = alternate_config
        else:
            self.config = CONFIG
