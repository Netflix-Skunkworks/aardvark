import confuse

from aardvark.configuration import CONFIG


class AardvarkPlugin:
    def __init__(self, alternative_config: confuse.Configuration = None):
        if alternative_config:
            self.config = alternative_config
        else:
            self.config = CONFIG
