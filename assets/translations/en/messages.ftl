# Onboarding
msg-onboarding-welcome =
    🌧️ <b>Welcome to Rain VPN!</b>

    You're one step away from a stable internet connection.

    { $trial_available ->
    [1] The first <b>{ $trial_days } days</b> are free.
    *[0] { "" }
    }

# Menu
msg-main-menu =
    { hdr-user-profile }
    { frg-user }

    { hdr-subscription }
    { $status ->
    [ACTIVE]
    { frg-subscription }
    [EXPIRED]
    <blockquote>
    • Subscription has expired.

    <i>{ $is_trial ->
    [0] Your subscription has expired. Renew it to continue using the service!
    *[1] Your free trial has ended. Subscribe to continue using the service!
    }</i>
    </blockquote>
    [LIMITED]
    <blockquote>
    • Your traffic has been exhausted.

    <i>{ $is_trial ->
    [0] { $traffic_strategy ->
        [NO_RESET] Renew your subscription to reset traffic and continue using the service!
        *[RESET] Traffic will be restored in { $reset_time }. You can also renew your subscription to reset traffic.
        }
    *[1] { $traffic_strategy ->
        [NO_RESET] Subscribe to continue using the service!
        *[RESET] Traffic will be restored in { $reset_time }. You can also subscribe to use the service without limits.
        }
    }</i>
    </blockquote>
    [DISABLED]
    <blockquote>
    • Your subscription is disabled.

    <i>Please contact support to find out the reason!</i>
    </blockquote>
    *[NONE]
    <blockquote>
    • You have no active subscription.

    <i>{ $trial_available ->
    [1] 🎁 A free trial is available for you — click the button below to get it.
    *[0] ↘️ Go to the «Subscription» menu to purchase access.
    }</i>
    </blockquote>
    }

msg-menu-devices =
    <b>📱 Device management</b>

    Connected: <b>{ $current_count } / { $max_count }</b>

    { $has_devices ->
    [0] { empty }
    *[HAS] Click on a device to remove it.
    If you need more devices — change your subscription.
    }

msg-menu-devices-confirm-reissue =
    🔄 <b>Reissue subscription</b>

    ⚠️ After reset, the old link will <b>stop working</b>.

    You will need to:
    • Remove the old subscription from the app
    • Add the new link from the «Connection» section

    Are you sure you want to reset the link?

msg-menu-devices-confirm-delete =
    🗑 Delete device <b>{ $selected_device_label }</b>?

msg-menu-devices-confirm-delete-all =
    🗑 Delete <b>all devices</b>?

msg-menu-invite =
    <b>🤝 Referral program</b>

    Invite users via your unique link and earn { $reward_type ->
        [POINTS] <b>points</b> — redeem for access days or a subscription
        [EXTRA_DAYS] <b>free days</b> added to your current subscription
        *[OTHER] { $reward_type }
    }.

    <b>📊 Your statistics:</b>
    <blockquote>
    • Users invited: { $referrals }
    • Payments via your link: { $payments }
    { $reward_type ->
    [POINTS] • Points on account: { $points }
    *[EXTRA_DAYS] { empty }
    }
    </blockquote>

    <b>🏆 Status and personal discount:</b>
    <blockquote>
    For every invited user who subscribes, you earn a permanent discount on all plans:

    • ☁️ Cloud — <b>5%</b> (1 person)
    • 🌩️ Storm Cloud — <b>10%</b> (3 people)
    • ⛈️ Storm — <b>15%</b> (5 people)
    • 🌧️ Rain — <b>25%</b> (10 people)

    { $referral_tier ->
    [0] Your status: not yet earned.
    [1] Your status: ☁️ Cloud — discount <b>{ $personal_discount }%</b>
    [2] Your status: 🌩️ Storm Cloud — discount <b>{ $personal_discount }%</b>
    [3] Your status: ⛈️ Storm — discount <b>{ $personal_discount }%</b>
    *[4] Your status: 🌧️ Rain — discount <b>{ $personal_discount }%</b>
    }
    </blockquote>

msg-menu-proxy =
    📡 <b>Help a friend get into Telegram</b>

    Telegram blocked? Send this link — one tap and they're connected, no VPN app needed.

    • <b>Send via Telegram</b> — if they already have access (via proxy or VPN)
    • <b>Other messenger</b> — copy the link and send via any other messenger that works

