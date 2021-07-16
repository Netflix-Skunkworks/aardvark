r"""
              ,-~~~~-,
        .-~~~;        ;~~~-.
       /    /          \    \
      {   .'{  O    O  }'.   }
       `~`  { .-~~~~-. }  `~`
            ;/        \;
           /'._  ()  _.'\
          /    `~~~~`    \
         ;                ;
         {                }
         {     }    {     }
         {     }    {     }
         /     \    /     \
        { { {   }~~{   } } }
         `~~~~~`    `~~~~~`
           (`"======="`)
           (_.=======._)

Good boy.
"""

import logging
from typing import Any, Dict

from dynaconf import Dynaconf

from aardvark.plugins import AardvarkPlugin

log = logging.getLogger("aardvark")


class RetrieverPlugin(AardvarkPlugin):
    _name: str

    def __init__(self, name: str, alternative_config: Dynaconf = None):
        super().__init__(alternative_config=alternative_config)
        self._name = name

    async def run(self, arn: str, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()

    @property
    def name(self):
        return self._name

    def __str__(self):
        return f"Retriever({self.name})"
