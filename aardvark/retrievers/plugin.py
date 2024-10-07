from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aardvark.plugins import AardvarkPlugin

if TYPE_CHECKING:
    from dynaconf.utils import DynaconfDict

log = logging.getLogger("aardvark")


class RetrieverPlugin(AardvarkPlugin):
    _name: str

    def __init__(self, name: str, alternative_config: DynaconfDict = None):
        super().__init__(alternative_config=alternative_config)
        self._name = name

    async def run(self, arn: str, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def name(self):
        return self._name

    def __str__(self):
        return f"Retriever({self.name})"
