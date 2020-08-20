from typing import Any, Dict, List, Optional

from aardvark.plugins import AardvarkPlugin


class PersistencePlugin(AardvarkPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init_db(self):
        raise NotImplementedError()

    def teardown_db(self):
        raise NotImplementedError()

    def remove(self):
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

    # @staticmethod
    # def update(*args, **kwargs):
    #     raise NotImplementedError()
    #
    # @staticmethod
    # def delete(*args, **kwargs):
    #     raise NotImplementedError()
    #
    # @staticmethod
    # def get_or_create(*args, **kwargs):
    #     raise NotImplementedError()
    #
    # @staticmethod
    # def create_or_update(*args, **kwargs):
    #     raise NotImplementedError()