msg-menu-invite-about =
    <b>💡 Program terms</b>

    <b>Accrual condition:</b>
    <blockquote>
    { $accrual_strategy ->
    [ON_FIRST_PAYMENT] Reward is credited once — for the first subscription payment by the invited user.
    [ON_EACH_PAYMENT] Reward is credited for every payment or subscription renewal by the invited user.
    *[OTHER] { $accrual_strategy }
    }
    </blockquote>

    <b>Reward amount:</b>
    <blockquote>
    { $max_level ->
    [1] For invited users: { $reward_level_1 }
    *[MORE]
    { $identical_reward ->
    [0]
    • Level 1 (your invites): { $reward_level_1 }
    • Level 2 (invites of your friends): { $reward_level_2 }
    *[1]
    For all levels: { $reward_level_1 }
    }
    }

    { $reward_strategy_type ->
    [AMOUNT] { $reward_type ->
        [POINTS] { space }
        [EXTRA_DAYS] <i>Extra days are added to your current subscription.</i>
        *[OTHER] { $reward_type }
    }
    [PERCENT] { $reward_type ->
        [POINTS] <i>Percentage is calculated from the invited user's subscription cost.</i>
        [EXTRA_DAYS] <i>Percentage is calculated from the invited user's subscription duration.</i>
        *[OTHER] { $reward_type }
    }
    *[OTHER] { $reward_strategy_type }
    }
    </blockquote>

msg-invite-reward = { $value }{ $reward_strategy_type ->
    [AMOUNT] { $reward_type ->
        [POINTS] { space }{ $value ->
            [one] point
            *[other] points
            }
        [EXTRA_DAYS] { space }extra { $value ->
            [one] day
            *[other] days
            }
        *[OTHER] { $reward_type }
    }
    [PERCENT] % { $reward_type ->
        [POINTS] points
        [EXTRA_DAYS] extra days
        *[OTHER] { $reward_type }
    }
    *[OTHER] { $reward_strategy_type }
    }


# Dashboard
msg-dashboard-main = <b>🛠 Dashboard</b>
msg-users-main = <b>👥 Users</b>
msg-broadcast-main = <b>📢 Broadcast</b>
msg-statistics-main = <b>📊 Statistics</b>

msg-statistics-users =
    <b>👥 User statistics</b>

    <blockquote>
    • <b>Total</b>: { $total_users }
    • <b>New today</b>: { $new_users_daily }
    • <b>New this week</b>: { $new_users_weekly }
    • <b>New this month</b>: { $new_users_monthly }

    • <b>With subscription</b>: { $users_with_subscription }
    • <b>Without subscription</b>: { $users_without_subscription }
    • <b>With trial</b>: { $users_with_trial }
    </blockquote>

    <blockquote>
    • <b>Blocked</b>: { $blocked_users }
    • <b>Blocked bot</b>: { $bot_blocked_users }

    • <b>Conversion users → purchase</b>: { $user_conversion }%
    • <b>Conversion trial → subscription</b>: { $trial_conversion }%
    </blockquote>

msg-statistics-subscriptions =
    { $plan_name ->
    [0] <b>💳 Subscription statistics</b>
    *[HAS] <b>📦 Plan statistics «{ $plan_name }»</b>
    }

    <blockquote>
    • <b>Total</b>: { $total }
    • <b>Active</b>: { $total_active }
    • <b>Disabled</b>: { $total_disabled }
    • <b>Limited</b>: { $total_limited }
    • <b>Expired</b>: { $total_expired }
    • <b>Expiring (7 days)</b>: { $expiring_soon }
    { $plan_name ->
    [0] • <b>Trial</b>: { $active_trial }
    *[HAS] • <b>Popular duration</b>: { $popular_duration }
    }
    </blockquote>

    { $plan_name ->
    [0] <blockquote>
    • <b>Unlimited</b>: { $total_unlimited }
    • <b>Traffic limited</b>: { $total_traffic }
    • <b>Device limited</b>: { $total_devices }
    </blockquote>
    *[HAS] <b>Total income</b>:
    <blockquote>
    { $all_income }
    </blockquote>
    }

msg-statistics-subscriptions-plan-income = { $income }{ $currency }

msg-statistics-transactions =
    { $gateway_type ->
    [0] <b>🧾 General transaction statistics</b>
    *[HAS] <b>🧾 { gateway-type } statistics</b>
    }

    <blockquote>
    • <b>Total transactions</b>: { $total_transactions }
    • <b>Completed transactions</b>: { $completed_transactions }
    • <b>Free transactions</b>: { $free_transactions }
    { $gateway_type ->
    [0] { $popular_gateway ->
        [0] { empty }
        *[HAS] • <b>Popular gateway</b>: { $popular_gateway }
        }
    *[HAS] { empty }
    }
    </blockquote>

    { $gateway_type ->
    [0] { empty }
    *[HAS] <blockquote>
    • <b>Total income</b>: { $total_income }{ $currency }
    • <b>Daily income</b>: { $daily_income }{ $currency }
    • <b>Weekly income</b>: { $weekly_income }{ $currency }
    • <b>Monthly income</b>: { $monthly_income }{ $currency }
    • <b>Average check</b>: { $average_check }{ $currency }
    • <b>Total discounts</b>: { $total_discounts }{ $currency }
    </blockquote>
    }

