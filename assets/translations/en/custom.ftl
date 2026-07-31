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
    .trial = <e id="5434043784549673084">🌧️</e> TRY FOR FREE
    .trial-paid = <e id="5434043784549673084">🌧️</e> TRY FOR { $trial_price }
    .connect = <e id="5431350621011746205">⚡</e> Connect
    .connect-reserve = <e id="5433768631764822220">🔗</e> Connect (reserve)
    .devices = <e id="5433608163196706522">📱</e> My devices
    .subscription = <e id="5431887891355703774">💎</e> Subscription
    .invite = <e id="5434067728992347183">👥</e> Invite a friend
    .support = <e id="5431834255804113657">💬</e> Support
    .web-cabinet = <e id="5431837348180565162">🌐</e> Web cabinet
    .dashboard = <e id="5431452321542350670">🎛</e> Dashboard

btn-invite =
    .about = <e id="5431426830911448115">❓</e> About the reward
    .copy = <e id="5433724552515460070">📋</e> Copy link
    .send = <e id="5433790699306787710">📩</e> Invite
    .qr = <e id="5431763569232355197">🔳</e> QR code
    .withdraw-points = <e id="5431658449907789518">⭐</e> Exchange points
    .reset-referral = <e id="5431450139698962745">🔄</e> Reset referral link

btn-devices =
    .delete-all = <e id="5433693255088776864">🗑</e> Delete all devices
    .reissue = <e id="5431450139698962745">🔄</e> Reissue subscription
    .confirm-delete = <e id="5433838236004820271">✅</e> Yes, delete
    .confirm-reissue = <e id="5433838236004820271">✅</e> Yes, reset
    .cancel-reissue = <e id="5433773811495378237">❌</e> No

btn-subscription =
    .plan = <e id="5431887363074728345">🗂</e> Go to subscription
    .new = <e id="5433718990532814817">💰</e> Buy subscription
    .renew = <e id="5433858061573858779">🔁</e> Renew
    .change = <e id="5433956609598464803">🔀</e> Change
    .promocode = <e id="5431503878329774916">🎟</e> Activate promocode
    .promocode-confirm = <e id="5433838236004820271">✅</e> Confirm
    .pay = <e id="5433625699548179370">💳</e> Pay
    .get = <e id="5431744001361352063">🎁</e> Get for free
    .connect = <e id="5431350621011746205">⚡</e> Connect

btn-back =
    .general = <e id="5434137616700186409">⬅️</e> Back
    .menu = <e id="5433682723828966023">🏠</e> Main menu
    .menu-return = <e id="5433682723828966023">🏠</e> Return to main menu

btn-common =
    .cancel = <e id="5433773811495378237">❌</e> Cancel
    .notification-close = <e id="5433773811495378237">❌</e> Close

# Menu buttons
btn-how-connect = <e id="5433622474027740592">🧭</e> How to connect?
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
