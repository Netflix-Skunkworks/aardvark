"""
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

import confuse

from aardvark.plugins import AardvarkPlugin

log = logging.getLogger("aardvark")


class RetrieverPlugin(AardvarkPlugin):
    def __init__(self, alternative_config: confuse.Configuration = None):
        super().__init__(alternative_config)

    async def run(self, arn: str, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()
