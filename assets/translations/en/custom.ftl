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
    .trial = 🌧️ TRY FOR FREE
    .trial-paid = 🌧️ TRY FOR { $trial_price }
    .connect = ⚡ Connect
    .connect-reserve = 🔗 Connect (reserve)
    .devices = 📱 My devices
    .subscription = 💎 Subscription
    .invite = 👥 Invite a friend
    .support = 💬 Support
    .web-cabinet = 🌐 Web cabinet
    .dashboard = 🎛 Dashboard

btn-invite =
    .about = ❓ About the reward
    .copy = 📋 Copy link
    .send = 📩 Invite
    .qr = 🔳 QR code
    .withdraw-points = ⭐ Exchange points
    .reset-referral = 🔄 Reset referral link

btn-devices =
    .delete-all = 🗑 Delete all devices
    .reissue = 🔄 Reissue subscription
    .confirm-delete = ✅ Yes, delete
    .confirm-reissue = ✅ Yes, reset
    .cancel-reissue = ❌ No

btn-subscription =
    .plan = 🗂 Go to subscription
    .new = 💰 Buy subscription
    .renew = 🔁 Renew
    .change = 🔀 Change
    .promocode = 🎟 Activate promocode
    .promocode-confirm = ✅ Confirm
    .pay = 💳 Pay
    .get = 🎁 Get for free
    .connect = ⚡ Connect

btn-back =
    .general = ⬅️ Back
    .menu = 🏠 Main menu
    .menu-return = 🏠 Return to main menu

btn-common =
    .cancel = ❌ Cancel
    .notification-close = ❌ Close

# Menu buttons
btn-how-connect = 🧭 How to connect?
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
