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
    { $is_trial ->
    [0]
    <b>⚠️ Attention! Your subscription expires in { unit-day }.</b>

    Renew it in advance to avoid losing access to the service!
    *[1]
    <b>⚠️ Attention! Your free trial expires in { unit-day }.</b>

    Subscribe to avoid losing access to the service!
    }

    .expired =
    <b>⛔ Attention! Access suspended — VPN is not working.</b>

    { $is_trial ->
    [0] Your subscription has expired. Renew it to continue using the VPN!
    *[1] Your free trial has ended. Subscribe to continue using the service!
    }

    .expired-ago =
    <b>⛔ Attention! Access suspended — VPN is not working.</b>

    { $is_trial ->
    [0] Your subscription expired { unit-day } ago. Renew it to continue using the service!
    *[1] Your free trial ended { unit-day } ago. Subscribe to continue using the service!
    }

    .limited =
    <b>⛔ Attention! Access suspended — VPN is not working.</b>

    Your traffic has been exhausted. { $is_trial ->
    [0] { $traffic_strategy ->
        [NO_RESET] Renew your subscription to reset traffic and continue using the service!
        *[RESET] Traffic will be restored in { $reset_time }. You can also renew your subscription to reset traffic.
        }
    *[1] { $traffic_strategy ->
        [NO_RESET] Subscribe to continue using the service!
        *[RESET] Traffic will be restored in { $reset_time }. You can also subscribe to use the service without limits.
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

event-remnashop-welcome =
    <b>🌧️ Rain VPN v{ $version }</b>

    Welcome to the Rain VPN dashboard! The bot has started successfully and is ready to work.

    🚀 <i>Configure payment gateways and plans in the «Dashboard» section to start accepting clients.</i>
