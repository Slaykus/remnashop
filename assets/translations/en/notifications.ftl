ntf-error =
    .unknown = ⚠️ <i>An error occurred.</i>
    .permission-denied = ⚠️ <i>You don't have sufficient permissions.</i>
    .log-not-found = ⚠️ <i>Log file not found.</i>
    .logs-disabled = ⚠️ <i>File logging is disabled.</i>

    .lost-context = ⚠️ <i>An error occurred. Restart the dialog with /start.</i>
    .lost-context-restart = ⚠️ <i>An error occurred. Dialog restarted.</i>

ntf-common =
    .trial-unavailable = ⚠️ <i>Trial subscription is temporarily unavailable.</i>
    .throttling = ⚠️ <i>You are sending too many requests. Please wait.</i>
    .double-click-confirm = ⚠️ <i>Click again to confirm the action.</i>
    .squads-empty = ⚠️ <i>No squads found. Please check their presence in the panel.</i>

    .withdraw-points = ❌ <i>You don't have enough points for the exchange.</i>
    .internal-squads-empty = ❌ <i>Please select at least one internal squad.</i>

    .invalid-value = ❌ <i>Invalid value.</i>
    .value-updated = ✅ <i>Parameter updated successfully.</i>
    .cooldown-active = ⏳ <i>Temporarily unavailable. Try again in { $available_at }.</i>

    .plan-not-found = ❌ <i>Plan not found or unavailable.</i>

    .connect-not-available =
    ⚠️ { $status ->
    [LIMITED]
    You have used all available traffic. { $is_trial ->
    [0] { $traffic_strategy ->
        [NO_RESET] Renew your subscription to reset traffic and continue using the service!
        *[RESET] Traffic will be restored in { $reset_time }. You can also renew your subscription to reset traffic.
        }
    *[1] { $traffic_strategy ->
        [NO_RESET] Subscribe to continue using the service!
        *[RESET] Traffic will be restored in { $reset_time }. You can also subscribe to use the service without limits.
        }
    }
    [EXPIRED]
    { $is_trial ->
    [0] Your subscription has expired. Renew it or purchase a new one.
    *[1] Your free trial has ended. Subscribe to continue using the service.
    }
    *[OTHER] An error occurred while checking your status or the subscription was disabled. Please contact support.
    }

ntf-command =
    .paysupport = 💸 <b>To request a refund, please contact support.</b>
    .rules = ⚠️ <b>Please read the <a href="{ $url }">Terms of Use</a> before using the service.</b>
    .help = 🆘 <b>Click the button below to contact support.</b>

ntf-requirement =
    .channel-join-required = ❇️ Subscribe to our channel and get <b>free days, promotions and news</b>. After subscribing, click «Confirm».
    .channel-join-required-left = ⚠️ You have unsubscribed from the channel. Subscribe to continue using the bot.
    .rules-accept-required = ⚠️ <b>Please read and accept the <a href="{ $url }">Terms of Use</a> before using the service.</b>
    .channel-join-error = ⚠️ We can't see your channel subscription. Please check and try again.
    .trial-paused = ⚠️ Trial period paused — you unsubscribed from the channel. Subscribe again to restore access.
    .trial-restored = ✅ Trial period resumed.

ntf-invite =
    .referral-reset = ✅ <i>Referral link updated.</i>

ntf-promocode =
    .not-found = ❌ <i>Promocode not found or invalid.</i>
    .not-available = ❌ <i>Promocode is unavailable.</i>
    .expired = ❌ <i>Promocode has expired.</i>
    .already-activated = ❌ <i>You have already activated this promocode.</i>
    .activated = ✅ <i>Promocode activated successfully!</i>
    .activation-failed = ❌ <i>Failed to activate the promocode. Please try again later.</i>
    .code-exists = ❌ <i>A promocode with this code already exists.</i>
    .created = ✅ <i>Promocode created.</i>
    .deleted = ✅ <i>Promocode deleted.</i>
    .fields-required = ❌ <i>Fill in the reward value.</i>
    .invalid-code = ❌ <i>The code may contain only Latin letters, digits, hyphens and underscores.</i>
    .plans-empty = ❌ <i>No plans available.</i>
    .updated = ✅ <i>Promocode updated.</i>

