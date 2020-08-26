from typing import Any, Dict, List, Optional

import confuse

from aardvark.plugins import AardvarkPlugin


class PersistencePlugin(AardvarkPlugin):
    def __init__(self, alternative_config: confuse.Configuration = None):
        super().__init__(alternative_config=alternative_config)

    def init_db(self):
        raise NotImplementedError()

    def teardown_db(self):
        raise NotImplementedError()

    def get_role_data(
        self,
        page: int = 0,
        count: int = 0,
        combine: bool = False,
        phrase: str = "",
        arns: Optional[List[str]] = None,
        regex: str = "",
    ) -> Dict[str, Any]:
        raise NotImplementedError()

    def store_role_data(self, access_advisor_data: Dict[str, Any]) -> None:
        raise NotImplementedError()

    def _combine_results(self, access_advisor_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()
