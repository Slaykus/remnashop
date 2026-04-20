from typing import Final

from src.application.common import Interactor

from .commands.reset_purchase import PurchaseTrafficReset

YANDEX_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    PurchaseTrafficReset,
)
