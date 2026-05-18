from dishka import Provider, Scope, provide

from src.application.common.dao import (
    BroadcastDao,
    PaymentGatewayDao,
    PlanDao,
    ReferralDao,
    SettingsDao,
    SubscriptionDao,
    TransactionDao,
    UserDao,
    WaitlistDao,
    WebhookDao,
    NodeQuotaDao,
)
from src.infrastructure.database.dao import (
    BroadcastDaoImpl,
    PaymentGatewayDaoImpl,
    PlanDaoImpl,
    ReferralDaoImpl,
    SettingsDaoImpl,
    SubscriptionDaoImpl,
    TransactionDaoImpl,
    UserDaoImpl,
    WaitlistDaoImpl,
    WebhookDaoImpl,
    NodeQuotaDaoImpl,
)


class DaoProvider(Provider):
    scope = Scope.REQUEST

    broadcast = provide(source=BroadcastDaoImpl, provides=BroadcastDao)
    payment_gateway = provide(source=PaymentGatewayDaoImpl, provides=PaymentGatewayDao)
    plan = provide(source=PlanDaoImpl, provides=PlanDao)
    referral = provide(source=ReferralDaoImpl, provides=ReferralDao)
    settings = provide(source=SettingsDaoImpl, provides=SettingsDao)
    subscription = provide(source=SubscriptionDaoImpl, provides=SubscriptionDao)
    transaction = provide(source=TransactionDaoImpl, provides=TransactionDao)
    user = provide(source=UserDaoImpl, provides=UserDao)
    node_quota = provide(source=NodeQuotaDaoImpl, provides=NodeQuotaDao)

    webhook = provide(source=WebhookDaoImpl, provides=WebhookDao, scope=Scope.APP)
    waitlist = provide(source=WaitlistDaoImpl, provides=WaitlistDao, scope=Scope.APP)
