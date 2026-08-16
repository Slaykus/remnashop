from typing import Final

from src.application.common import Interactor

from .commands.manage import (
    CreatePartner,
    CreatePartnerLink,
    MarkPartnerEarningsAvailable,
    PayPartner,
    RequestPayout,
    SavePayoutDetails,
    SetLinkBonus,
    ToggleLinkOwner,
    UpdatePartnerTerms,
)
from .queries.list import GetPartnerOverview, GetPartners, GetPartnersComparison

PARTNER_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    CreatePartner,
    CreatePartnerLink,
    UpdatePartnerTerms,
    PayPartner,
    RequestPayout,
    SavePayoutDetails,
    SetLinkBonus,
    ToggleLinkOwner,
    MarkPartnerEarningsAvailable,
    GetPartners,
    GetPartnerOverview,
    GetPartnersComparison,
)
