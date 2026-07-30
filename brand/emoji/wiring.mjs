// Привязка иконок к ключам переводов и запасным Unicode-эмодзи.
//
// Держится отдельно от отрисовки намеренно: арт и проводка меняются в разном
// темпе, а когда они лежали вместе, запасные эмодзи разъехались с custom.ftl.
//
// fallback обязан совпадать с эмодзи, который уже стоит в custom.ftl, —
// apply-ids.mjs подставляет именно его внутрь тега <e id="...">.
// keys перечисляет только ключи внутри маркеров rain-emoji; пустой массив
// означает, что иконка не привязана к кнопке (используется в тексте сообщений).

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
};
