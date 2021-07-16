from dynaconf import Dynaconf
from dynaconf import settings


class AardvarkPlugin:
    def __init__(self, alternative_config: Dynaconf = None):
        if alternative_config:
            self.config = alternative_config
        else:
            self.config = settings