ntf-user =
    .not-found = <i>❌ User not found.</i>
    .transactions-empty = ❌ <i>Transaction list is empty.</i>
    .subscription-empty = ❌ <i>No active subscription found.</i>
    .subscription-deleted = ✅ <i>Subscription deleted successfully.</i>
    .plans-empty = ❌ <i>No plans available.</i>
    .devices-empty = ❌ <i>Device list is empty.</i>
    .allowed-plans-empty = ❌ <i>No plans available to grant access.</i>
    .message-success = ✅ <i>Message sent successfully.</i>
    .message-failed = ❌ <i>Failed to send message.</i>

    .sync-already = ✅ <i>Subscription data is identical.</i>
    .sync-missing-data = ⚠️ <i>Synchronization impossible. Subscription data is missing in both the panel and the bot.</i>
    .sync-success = ✅ <i>Subscription synchronized successfully.</i>

    .invalid-expire-time = ❌ <i>Cannot { $operation ->
    [ADD] extend
    *[SUB] reduce
    } subscription by the specified number of days.</i>

    .invalid-points = ❌ <i>Cannot { $operation ->
    [ADD] add
    *[SUB] deduct
    } the specified number of points.</i>

ntf-access =
    .maintenance = 🚧 <i>The bot is under maintenance. Please try later.</i>
    .registration-disabled = ❌ <i>New user registration is disabled.</i>
    .registration-invite-only = ❌ <i>Registration is available by invitation only.</i>
    .payments-disabled = 🚧 <i>Payments are temporarily unavailable! You will receive a notification when they are restored.</i>
    .payments-restored = ❇️ <i>Payments restored! You can now buy or renew a subscription. Thank you for waiting.</i>

ntf-plan =
    .not-file = ⚠️ <i>Please send plans as a json file.</i>
    .import-failed = ❌ <i>Import failed.</i>
    .import-success = ✅ <i>Imported successfully.</i>
    .export-plans_not_selected = ❌ <i>Please select at least one plan to export.</i>
    .export-failed = ❌ <i>Export failed.</i>
    .export-success = ✅ <i>Selected plans exported.</i>
    .trial-single-duration = ❌ <i>A trial plan can only have one duration.</i>
    .duration-already-exists = ❌ <i>This duration already exists.</i>
    .name-already-exists = ❌ <i>A plan with this name already exists.</i>
    .user-already-allowed = ❌ <i>This user ID is already added.</i>

    .updated = ✅ <i>Plan updated successfully.</i>
    .created = ✅ <i>Plan created successfully.</i>
    .deleted = ✅ <i>Plan deleted successfully.</i>

ntf-gateway =
    .not-configured = ❌ <i>Payment gateway is not configured.</i>
    .not-configurable = ❌ <i>This payment gateway has no settings.</i>

    .test-payment-created = ✅ <i><a href="{ $url }">Test payment</a> created successfully.</i>
    .test-payment-error = ❌ <i>Error creating test payment.</i>
    .test-payment-confirmed = ✅ <i>Test payment processed successfully.</i>
    .gift-issued =
        🎁 <b>Gift subscription paid</b>

        Code for the recipient: <code>{ $code }</code>

        Pass it on to whoever you are gifting. The code is single-use and valid for { $days } days, then it expires.

ntf-subscription =
    .plans-unavailable = ❌ <i>No plans available at the moment.</i>
    .gateways-unavailable = ❌ <i>No payment gateways available at the moment.</i>
    .renew-plan-unavailable = ❌ <i>The current plan is outdated and unavailable for renewal.</i>
    .payment-creation-failed = ❌ <i>Error creating payment. Please try later.</i>

ntf-broadcast =
    .message = { $content }
    .text-too-long = ❌ Maximum character limit exceeded ({ $max_limit }).
    .list-empty = ❌ <i>Broadcast list is empty.</i>
    .plans-unavailable = ❌ <i>No plans available.</i>
    .audience-unavailable = ❌ <i>No users for the selected audience.</i>
    .content-empty = ❌ <i>Content is empty.</i>
    .content-saved = ✅ <i>Content saved successfully.</i>

    .not-cancelable = ❌ <i>Broadcast cannot be canceled.</i>
    .canceled = ✅ <i>Broadcast canceled successfully.</i>
    .deleting = ⚠️ <i>Deleting sent messages.</i>
    .already-deleted = ❌ <i>Broadcast is already deleted or being deleted.</i>

    .deleted-success =
        ✅ Broadcast <code>{ $task_id }</code> deleted successfully.

        <blockquote>
        • <b>Total messages</b>: { $total_count }
        • <b>Deleted</b>: { $deleted_count }
        • <b>Failed to delete</b>: { $failed_count }
        </blockquote>

