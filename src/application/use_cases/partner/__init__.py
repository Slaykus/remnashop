from typing import Final

from src.application.common import Interactor

from .commands.manage import (
    CreatePartner,
    MarkPartnerEarningsAvailable,
    PayPartner,
    UpdatePartnerTerms,
)
from .queries.list import GetPartnerOverview, GetPartners

PARTNER_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    CreatePartner,
    UpdatePartnerTerms,
    PayPartner,
    MarkPartnerEarningsAvailable,
    GetPartners,
    GetPartnerOverview,
)
