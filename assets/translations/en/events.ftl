event-error =
    .general =
    #ErrorEvent

    <b>🔅 Event: An error occurred!</b>

    { frg-build-info }

    { $telegram_id ->
    [0] { space }
    *[HAS]
    { hdr-user }
    { frg-user-info }
    }

    { hdr-error }
    <blockquote>
    { $error }
    </blockquote>

    .remnawave =
    #ErrorEvent

    <b>🔅 Event: Remnawave connection error!</b>

    <blockquote>
    Without an active connection the bot cannot function correctly!
    </blockquote>

    { frg-build-info }

    { hdr-error }
    <blockquote>
    { $error }
    </blockquote>

    .webhook =
    #ErrorEvent

    <b>🔅 Event: Webhook error detected!</b>

    { hdr-error }
    <blockquote>
    { $error }
    </blockquote>


event-bot =
    .startup =
    #BotStartupEvent

    <b>🔅 Event: Bot started!</b>

    { frg-build-info }

    <b>🔓 Availability:</b>
    <blockquote>
    • <b>Mode</b>: { access-mode }
    • <b>Payments</b>: { $payments_allowed ->
    [0] disabled
    *[1] enabled
    }
    • <b>Registration</b>: { $registration_allowed ->
    [0] disabled
    *[1] enabled
    }
    </blockquote>

    .shutdown =
    #BotShutdownEvent

    <b>🔅 Event: Bot stopped!</b>

    { frg-build-info }

    <blockquote>
    • <b>Uptime</b>: { $uptime }
    </blockquote>

    .update =
    #BotUpdateEvent

    <b>🔅 Event: Rain VPN update detected!</b>

    <b>📑 Versions:</b>
    <blockquote>
    • <b>Current</b>: { $local_version }
    • <b>Latest</b>: { $remote_version }
    </blockquote>


event-user =
    .registered =
    #UserRegisteredEvent

    <b>🔅 Event: New user!</b>

    { hdr-user }
    { frg-user-info }

    { $referrer_telegram_id ->
    [0] { empty }
    *[HAS]
    <b>🤝 Referrer:</b>
    <blockquote>
    • <b>ID</b>: <code>{ NUMBER($referrer_telegram_id, useGrouping: 0) }</code>
    • <b>Name</b>: { $referrer_name } { $referrer_username ->
        [0] { empty }
        *[HAS] (<a href="tg://user?id={ $referrer_telegram_id }">@{ $referrer_username }</a>)
    }
    </blockquote>
    }

    .first-connected =
    #UserFirstConnectionEvent

    <b>🔅 Event: User's first connection!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-subscription }
    { frg-subscription-details }

    .device-added =
    #UserDeviceAddedEvent

    <b>🔅 Event: User added a new device!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-hwid }
    { frg-user-hwid }

    .device-deleted =
    #UserDeviceDeletedEvent

    <b>🔅 Event: User deleted a device!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-hwid }
    { frg-user-hwid }


