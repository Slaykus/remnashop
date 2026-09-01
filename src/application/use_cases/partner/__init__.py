from typing import Final

from src.application.common import Interactor

from .commands.manage import (
    ConfirmPayout,
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
from .queries.list import (
    GetPartnerOverview,
    GetPartners,
    PartnerListItemDto,
    GetPartnersComparison,
    PartnerListItemDto,
)

PARTNER_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    ConfirmPayout,
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