msg-statistics-promocodes =
    <b>🎁 Promo code statistics</b>

    <blockquote>
    • <b>Total activations</b>: { $total_promo_activations }
    • <b>Most popular promo code</b>: { $most_popular_promo ->
    [0] { unknown }
    *[HAS] { $most_popular_promo }
    }
    • <b>Days granted</b>: { $total_promo_days }
    • <b>Traffic granted</b>: { $total_promo_days }
    • <b>Subscriptions granted</b>: { $total_promo_subscriptions }
    • <b>Personal discounts granted</b>: { $total_promo_personal_discounts }
    • <b>One-time discounts granted</b>: { $total_promo_purchase_discounts }
    </blockquote>

msg-statistics-referrals =
    <b>👪 Referral statistics</b>

    <blockquote>
    • <b>Total referrals</b>: { $total_referrals }
    • <b>Level 1</b>: { $level_1_count }
    • <b>Level 2</b>: { $level_2_count }
    • <b>Unique referrers</b>: { $unique_referrers }
    { $top_referrer_telegram_id ->
        [0] { empty }
        *[HAS] • <b>Top referrer</b>: { $top_referrer_username ->
            [0] { NUMBER($top_referrer_telegram_id, useGrouping: 0) }
            *[HAS] <a href="tg://user?id={ $top_referrer_telegram_id }">@{ $top_referrer_username }</a>
            } ({ $top_referrer_referrals_count } invited)
    }
    </blockquote>

    <blockquote>
    • <b>Rewards issued</b>: { $total_rewards_issued }
    • <b>Points issued</b>: { $total_points_issued }
    • <b>Days issued</b>: { $total_days_issued }
    </blockquote>


# Access
msg-access-main =
    <b>🔓 Access mode</b>

    <blockquote>
    • <b>Mode</b>: { access-mode }
    • <b>Payments</b>: { $payments_allowed ->
    [0] disabled
    *[1] enabled
    }.
    • <b>Registration</b>: { $registration_allowed ->
    [0] disabled
    *[1] enabled
    }.
    </blockquote>

msg-access-conditions =
    <b>⚙️ Access conditions</b>

