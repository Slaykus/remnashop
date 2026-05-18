from typing import Final

from src.application.common import Interactor

from .commands.reset_purchase import PurchaseTrafficReset

NODE_QUOTA_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    PurchaseTrafficReset,
)
