from dataclasses import asdict, dataclass, field
from typing import Any

from remnapy.enums.users import TrafficLimitStrategy

from src.application.dto import MessagePayloadDto
from src.core.enums import MessageEffectId, ReferralRewardType, UserNotificationType
from src.core.types import NotificationType

from .base import UserEvent


@dataclass(frozen=True, kw_only=True)
class SubscriptionLimitedEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.LIMITED,
        init=False,
    )

    is_trial: bool
    traffic_strategy: TrafficLimitStrategy
    reset_time: Any

    @property
    def event_key(self) -> str:
        return "event-subscription.limited"

    def as_payload(self) -> "MessagePayloadDto":
        return MessagePayloadDto(
            i18n_key=self.event_key,
            i18n_kwargs={**asdict(self)},
            disable_default_markup=False,
            delete_after=None,
        )


@dataclass(frozen=True, kw_only=True)
class SubscriptionExpiredEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.EXPIRED,
        init=True,
    )

    is_trial: bool

    @property
    def event_key(self) -> str:
        return "event-subscription.expired"

    def as_payload(self) -> "MessagePayloadDto":
        return MessagePayloadDto(
            i18n_key=self.event_key,
            i18n_kwargs={**asdict(self)},
            disable_default_markup=False,
            delete_after=None,
        )


@dataclass(frozen=True, kw_only=True)
class SubscriptionExpiredAgoEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.EXPIRED_1_DAY_AGO,
        init=True,
    )

    is_trial: bool
    day: int

    @property
    def event_key(self) -> str:
        return "event-subscription.expired-ago"

    def as_payload(self) -> "MessagePayloadDto":
        return MessagePayloadDto(
            i18n_key=self.event_key,
            i18n_kwargs={**asdict(self), "value": self.day},
            disable_default_markup=False,
            delete_after=None,
        )


@dataclass(frozen=True, kw_only=True)
class SubscriptionExpiresEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.EXPIRES_IN_1_DAY,
        init=True,
    )

    is_trial: bool
    day: int

    @property
    def event_key(self) -> str:
        return "event-subscription.expiring"

    def as_payload(self) -> "MessagePayloadDto":
        return MessagePayloadDto(
            i18n_key=self.event_key,
            i18n_kwargs={**asdict(self), "value": self.day},
            disable_default_markup=False,
            delete_after=None,
        )


@dataclass(frozen=True, kw_only=True)
class TorrentBlockedEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.TORRENT_BLOCKED,
        init=False,
    )

    node_name: str
    block_duration: Any
    support_url: str

    @property
    def event_key(self) -> str:
        return "event-torrent-blocker.user-blocked"


@dataclass(frozen=True, kw_only=True)
class ReferralEvent(UserEvent):
    name: str


@dataclass(frozen=True, kw_only=True)
class ReferralAttachedEvent(ReferralEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.REFERRAL_ATTACHED,
        init=True,
    )

    @property
    def event_key(self) -> str:
        return "event-referral.attached"


@dataclass(frozen=True, kw_only=True)
class ReferralRewardEvent(ReferralEvent):
    value: int
    reward_type: ReferralRewardType


@dataclass(frozen=True, kw_only=True)
class ReferralRewardReceivedEvent(ReferralRewardEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.REFERRAL_REWARD_RECEIVED,
        init=True,
    )

    @property
    def event_key(self) -> str:
        return "event-referral.reward"

    def as_payload(self) -> "MessagePayloadDto":
        return MessagePayloadDto(
            i18n_key=self.event_key,
            i18n_kwargs={**asdict(self)},
            disable_default_markup=False,
            delete_after=None,
            message_effect=MessageEffectId.PARTY,
        )


@dataclass(frozen=True, kw_only=True)
class ReferralRewardFailedEvent(ReferralRewardEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.REFERRAL_REWARD_FAILED,
        init=True,
    )

    @property
    def event_key(self) -> str:
        return "event-referral.reward-failed"


@dataclass(frozen=True, kw_only=True)
class ReferralMilestoneEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.REFERRAL_MILESTONE,
        init=False,
    )

    tier: int
    paid_referrals_count: int
    discount: int

    @property
    def event_key(self) -> str:
        return "event-referral.milestone"

    def as_payload(self) -> "MessagePayloadDto":
        return MessagePayloadDto(
            i18n_key=self.event_key,
            i18n_kwargs={
                "tier": self.tier,
                "paid_referrals_count": self.paid_referrals_count,
                "discount": self.discount,
            },
            disable_default_markup=False,
            delete_after=None,
            message_effect=MessageEffectId.PARTY,
        )


@dataclass(frozen=True, kw_only=True)
class ReactivationEvent(UserEvent):
    """Письмо кампании возврата.

    Отдельным событием, а не прямым вызовом уведомителя: так клавиатуру
    собирает служба уведомлений, как для всех прочих писем, и сценарию не
    нужно знать про телеграм.
    """

    notification_type: NotificationType = field(
        default=UserNotificationType.REACTIVATION,
        init=False,
    )

    i18n_key: str
    keyboard: str
    support_url: str
    discount: int = 0
    days: int = 0

    @property
    def event_key(self) -> str:
        return self.i18n_key

    def as_payload(self) -> "MessagePayloadDto":
        return MessagePayloadDto(
            i18n_key=self.event_key,
            i18n_kwargs={"discount": self.discount, "days": self.days},
            disable_default_markup=False,
            delete_after=None,
        )


@dataclass(frozen=True, kw_only=True)
class UserNotConnectedEvent(UserEvent):
    notification_type: NotificationType = field(
        default=UserNotificationType.NOT_CONNECTED,
        init=False,
    )

    support_url: str

    @property
    def event_key(self) -> str:
        return "event-subscription.not-connected"

    def as_payload(self) -> "MessagePayloadDto":
        return MessagePayloadDto(
            i18n_key=self.event_key,
            disable_default_markup=True,
            delete_after=None,
        )
