# Additional translations for custom use.
# Used for: extra menu buttons, plan names, etc.

# To use translations, specify the key instead of text (e.g., in the plan name).
# Keys must be unique. See assets/README.md for documentation.

# Maximum translation length:
# For use in buttons - 16 characters.
# For use in messages - 1024 characters.

# example-key = translation

c-menu-link1 = 1️⃣ First button
c-menu-link2 = 2️⃣ Second button

c-plan-name1 = 1️⃣ First plan
c-plan-name2 = 2️⃣ Second plan

# ============================================================
# User menu buttons — Rain VPN branding.
# Plain Unicode emoji here double as the fallback for clients without
# custom emoji support. Run `node brand/emoji/apply-ids.mjs` after filling
# brand/emoji/ids.json to inject <e id="..."> tags between the markers.
# ============================================================

# >>> rain-emoji

btn-menu =
    .trial = <e id="5429339305006900161">🌧️</e> TRY FOR FREE
    .trial-paid = <e id="5429339305006900161">🌧️</e> TRY FOR { $trial_price }
    .connect = <e id="5429282761762450449">⚡</e> Connect
    .connect-reserve = <e id="5429584264171661832">🔗</e> Connect (reserve)
    .devices = <e id="5429616296037753715">📱</e> My devices
    .subscription = <e id="5429564215264325150">💎</e> Subscription
    .invite = <e id="5429600567867515464">👥</e> Invite a friend
    .support = <e id="5431896318081542131">💬</e> Support
    .web-cabinet = <e id="5429122254539629456">🌐</e> Web cabinet
    .dashboard = <e id="5429161811188426323">🎛</e> Dashboard

btn-invite =
    .about = <e id="5429441933250439962">❓</e> About the reward
    .copy = <e id="5431552836661977123">📋</e> Copy link
    .send = <e id="5429450274076929631">📩</e> Invite
    .qr = <e id="5429192215261911590">🔳</e> QR code
    .withdraw-points = <e id="5429251773573407519">⭐</e> Exchange points
    .reset-referral = <e id="5429165006644095979">🔄</e> Reset referral link

btn-devices =
    .delete-all = <e id="5429606649541208054">🗑</e> Delete all devices
    .reissue = <e id="5429165006644095979">🔄</e> Reissue subscription
    .confirm-delete = <e id="5431365176655913424">✅</e> Yes, delete
    .confirm-reissue = <e id="5431365176655913424">✅</e> Yes, reset
    .cancel-reissue = <e id="5431373569022009585">❌</e> No

btn-subscription =
    .plan = <e id="5431866897555564066">🗂</e> Go to subscription
    .new = <e id="5429458988565570302">💰</e> Buy subscription
    .renew = <e id="5431470622397996981">🔁</e> Renew
    .change = <e id="5429519899791762269">🔀</e> Change
    .promocode = <e id="5431674023459204413">🎟</e> Activate promocode
    .promocode-confirm = <e id="5431365176655913424">✅</e> Confirm
    .pay = <e id="5429173368945420581">💳</e> Pay
    .get = <e id="5429103378158366023">🎁</e> Get for free
    .connect = <e id="5429282761762450449">⚡</e> Connect

btn-back =
    .general = <e id="5429579775930837843">⬅️</e> Back
    .menu = <e id="5431571386625732786">🏠</e> Main menu
    .menu-return = <e id="5431571386625732786">🏠</e> Return to main menu

btn-common =
    .cancel = <e id="5431373569022009585">❌</e> Cancel
    .notification-close = <e id="5431373569022009585">❌</e> Close

# Menu buttons
btn-how-connect = <e id="5431382528323788017">🧭</e> How to connect?
btn-proxy = 👀 Share Mtproxy

# <<< rain-emoji

# System labels (squad for imported users)
IMPORTED = 🔄 Imported

# Rain VPN plan names
Free = 🌧️ Free | Basic
Solo = 👤 Solo | 2 devices
Duo = 👥 Duo | 4 devices
Family = 👨‍👩‍👧 Family | 6 devices
Team = 🏢 Team | 10 devices

# Rain VPN plan descriptions
plan-desc-free = Free long-term access to test the service in real conditions.
plan-desc-solo = Unlimited VPN for personal use. Connect your devices and enjoy without limits.
plan-desc-duo = Extended plan for two users or multiple devices.
plan-desc-family = Optimal for the whole family.
plan-desc-team = For a team or project. One plan — many devices.
