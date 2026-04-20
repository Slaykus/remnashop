from typing import Final

from src.application.common import Interactor

from .commands.attachment import AttachReferral
from .commands.milestone import CheckReferralMilestone
from .commands.rewards import AssignReferralRewards, GiveReferrerReward
from .queries.calculations import CalculateReferralReward
from .queries.code import GenerateReferralQr, GetReferralCodeFromEvent, ValidateReferralCode

REFERRAL_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    AttachReferral,
    CheckReferralMilestone,
    ValidateReferralCode,
    GetReferralCodeFromEvent,
    GenerateReferralQr,
    CalculateReferralReward,
    GiveReferrerReward,
    AssignReferralRewards,
)