event-subscription =
    .trial =
    #SubscriptionTrialEvent

    <b>🔅 Event: Trial subscription received!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-plan }
    { frg-plan-snapshot }

    .new =
    #SubscriptionNewEvent

    <b>🔅 Event: Subscription purchased!</b>

    { hdr-payment }
    { frg-payment-info }

    { hdr-user }
    { frg-user-info }

    { hdr-plan }
    { frg-plan-snapshot }

    .renew =
    #SubscriptionRenewEvent

    <b>🔅 Event: Subscription renewed!</b>

    { hdr-payment }
    { frg-payment-info }

    { hdr-user }
    { frg-user-info }

    { hdr-plan }
    { frg-plan-snapshot }

    .change =
    #SubscriptionChangeEvent

    <b>🔅 Event: Subscription changed!</b>

    { hdr-payment }
    { frg-payment-info }

    { hdr-user }
    { frg-user-info }

    { hdr-plan }
    { frg-plan-snapshot-comparison }

    .expiring =
    { $value ->
    [1]
    { $is_trial ->
    [0]
    ⚠️ <b>Your subscription expires tomorrow!</b>

    Renew now — otherwise VPN will stop working tomorrow.
    *[1]
    ⚠️ <b>Your free trial ends tomorrow!</b>

    Subscribe now to keep access to the service.
    }
    [2]
    { $is_trial ->
    [0]
    ⏰ <b>Your subscription ends in 2 days.</b>

    Renew in advance to avoid any interruption.
    *[1]
    ⏰ <b>Your free trial ends in 2 days.</b>

    Subscribe in advance to keep uninterrupted access.
    }
    *[other]
    { $is_trial ->
    [0]
    📅 <b>Reminder: your subscription ends in { unit-day }.</b>

    Renew in advance to keep access to the service.
    *[1]
    📅 <b>Reminder: your free trial ends in { unit-day }.</b>

    Subscribe to continue using the VPN.
    }
    }

    .expired =
    { $is_trial ->
    [0]
    ⛔ <b>Subscription expired — VPN is offline.</b>

    Renew your subscription to restore access.
    *[1]
    ⛔ <b>Free trial ended — VPN is offline.</b>

    Subscribe to continue using the service.
    }

    .expired-ago =
    { $is_trial ->
    [0]
    ⛔ <b>Your subscription expired { unit-day } ago.</b>

    VPN is still offline. Renew whenever you're ready.
    *[1]
    ⛔ <b>Your free trial ended { unit-day } ago.</b>

    Subscribe whenever you're ready — access restores instantly.
    }

    .limited =
    { $is_trial ->
    [0]
    ⛔ <b>Traffic exhausted — VPN is suspended.</b>

    { $traffic_strategy ->
    [NO_RESET] Renew your subscription to reset the counter and continue.
    *[RESET] Traffic resets in { $reset_time }. Or renew now to reset it immediately.
    }
    *[1]
    ⛔ <b>Trial traffic exhausted.</b>

    { $traffic_strategy ->
    [NO_RESET] Subscribe to continue using the service.
    *[RESET] Traffic resets in { $reset_time }. Subscribe for unlimited access.
    }
    }

    .revoked =
    #SubscriptionRevokedEvent

    <b>🔅 Event: User reissued subscription!</b>

    { hdr-user }
    { frg-user-info }

    { hdr-subscription }
    { frg-subscription-details }


event-node =
    .connection-lost =
    #NodeConnectionLostEvent

    <b>🔅 Event: Node connection lost!</b>

    { hdr-node }
    { frg-node-info }

    .connection-restored =
    #NodeConnectionRestoredEvent

    <b>🔅 Event: Node connection restored!</b>

    { hdr-node }
    { frg-node-info }

    .traffic-reached =
    #NodeTrafficReachedEvent

    <b>🔅 Event: Node has reached traffic limit threshold!</b>

    { hdr-node }
    { frg-node-info }


event-referral =
    .attached =
    <b>🤝 New referral</b>

    <blockquote>
    User <b>{ $name }</b> registered via your referral link. The reward will be credited after the first payment.
    </blockquote>

    .reward =
    <b>✅ Reward credited</b>

    <blockquote>
    User <b>{ $name }</b> made a payment. You received: <b>{ $value } { $reward_type ->
    [POINTS] { $value ->
        [one] point
        *[other] points
        }

    <i>Go to the «Invite» section to learn about available rewards and how to use them.</i>
    [EXTRA_DAYS] extra { $value ->
        [one] day
        *[other] days
        } </b> added to your subscription.
    *[OTHER] { $reward_type }
    }
    </blockquote>

    .reward-failed =
    <b>⚠️ Failed to credit reward</b>

    <blockquote>
    User <b>{ $name }</b> made a payment, but the reward cannot be credited: <b>you have no active subscription</b> to add { $value } { $reward_type ->
    [POINTS] { $value ->
        [one] point
        *[other] points
        }
    [EXTRA_DAYS] extra { $value ->
        [one] day
        *[other] days
        }
    *[OTHER] { $reward_type }
    } to.

    <i>Subscribe to receive rewards for invited users.</i>
    </blockquote>

    .milestone =
    { $tier ->
    [1] 🎉 <b>New status: ☁️ Cloud!</b>
    [2] 🎉 <b>New status: 🌩️ Storm Cloud!</b>
    [3] 🎉 <b>New status: ⛈️ Storm!</b>
    [4] 🎉 <b>New status: 🌧️ Rain!</b>
    *[other] 🎉 <b>New status unlocked!</b>
    }

    <blockquote>
    You've brought <b>{ $paid_referrals_count } active { $paid_referrals_count ->
        [one] user
        *[other] users
    }</b> — and earned a permanent <b>{ $discount }% discount</b> on all subscriptions!
    </blockquote>

event-remnashop-welcome =
    <b>🌧️ Rain VPN v{ $version }</b>

    Welcome to the Rain VPN dashboard! The bot has started successfully and is ready to work.

    🚀 <i>Configure payment gateways and plans in the «Dashboard» section to start accepting clients.</i>