msg-access-rules =
    <b>✳️ Change rules link</b>

    { $rules_url ->
    [0] { space }
    *[HAS]
    <blockquote>
    { $rules_url }
    </blockquote>
    }

    Enter the link (in the format https://telegram.org/tos).

msg-access-channel =
    <b>❇️ Change channel/group link</b>

    { $channel_url ->
    [0] { space }
    *[HAS]
    <blockquote>
    { $channel_url } { $channel_id ->
        [0] { empty }
        *[HAS] (ID: { $channel_id })
        }
    </blockquote>
    }

    If your group has no @username, send the group ID and invite link as separate messages.

    If you have a public channel/group, enter only the @username.


# Broadcast
msg-broadcast-list = <b>📄 Broadcast list</b>
msg-broadcast-plan-select = <b>📦 Select a plan for broadcast</b>
msg-broadcast-send = <b>📢 Send broadcast ({ audience-type })</b>

    { $audience_count } { $audience_count ->
    [one] user
    *[other] users
    } will receive the broadcast

msg-broadcast-content =
    <b>✉️ Broadcast content</b>

    Send any message: text, image or both (HTML supported).

msg-broadcast-buttons = <b>✳️ Broadcast buttons</b>

msg-broadcast-view =
    <b>📢 Broadcast</b>

    <blockquote>
    • <b>ID</b>: <code>{ $broadcast_id }</code>
    • <b>Status</b>: { broadcast-status }
    • <b>Audience</b>: { audience-type }
    • <b>Created</b>: { $created_at }
    </blockquote>

    <blockquote>
    • <b>Total messages</b>: { $total_count }
    • <b>Successful</b>: { $success_count }
    • <b>Failed</b>: { $failed_count }
    </blockquote>


# Users
msg-users-recent-registered = <b>🆕 Recently registered</b>
msg-users-recent-activity = <b>📝 Recently active</b>
msg-user-transactions = <b>🧾 User transactions</b>
msg-user-devices = <b>📱 User devices ({ $current_count } / { $max_count })</b>
msg-user-give-access = <b>🔑 Grant plan access</b>

msg-users-search =
    <b>🔍 Search user</b>

    Enter a user ID, part of their name, or forward any of their messages.

msg-users-search-results =
    <b>🔍 Search user</b>

    Found <b>{ $count }</b> { $count ->
    [one] user
    *[other] users
    } matching the query

msg-user-main =
    <b>📝 User information</b>

    { hdr-user-profile }
    { frg-user-details }

    <b>💸 Discount:</b>
    <blockquote>
    • <b>Personal</b>: { $personal_discount }%
    • <b>Next purchase</b>: { $purchase_discount }%
    </blockquote>

    { hdr-subscription }
    { $status ->
    [ACTIVE]
    { frg-subscription }
    [EXPIRED]
    <blockquote>
    • Subscription has expired.
    </blockquote>
    [LIMITED]
    <blockquote>
    • Traffic limit exceeded.
    </blockquote>
    [DISABLED]
    <blockquote>
    • Subscription is disabled.
    </blockquote>
    *[NONE]
    <blockquote>
    • No active subscription.
    </blockquote>
    }

msg-user-statistics =
    <b>📊 User statistics</b>

    <blockquote>
    • <b>Registration date</b>: { $registered_at }
    • <b>Last payment</b>: { $last_payment_at ->
        [0] { unknown }
        *[HAS] { $last_payment_at }
    }
    </blockquote>

    { $payment_amounts ->
    [0] { space }
    *[HAS] <blockquote>
    { $payment_amounts }
    </blockquote>
    }

    <blockquote>
    • <b>Invited by</b>: { $referrer_telegram_id ->
        [0] { unknown }
        *[HAS] { $referrer_username ->
            [0] { NUMBER($referrer_telegram_id, useGrouping: 0) }
            *[HAS] <a href="tg://user?id={ $referrer_telegram_id }">@{ $referrer_username }</a>
            }
    }
    • <b>Invited (lvl 1)</b>: { $referrals_level_1 }
    • <b>Invited (lvl 2)</b>: { $referrals_level_2 }
    • <b>Points received</b>: { $reward_points }
    • <b>Days received</b>: { $reward_days }
    </blockquote>

msg-user-statistics-payment-amount = • <b>Paid ({ $currency })</b>: { $amount }

msg-user-referrals = <b>👪 User referrals</b>

msg-user-sync =
    <b>🌀 Synchronize user</b>

    <b>🌧️ Rain VPN:</b> { $bot_version }
    <blockquote>
    { $has_bot_subscription ->
    [0] No data
    *[HAS]{ $bot_subscription }
    }
    </blockquote>

    <b>🌊 Remnawave:</b> { $remna_version }
    <blockquote>
    { $has_remna_subscription ->
    [0] No data
    *[HAS] { $remna_subscription }
    }
    </blockquote>

    Select the relevant data to synchronize.

msg-user-sync-version = { $version ->
    [NEWER] (newer)
    [OLDER] (older)
    *[UNKNOWN] { empty }
    }

msg-user-sync-subscription =
    • <b>ID</b>: <code>{ $id }</code>
    • Status: { $status ->
    [ACTIVE] Active
    [DISABLED] Disabled
    [LIMITED] Traffic exhausted
    [EXPIRED] Expired
    [DELETED] Deleted
    *[OTHER] { $status }
    }
    • Link: <a href="{ $url }">*********</a>

    • Traffic limit: { $traffic_limit }
    • Device limit: { $device_limit }
    • Expires in: { $expire_time }

    • Internal squads: { $internal_squads ->
    [0] { unknown }
    *[HAS] { $internal_squads }
    }
    • External squad: { $external_squad ->
    [0] { unknown }
    *[HAS] { $external_squad }
    }
    • Traffic reset: { $traffic_limit_strategy ->
    [NO_RESET] On payment
    [DAY] Every day
    [WEEK] Every week
    [MONTH] Every month
    *[OTHER] { $traffic_limit_strategy }
    }
    • Tag: { $tag ->
    [0] { unknown }
    *[HAS] { $tag }
    }

msg-user-sync-waiting =
    <b>🌀 User synchronization</b>

    Please wait... User data synchronization is in progress. You will be automatically returned to the user editor upon completion.

msg-user-give-subscription =
    <b>🎁 Give subscription</b>

    Select the plan you want to give the user.

msg-user-give-subscription-duration =
    <b>⏳ Select duration</b>

    Select the duration of the subscription to be given.

msg-user-discount =
    <b>💸 Change personal discount</b>

    Select from the buttons or enter your own value.

msg-user-points =
    <b>💎 Change referral system points</b>

    <b>Current points: { $current_points }</b>

    Select from the buttons or enter your own value to add or subtract.

msg-user-subscription-traffic-limit =
    <b>🌐 Change traffic limit</b>

    Select from the buttons or enter your own value (in GB) to change the traffic limit.

msg-user-subscription-device-limit =
    <b>📱 Change device limit</b>

    Select from the buttons or enter your own value to change the device limit.

msg-user-subscription-expire-time =
    <b>⏳ Change expiry time</b>

    <b>Expires in: { $expire_time }</b>

    Select from the buttons or enter your own value (in days) to add or subtract.

msg-user-subscription-squads =
    <b>🔗 Change squad list</b>

    { $internal_squads ->
    [0] { empty }
    *[HAS] <b>⏺️ Internal:</b> { $internal_squads }
    }

    { $external_squad ->
    [0] { empty }
    *[HAS] <b>⏹️ External:</b> { $external_squad }
    }

msg-user-subscription-internal-squads =
    <b>⏺️ Change internal squad list</b>

    Select which internal groups will be assigned to this user.

msg-user-yandex-quota =
    <b>🔴 4G/LTE Server</b>

    <blockquote>
    • <b>Node</b>: 🇷🇺🔴 4G/LTE | Not for Wi-Fi
    • <b>Limit</b>: { $yandex_limit_gb } GB / month
    • <b>Used</b>: { $yandex_used_gb } GB ({ $yandex_pct }%)
    • <b>Free</b>: { $yandex_free_gb } GB
    • <b>Period</b>: since { $period_start }
    • <b>Status</b>: { $is_restricted ->
    [1] 🚫 Restricted
    *[0] ✅ Active
    }
    { $restricted_at ->
    [0] { empty }
    *[HAS] • <b>Restricted since</b>: { $restricted_at }
    }
    </blockquote>

msg-user-subscription-external-squads =
    <b>⏹️ Change external squad</b>

    Select which external group will be assigned to this user.

msg-user-subscription-info =
    <b>💳 Current subscription info</b>

    { hdr-subscription }
    { frg-subscription-details }

    <blockquote>
    • <b>Internal squads</b>: { $internal_squads ->
    [0] { unknown }
    *[HAS] { $internal_squads }
    }
    • <b>External squad</b>: { $external_squad ->
    [0] { unknown }
    *[HAS] { $external_squad }
    }
    • <b>First connection</b>: { $first_connected_at ->
    [0] { unknown }
    *[HAS] { $first_connected_at }
    }
    • <b>Last connection</b>: { $last_connected_at ->
    [0] { unknown }
    *[HAS] { $last_connected_at } ({ $node_name })
    }
    </blockquote>

    { hdr-plan }
    { frg-plan-snapshot }

msg-user-transaction-info =
    <b>🧾 Transaction info</b>

    { hdr-payment }
    <blockquote>
    • <b>ID</b>: <code>{ $payment_id }</code>
    • <b>Type</b>: { purchase-type }
    • <b>Status</b>: { transaction-status }
    • <b>Payment method</b>: { gateway-type }
    • <b>Amount</b>: { frg-payment-amount }
    • <b>Created</b>: { $created_at }
    </blockquote>

    { $is_test ->
    [1] ⚠️ Test transaction
    *[0]
    { hdr-plan }
    { frg-plan-snapshot }
    }

msg-user-role =
    <b>👮‍♂️ Change role</b>

    Select a new role for the user.

msg-users-blacklist =
    <b>🚫 Blacklist</b>

    Blocked: <b>{ $count_blocked }</b> / <b>{ $count_users }</b> ({ $percent }%).

msg-user-message =
    <b>📩 Send message to user</b>

    Send any message: text, image or both (HTML supported).


# RemnaWave
msg-remnawave-main =
    <b>🌊 RemnaWave v{ $version }</b>

    <b>🖥️ System:</b>
    <blockquote>
    • <b>CPU</b>: { $cpu_cores } { $cpu_cores ->
    [one] core
    *[other] cores
    } { $cpu_threads } { $cpu_threads ->
    [one] thread
    *[other] threads
    }
    • <b>RAM</b>: { $ram_used } / { $ram_total } ({ $ram_used_percent }%)
    • <b>Uptime</b>: { $uptime }
    </blockquote>

msg-remnawave-users =
    <b>👥 Users</b>

    <b>📊 Statistics:</b>
    <blockquote>
    • <b>Total</b>: { $users_total }
    • <b>Active</b>: { $users_active }
    • <b>Disabled</b>: { $users_disabled }
    • <b>Limited</b>: { $users_limited }
    • <b>Expired</b>: { $users_expired }
    </blockquote>

    <b>🟢 Online:</b>
    <blockquote>
    • <b>Last day</b>: { $online_last_day }
    • <b>Last week</b>: { $online_last_week }
    • <b>Never connected</b>: { $online_never }
    • <b>Online now</b>: { $online_now }
    </blockquote>

msg-remnawave-host-details =
    <b>{ $remark } ({ $is_disabled ->
    [1] disabled
    *[0] enabled
    }):</b>
    <blockquote>
    • <b>Address</b>: <code>{ $address }:{ $port }</code>
    { $inbound_uuid ->
    [0] { empty }
    *[HAS] • <b>Inbound</b>: <code>{ $inbound_uuid }</code>
    }
    </blockquote>

msg-remnawave-node-details =
    <b>{ $country } { $name } ({ $is_connected ->
    [1] connected
    *[0] disconnected
    }):</b>
    <blockquote>
    • <b>Address</b>: <code>{ $address }{ $port ->
    [0] { empty }
    *[HAS]:{ $port }
    }</code>
    • <b>Uptime (xray)</b>: { $xray_uptime }
    • <b>Users online</b>: { $users_online }
    • <b>Traffic</b>: { $traffic_used } / { $traffic_limit }
    </blockquote>

msg-remnawave-inbound-details =
    <b>🔗 { $tag }</b>
    <blockquote>
    • <b>ID</b>: <code>{ $inbound_id }</code>
    • <b>Protocol</b>: { $type } { $network ->
    [0] { space }
    *[HAS] ({ $network })
    }
    { $port ->
    [0] { empty }
    *[HAS] • <b>Port</b>: { $port }
    }
    { $security ->
    [0] { empty }
    *[HAS] • <b>Security</b>: { $security }
    }
    </blockquote>

msg-remnawave-hosts =
    <b>🌐 Hosts</b>

    { $host }

msg-remnawave-nodes =
    <b>🖥️ Nodes</b>

    { $node }

msg-remnawave-inbounds =
    <b>🔌 Inbounds</b>

    { $inbound }


# Rain VPN
msg-remnashop-main = <b>🌧️ Rain VPN { $version ->
[0] { space }
*[HAS] { $version }
}</b>

msg-admins-main = <b>👮‍♂️ Administrators</b>


# Menu editor
msg-menu-editor-main =
    <b>🎛 Main menu button editor</b>

    Select a button to edit.

msg-menu-editor-button =
    <b>🎛 Button configurator</b>

    <blockquote>
    • <b>Status</b>: { $is_active ->
        [1] 🟢 Enabled
        *[0] 🔴 Disabled
        }
    • <b>Text</b>: { $text }
    • <b>Access</b>: { role }
    • <b>Type</b>: { button-type }
    • <b>Data</b>: { $payload }

    </blockquote>

    Select a field to change.

msg-menu-editor-button-text =
    <b>🏷️ Change button text</b>

    Enter button text (maximum 16 characters) or a translation key.

msg-menu-editor-button-availability =
    <b>✴️ Change button access</b>

    Select a role to access the button.

msg-menu-editor-button-type =
    <b>🔖 Change button type</b>

    Select the button type.

msg-menu-editor-button-payload =
    <b>📄 Change button data</b>

    Enter button data (use https for links).



# Gateways
msg-gateways-main = <b>🌐 Payment gateways</b>
msg-gateways-settings = <b>🌐 { gateway-type } configuration</b>
msg-gateways-default-currency = <b>💸 Default currency</b>
msg-gateways-placement = <b>🔢 Change placement</b>

msg-gateways-field =
    <b>🌐 { gateway-type } configuration</b>

    Enter a new value for { $field }.


# Referral
msg-referral-main =
    <b>👥 Referral system</b>

    <blockquote>
    • <b>Status</b>: { $is_enable ->
        [1] 🟢 Enabled
        *[0] 🔴 Disabled
        }
    • <b>Reward type</b>: { reward-type }
    • <b>Levels</b>: { $referral_level }
    • <b>Accrual condition</b>: { accrual-strategy }
    • <b>Accrual method</b>: { reward-strategy }
    </blockquote>

    Select a field to change.

msg-referral-level =
    <b>🔢 Change level</b>

    Select the maximum referral level.

msg-referral-reward-type =
    <b>🎀 Change reward type</b>

    Select a new reward type.

msg-referral-accrual-strategy =
    <b>📍 Change accrual condition</b>

    Select when the reward will be credited.


msg-referral-reward-strategy =
    <b>⚖️ Change accrual method</b>

    Select the reward calculation method.


msg-referral-reward-level = { $level } level: { $value }{ $reward_strategy_type ->
    [AMOUNT] { $reward_type ->
        [POINTS] { space }{ $value ->
            [one] point
            *[other] points
            }
        [EXTRA_DAYS] { space }extra { $value ->
            [one] day
            *[other] days
            }
        *[OTHER] { $reward_type }
    }
    [PERCENT] % { $reward_type ->
        [POINTS] points
        [EXTRA_DAYS] extra days
        *[OTHER] { $reward_type }
    }
    *[OTHER] { $reward_strategy_type }
    }

msg-referral-reward =
    <b>🎁 Change reward</b>

    <blockquote>
    { $reward }
    </blockquote>

    { $reward_strategy_type ->
        [AMOUNT] Enter the number of { $reward_type ->
            [POINTS] points
            [EXTRA_DAYS] days
            *[OTHER] { $reward_type }
        }
        [PERCENT] Enter the percentage of { $reward_type ->
            [POINTS] <u>subscription cost</u>
            [EXTRA_DAYS] <u>subscription duration</u>
            *[OTHER] { $reward_type }
        }
        *[OTHER] { $reward_strategy_type }
    } (in format: level=value)

# Plans
msg-plans-main = <b>📦 Plans</b>

msg-plans-import =
    <b>📦 Import plans</b>

    Send a json file to import.

msg-plans-export =
    <b>📦 Export plans</b>

    Select plans to export.

msg-plan-configurator =
    <b>📦 Plan configurator</b>

    <blockquote>
    • <b>Name</b>: { $name }
    • <b>Type</b>: { plan-type } { $is_trial ->
    [1] (Trial)
    *[0] { space }
    }
    • <b>Access</b>: { availability-type }
    • <b>Status</b>: { $is_active ->
        [1] 🟢 Enabled
        *[0] 🔴 Disabled
        }
    </blockquote>

    <blockquote>
    • <b>Traffic limit</b>: { $is_unlimited_traffic ->
        [1] { unlimited }
        *[0] { $traffic_limit }
        }
    • <b>Device limit</b>: { $is_unlimited_devices ->
        [1] { unlimited }
        *[0] { $device_limit }
        }
    </blockquote>

    Select a field to change.

msg-plan-name =
    <b>🏷️ Change name</b>

    { $name ->
    [0] { space }
    *[HAS]
    <blockquote>
    { $name }
    </blockquote>
    }

    Enter a unique plan name or translation key (maximum 16 characters).

msg-plan-description =
    <b>💬 Change description</b>

    { $description ->
    [0] { space }
    *[HAS]
    <blockquote>
    { $description }
    </blockquote>
    }

    Enter a new plan description or translation key.

msg-plan-tag =
    <b>📌 Change tag</b>

    { $tag ->
    [0] { space }
    *[HAS]
    <blockquote>
    { $tag }
    </blockquote>
    }

    Enter a new plan tag (only uppercase Latin letters, digits and underscore).

msg-plan-type =
    <b>🔖 Change type</b>

    Select a new plan type. Check the «Trial» button to provide this plan as a trial.

msg-plan-availability =
    <b>✴️ Change availability</b>

    Select plan availability.

msg-plan-traffic =
    <b>🌐 Change traffic limit and reset strategy</b>

    Enter the new plan traffic limit (in GB) and select the reset strategy.

msg-plan-devices =
    <b>📱 Change device limit</b>

    Enter the new plan device limit.

msg-plan-durations =
    <b>⏳ Plan durations</b>

    Select a duration to change the price.

msg-plan-duration =
    <b>⏳ Add plan duration</b>

    Enter the new duration (in days).

msg-plan-prices =
    <b>💰 Change duration prices ({ $value ->
            [0] { unlimited }
            *[other] { unit-day }
        })</b>

    Select a currency with price to change.

msg-plan-price =
    <b>💰 Change price for duration ({ $value ->
            [0] { unlimited }
            *[other] { unit-day }
        })</b>

    Enter the new price for currency { $currency }.

msg-plan-allowed-users =
    <b>👥 Change allowed users list</b>

    Enter the user ID to add to the list.

msg-plan-squads =
    <b>🔗 Squads</b>

    { $internal_squads ->
    [0] { space }
    *[HAS] <b>⏺️ Internal:</b> { $internal_squads }
    }

    { $external_squad ->
    [0] { space }
    *[HAS] <b>⏹️ External:</b> { $external_squad }
    }

msg-plan-internal-squads =
    <b>⏺️ Change internal squad list</b>

    Select which internal groups will be assigned to this plan.

msg-plan-external-squads =
    <b>⏹️ Change external squad</b>

    Select which external group will be assigned to this plan.


# Notifications
msg-notifications-main = <b>🔔 Notification settings</b>
msg-notifications-user = <b>👥 User notifications</b>
msg-notifications-system = <b>⚙️ System notifications</b>


# Subscription
msg-subscription-main =
    <b>💳 Subscription</b>

    { $has_current_subscription ->
    [1] { frg-subscription }
    *[0] { empty }
    }

    { $yandex_quota_enabled ->
    [1]
    <b>🔴 4G/LTE Server:</b>
    <blockquote>
    { $yandex_is_restricted ->
    [1] • 🚫 Access restricted until the 1st of next month
    *[0]
    • <b>Used</b>: { $yandex_used_gb } / { $yandex_limit_gb } GB
    • <b>Free</b>: { $yandex_free_gb } GB
    }
    </blockquote>
    *[0] { empty }
    }

msg-subscription-traffic-reset-confirm =
    <b>🔴 4G/LTE Traffic Reset</b>

    Reset your used traffic counter for the 4G/LTE server.

    <b>Cost:</b> { $price } ₽

    After successful payment, your counter will be reset immediately and you will regain access to your full monthly limit.

    { $tr_url_has ->
    [1] ✅ Payment created. Click the button below to pay.
    *[0] Select a payment method:
    }

msg-subscription-plans = <b>📦 Select a plan</b>
msg-subscription-new-success = To start using our service, click the <code>`{ btn-subscription.connect }`</code> button and follow the instructions!
msg-subscription-renew-success = Your subscription has been extended by { $added_duration }.

msg-subscription-plan =
    <b>📦 Plan available by link</b>

    The plan <b>{ $name }</b> is available to you by link. Click the button below to select the duration and payment method.

    { $description ->
    [0] { space }
    *[HAS]
    <blockquote>
    { $description }
    </blockquote>
    }

    { $purchase_type ->
    [RENEW] <i>⚠️ Your current subscription will be <u>extended</u> by the selected period.</i>
    [CHANGE] <i>⚠️ Your current subscription will be <u>replaced</u> by this plan without recalculating the remaining period.</i>
    *[OTHER] { empty }
    }

msg-subscription-details =
    <b>{ $plan }:</b>
    <blockquote>
    { $description ->
    [0] { empty }
    *[HAS]
    { $description }
    }

    • <b>Traffic limit</b>: { $traffic }
    • <b>Device limit</b>: { $devices }
    { $period ->
    [0] { empty }
    *[HAS] • <b>Duration</b>: { $period }
    }
    { $final_amount ->
    [0] { empty }
    *[HAS] • <b>Price</b>: { frg-payment-amount }
    }
    </blockquote>

msg-subscription-duration =
    <b>⏳ Select duration</b>

    { msg-subscription-details }

msg-subscription-payment-method =
    <b>💳 Select payment method</b>

    { msg-subscription-details }

msg-subscription-confirm =
    <b>🛒 Confirm { $purchase_type ->
    [RENEW] renewal
    [CHANGE] change
    *[OTHER] purchase
    } of subscription</b>

    { msg-subscription-details }

    { $purchase_type ->
    [RENEW] <i>⚠️ Your current subscription will be <u>extended</u> by the selected period.</i>
    [CHANGE] <i>⚠️ Your current subscription will be <u>replaced</u> by the selected one without recalculating the remaining period.</i>
    *[OTHER] { empty }
    }

msg-subscription-trial =
    <b>✅ Trial subscription received successfully!</b>

    { msg-subscription-new-success }

msg-subscription-success =
    <b>✅ Payment successful!</b>

    { $purchase_type ->
    [NEW] { msg-subscription-new-success }
    [RENEW] { msg-subscription-renew-success }
    [CHANGE] { msg-subscription-change-success }
    *[OTHER] { $purchase_type }
    }

msg-subscription-change-success =
    Your subscription has been changed.

    <b>{ $plan_name }</b>
    { frg-subscription }

msg-subscription-failed =
    <b>❌ An error occurred!</b>

    Don't worry, technical support has been notified and will contact you shortly. We apologize for the inconvenience.


# Importer
msg-importer-main =
    <b>📥 Import users</b>

    Starting synchronization: checking all users in RemnaWave. If a user is not in the bot's database, they will be created and receive a temporary subscription. If the user's data differs, it will be automatically updated (panel data takes priority).

msg-importer-from-xui =
    <b>📥 Import users (3X-UI)</b>

    { $has_exported ->
    [1]
    <b>🔍 Found:</b>
    <blockquote>
    Total users: { $total }
    With active subscription: { $active }
    With expired subscription: { $expired }
    </blockquote>
    *[0]
    All <b>active</b> users with a <b>numeric</b> email are imported.

    It is recommended to disable users whose email field doesn't contain a Telegram ID beforehand. The operation may take significant time depending on the number of users.

    Send the database file (in .db format).
    }

msg-importer-squads =
    <b>🔗 Internal squad list</b>

    Select which internal groups will be available to imported users.

msg-importer-import-completed =
    <b>📥 User import completed</b>

    <b>📃 Info:</b>
    <blockquote>
    • <b>Total users</b>: { $total_count }
    • <b>Successfully imported</b>: { $success_count }
    • <b>Failed to import</b>: { $failed_count }
    </blockquote>

msg-importer-sync-completed =
    <b>📥 User synchronization completed</b>

    <b>📃 Info:</b>
    <blockquote>
    Total users in panel: { $total_panel_users }
    Total users in bot: { $total_bot_users }

    New users: { $added_users }
    Subscriptions added: { $added_subscription }
    Subscriptions updated: { $updated}

    Users without Telegram ID: { $missing_telegram }
    Synchronization errors: { $errors }
    </blockquote>


# Promocodes
msg-promocodes-main = <b>🎟 Promo codes</b>
msg-promocode-configurator =
    <b>🎟 Promo code configurator</b>

    <blockquote>
    • <b>Code</b>: { $code }
    • <b>Type</b>: { promocode-type }
    • <b>Access</b>: { availability-type }
    • <b>Status</b>: { $is_active ->
        [1] 🟢 Enabled
        *[0] 🔴 Disabled
        }
    </blockquote>

    <blockquote>
    { $promocode_type ->
    [DURATION] • <b>Duration</b>: { $reward }
    [TRAFFIC] • <b>Traffic</b>: { $reward }
    [DEVICES] • <b>Devices</b>: { $reward }
    [SUBSCRIPTION] • <b>Subscription</b>: { frg-plan-snapshot }
    [PERSONAL_DISCOUNT] • <b>Personal discount</b>: { $reward }%
    [PURCHASE_DISCOUNT] • <b>Purchase discount</b>: { $reward }%
    *[OTHER] { $promocode_type }
    }
    • <b>Lifetime</b>: { $lifetime }
    • <b>Activation limit</b>: { $max_activations }
    </blockquote>

    Select a field to change.
