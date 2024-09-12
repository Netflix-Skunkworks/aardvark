from __future__ import annotations

from typing import TYPE_CHECKING

from aardvark.plugins import AardvarkPlugin

if TYPE_CHECKING:
    from dynaconf import Dynaconf


class PersistencePlugin(AardvarkPlugin):
    def __init__(self, alternative_config: 'Dynaconf' = None):
        super().__init__(alternative_config=alternative_config)

    def init_db(self):
        raise NotImplementedError

    def teardown_db(self):
        raise NotImplementedError

    def get_role_data(
        self,
        *,
        page: int = 0,
        count: int = 0,
        combine: bool = False,
        phrase: str = "",
        arns: list[str] | None = None,
        regex: str = "",
    ) -> dict[str, any]:
        raise NotImplementedError

    def store_role_data(self, access_advisor_data: dict[str, any]) -> None:
        raise NotImplementedError

    def _combine_results(self, access_advisor_data: dict[str, any]) -> dict[str, any]:
        raise NotImplementedError
