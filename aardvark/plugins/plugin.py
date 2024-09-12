from __future__ import annotations

from typing import TYPE_CHECKING

from aardvark.config import settings

if TYPE_CHECKING:
    from dynaconf.utils import DynaconfDict


class AardvarkPlugin:
    def __init__(self, alternative_config: DynaconfDict | None = None):
        if alternative_config:
            self.config = alternative_config
        else:
            self.config = settings