ntf-importer =
    .not-file = ⚠️ <i>Please send the database as a file.</i>
    .db-failed = ❌ <i>Error exporting users from the database.</i>
    .users-empty = ❌ <i>User list in the database is empty.</i>

    .import-started = ✅ <i>Import started. Please wait for completion...</i>
    .started = ✅ <i>Import started. Please wait for completion...</i>
    .import-failed = ❌ <i>Import error. Please check the logs.</i>
    .already-running = ⚠️ <i>Import is already running. Please wait.</i>

ntf-sync =
    .started = ✅ <i>Synchronization started. Please wait for completion...</i>
    .users-not-found = ❌ <i>No users found for synchronization.</i>
    .already-running = ⚠️ <i>Synchronization is already running. Please wait.</i>

ntf-menu-editor =
    .button-saved = ✅ <i>Button saved successfully.</i>
    .invalid-payload = ❌ <i>Invalid URL format for payload.</i>

ntf-devices =
    .deleted = ✅ <i>Device deleted.</i>
    .all-deleted = ✅ <i>All devices deleted.</i>
    .reissued = ✅ <i>Subscription reissued successfully.</i>

ntf-node-quota =
    .reset-purchased = ✅ <i>whitelist bypass traffic counter has been reset!</i>

    .reset-purchased-system =
        💳 <b>Paid Whitelist Bypass traffic reset</b>

        User: <code>{ $telegram_id }</code> ({ $name }, @{ $username })
        Amount: <b>{ $price } ₽</b>
        Reset traffic: <b>{ $used_gb } GB</b>
        Was restricted: { $was_restricted ->
            [1] yes
            *[0] no
        }

    .reset-by-admin-system =
        🛠 <b>Whitelist Bypass traffic reset by administrator</b>

        Administrator: <code>{ $admin_telegram_id }</code> ({ $admin_name })
        User: <code>{ $target_telegram_id }</code> ({ $target_name }, @{ $target_username })
        Reset traffic: <b>{ $used_gb } GB</b>
        Was restricted: { $was_restricted ->
            [1] yes
            *[0] no
        }

    .warn =
        ⚠️ You have used <b>{ $used_gb } GB</b> out of <b>{ $limit_gb } GB</b> of your monthly limit on the whitelist bypass server.

        At 100% usage, access to this server will be restricted until the end of the month.

    .limited =
        🚫 Your monthly limit on the whitelist bypass server (<b>{ $limit_gb } GB</b>) has been reached.

        Access will be restored on the 1st of next month.{ $reset_price ->
            [0] { "" }
            *[other]  You can also <b>reset the counter early</b> for { $reset_price } ₽ in the Subscription section.
        }

ntf-ad =
    .bonus-received =
        🎁 <b>You received a bonus for following the ad link!</b>
        { $bonus_points ->
        [0] { "" }
        *[other]
         • +{ $bonus_points } points
        }{ $bonus_days ->
        [0] { "" }
        *[other]
         • +{ $bonus_days } days added to your subscription
        }{ $bonus_discount_pct ->
        [0] { "" }
        *[other]
         • { $bonus_discount_pct }% discount on your next purchase
        }

    .code-invalid = ⚠️ <i>Ad link not found or unavailable.</i>

ntf-partner =
    .payout-confirmed =
        <e id="5427009714745517609">✅</e> <b>Partner confirmed receipt</b>

        { $name } confirmed the money arrived.
    .earning =
        <e id="5433758580765754681">💰</e> <b>Earned { $amount } ₽</b>

        Someone you referred paid { $payment } ₽ for a subscription.
        Your share at { $rate }% is <b>{ $amount } ₽</b>.

        Available for payout on { $available }.

    .available =
        <e id="5427009714745517609">✅</e> <b>{ $amount } ₽ ready to withdraw</b>

        The hold period is over. Request a payout in your cabinet.

    .paid =
        <e id="5433758580765754681">💸</e> <b>Payout of { $amount } ₽ sent</b>

        If the money did not arrive — let us know and we will sort it out.

    .terms-changed =
        <e id="5424858262950111605">🔄</e> <b>Your terms changed</b>

        <blockquote>
        • <b>Rate</b>: { $rate }%
        • <b>Hold</b>: { $hold } days
        • <b>Minimum payout</b>: { $min_payout } ₽
        </blockquote>

        Past earnings are not recalculated: each one keeps the rate it was
        calculated at.
    .payout-requested =
        <e id="5433758580765754681">💰</e> <b>Partner requests a payout</b>

        <blockquote>
        • <b>Who</b>: { $name }
        • <b>Amount</b>: { $amount } ₽
        • <b>Details</b>: { $details }
        </blockquote>

        Issue it in the advertising section, partner card.
