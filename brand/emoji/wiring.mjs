// Привязка иконок к ключам переводов и запасным Unicode-эмодзи.
//
// Держится отдельно от отрисовки намеренно: арт и проводка меняются в разном
// темпе, а когда они лежали вместе, запасные эмодзи разъехались с custom.ftl.
//
// fallback обязан совпадать с эмодзи, который уже стоит в custom.ftl, —
// apply-ids.mjs подставляет именно его внутрь тега <e id="...">.
// keys перечисляет только ключи внутри маркеров rain-emoji; пустой массив
// означает, что иконка не привязана к кнопке (используется в тексте сообщений).

/**
 * Эмодзи в текстах сообщений.
 *
 * Кнопки правятся в custom.ftl, а тексты — во встроенных файлах образа, и вот
 * почему. Заголовки вроде hdr-user-profile подставляются в сообщения ссылкой
 * `{ hdr-user-profile }`, а ссылки в Fluent резолвятся внутри своего бандла.
 * custom.ftl загружается отдельным бандлом, поэтому переопределение заголовка
 * там до сообщения не доедет — сообщение возьмёт встроенный вариант.
 *
 * Структура: файл -> ключ -> список пар «эмодзи в тексте» → «иконка пака».
 * Эмодзи может не совпадать с запасным у иконки: в тексте стоит 💳, а иконка
 * называется subscription — сопоставление задаётся явно.
 */
export const MESSAGE_EMOJI = {
  "utils.ftl": {
    // Ступени реферальной программы. Порядок задан в frg-user: облако, туча,
    // дождь, шторм — от 5% до 25% скидки.
    "frg-user": [
      ["☁️", "tier-cloud"],
      ["🌩️", "tier-thunder"],
      ["🌧️", "tier-rain"],
      ["⛈️", "tier-storm"],
    ],
    "hdr-user": [["👤", "profile"]],
    "hdr-node": [["🖥", "node"]],
    "hdr-user-profile": [["👤", "profile"]],
    "hdr-payment": [["💰", "buy"]],
    "hdr-error": [["⚠️", "warning"]],
    "hdr-hwid": [["📱", "devices"]],
    "hdr-subscription": [
      ["🎁", "gift"],
      ["💳", "subscription"],
    ],
    "hdr-plan": [
      ["🎁", "gift"],
      ["📦", "plan"],
    ],
  },
  "messages.ftl": {
    "msg-main-menu": [["🎁", "gift"]],
    "msg-menu-devices": [["📱", "devices"]],
    "msg-menu-devices-confirm-delete": [["🗑", "delete"]],
    "msg-menu-devices-confirm-delete-all": [["🗑", "delete"]],
    "msg-menu-devices-confirm-reissue": [
      ["🔄", "reissue"],
      ["⚠️", "warning"],
    ],
    "msg-menu-invite": [
      ["👥", "invite"],
      ["🤝", "invite"],
      ["💳", "subscription"],
      ["💎", "points"],
      ["📊", "stats"],
      ["🏆", "points"],
      ["☁️", "tier-cloud"],
      ["🌩️", "tier-thunder"],
      ["🌧️", "tier-rain"],
      ["⛈️", "tier-storm"],
    ],
    "msg-menu-invite-about": [
      ["🎁", "gift"],
      ["💎", "points"],
      ["✨", "sparkle"],
      ["💡", "sparkle"],
    ],
    "msg-subscription-main": [
      ["💳", "subscription"],
      ["🔴", "node"],
      ["🚫", "restricted"],
    ],
    "msg-subscription-plans": [["📦", "plan"]],
    "msg-subscription-plan": [
      ["📦", "plan"],
      ["⚠️", "warning"],
    ],
    "msg-subscription-payment-method": [["💳", "pay"]],
    "msg-subscription-confirm": [
      ["🛒", "buy"],
      ["⚠️", "warning"],
    ],
    "msg-subscription-success": [["✅", "confirm"]],
    "msg-subscription-trial": [["✅", "confirm"]],
    "msg-subscription-failed": [["❌", "cancel"]],
    "msg-promocode-input": [["🎟", "promocode"]],
    "msg-promocode-confirm": [
      ["🎟", "promocode"],
      ["🎁", "gift"],
      ["⚠️", "warning"],
    ],
    "msg-subscription-traffic-reset-confirm": [
      ["⚠️", "warning"],
      ["✅", "confirm"],
    ],
  },
};

export const WIRING = {
  // ── брендовое ядро ──
  connect: { fallback: "⚡", keys: ["btn-menu.connect", "btn-subscription.connect"] },
  subscription: { fallback: "💎", keys: ["btn-menu.subscription"] },
  trial: { fallback: "🌧️", keys: ["btn-menu.trial", "btn-menu.trial-paid"] },
  devices: { fallback: "📱", keys: ["btn-menu.devices"] },
  invite: { fallback: "👥", keys: ["btn-menu.invite"] },
  support: { fallback: "💬", keys: ["btn-menu.support"] },
  "web-cabinet": { fallback: "🌐", keys: ["btn-menu.web-cabinet"] },
  dashboard: { fallback: "🎛", keys: ["btn-menu.dashboard"] },
  traffic: { fallback: "🌐", keys: [] },
  plan: { fallback: "🗂", keys: ["btn-subscription.plan"] },
  points: { fallback: "⭐", keys: ["btn-invite.withdraw-points"] },
  renew: { fallback: "🔁", keys: ["btn-subscription.renew"] },
  shield: { fallback: "🛡", keys: [] },
  logo: { fallback: "🌧", keys: [] },

  // ── утилитарный слой ──
  back: {
    fallback: "⬅️",
    keys: [
      "btn-back.general",
      "btn-subscription.back-plans",
      "btn-subscription.back-duration",
      "btn-subscription.back-payment-method",
    ],
  },
  home: { fallback: "🏠", keys: ["btn-back.menu", "btn-back.menu-return"] },
  cancel: {
    fallback: "❌",
    keys: ["btn-common.cancel", "btn-common.notification-close", "btn-devices.cancel-reissue"],
  },
  confirm: {
    fallback: "✅",
    keys: [
      "btn-devices.confirm-delete",
      "btn-devices.confirm-reissue",
      "btn-subscription.promocode-confirm",
    ],
  },
  copy: { fallback: "📋", keys: ["btn-invite.copy", "btn-proxy-copy"] },
  send: { fallback: "📩", keys: ["btn-invite.send", "btn-proxy-share"] },
  qr: { fallback: "🔳", keys: ["btn-invite.qr"] },
  promocode: { fallback: "🎟", keys: ["btn-subscription.promocode"] },
  pay: { fallback: "💳", keys: ["btn-subscription.pay"] },
  buy: { fallback: "💰", keys: ["btn-subscription.new"] },
  gift: { fallback: "🎁", keys: ["btn-subscription.get"] },
  change: { fallback: "🔀", keys: ["btn-subscription.change"] },
  delete: { fallback: "🗑", keys: ["btn-devices.delete-all"] },
  reissue: { fallback: "🔄", keys: ["btn-devices.reissue", "btn-invite.reset-referral"] },
  clock: { fallback: "⏳", keys: [] },
  profile: { fallback: "👤", keys: [] },
  warning: { fallback: "⚠️", keys: [] },
  about: { fallback: "❓", keys: ["btn-invite.about"] },
  "connect-reserve": { fallback: "🔗", keys: ["btn-menu.connect-reserve"] },
  "how-connect": { fallback: "🧭", keys: ["btn-how-connect"] },

  // ── дополнение: только для текстов сообщений, кнопкам не назначены ──
  "tier-cloud": { fallback: "☁️", keys: [] },
  "tier-thunder": { fallback: "🌩️", keys: [] },
  "tier-rain": { fallback: "🌧️", keys: [] },
  "tier-storm": { fallback: "⛈️", keys: [] },
  stats: { fallback: "📊", keys: [] },
  sparkle: { fallback: "✨", keys: [] },
  node: { fallback: "🖥", keys: [] },
  restricted: { fallback: "🚫", keys: [] },
};
