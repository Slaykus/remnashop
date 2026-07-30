// Rain VPN — исходники премиум-эмодзи.
//
// Каждая иконка рисуется на канве 100x100 с прозрачным фоном — требование
// Telegram к кастом-эмодзи. Значимая часть держится в пределах 10..90, чтобы
// глиф не обрезался при рендере в кнопке (~20px) и не слипался с текстом.
//
// Формы намеренно крупные и заливочные: тонкие обводки на 20px исчезают.

export const PALETTE = {
  navy: "#16283F", // контур и тени
  navyDeep: "#0F1C2E",
  blue: "#4C9AE8", // основной акцент бренда
  blueDeep: "#2C6FB8", // нижняя грань, объём
  cloud: "#EEF4FB", // белый облачный
  cloudShade: "#CBD9EA",
  cyan: "#6FD3F0", // дождь
  cyanDeep: "#3FB4D8",
  gold: "#F5C451",
  goldDeep: "#D9A22F",
  green: "#4FD18B",
  greenDeep: "#2FA968",
  red: "#F2685E",
  redDeep: "#C9453B",
  violet: "#A78BFA",
  violetDeep: "#7C5CE0",
  slate: "#41618C", // нейтральная плашка: navy на тёмной теме бота не читается
  slateDeep: "#2C4463",
};

const P = PALETTE;

// Облако — базовый элемент логотипа, переиспользуется в нескольких иконках.
const cloud = (fill, shade, dy = 0) => `
  <g transform="translate(0 ${dy})">
    <path d="M28 68 A18 18 0 0 1 30 32 A22 22 0 0 1 71 38 A15 15 0 0 1 72 68 Z" fill="${fill}"/>
    <path d="M28 68 A18 18 0 0 1 27.5 58 L72.5 58 A15 15 0 0 1 72 68 Z" fill="${shade}"/>
  </g>`;

const drop = (x, y, s, fill, shade) => `
  <g transform="translate(${x} ${y}) scale(${s})">
    <path d="M0 -14 C7 -4 11 2 11 7 A11 11 0 0 1 -11 7 C-11 2 -7 -4 0 -14 Z" fill="${fill}"/>
    <path d="M-11 7 A11 11 0 0 0 11 7 C11 4 10 1 8 -3 C6 4 0 7 -6 4 C-9 2 -10 4 -11 7 Z" fill="${shade}"/>
  </g>`;

const bolt = (fill, shade) => `
  <path d="M56 12 L30 56 H46 L40 88 L70 42 H53 Z" fill="${fill}"/>
  <path d="M46 56 H30 L56 12 L50 40 Z" fill="${shade}"/>`;

const check = (fill, w = 11) =>
  `<path d="M31 51 L44 64 L69 38" fill="none" stroke="${fill}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;

const cross = (fill, w = 11) =>
  `<path d="M35 35 L65 65 M65 35 L35 65" fill="none" stroke="${fill}" stroke-width="${w}" stroke-linecap="round"/>`;

// Круглая плашка под глиф — даёт иконке вес и единый силуэт в ряду кнопок.
const disc = (fill, shade) => `
  <circle cx="50" cy="50" r="42" fill="${fill}"/>
  <path d="M50 92 A42 42 0 0 0 92 50 A42 42 0 0 1 50 92 Z" fill="${shade}"/>
  <circle cx="50" cy="50" r="42" fill="none" stroke="${shade}" stroke-width="3" opacity="0.5"/>`;

export const ICONS = {
  // ---------- Главное меню ----------

  connect: {
    title: "Подключиться",
    fallback: "⚡",
    keys: ["btn-menu.connect", "btn-subscription.connect"],
    svg: `
      ${cloud(P.cloud, P.cloudShade, 6)}
      ${bolt(P.gold, P.goldDeep)}`,
  },

  "connect-reserve": {
    title: "Подключиться (резерв)",
    fallback: "🔗",
    keys: ["btn-menu.connect-reserve"],
    svg: `
      <g transform="rotate(-45 50 50)" fill="none" stroke-width="12" stroke-linecap="round">
        <rect x="12" y="34" width="46" height="32" rx="16" stroke="${P.cyan}"/>
        <rect x="42" y="34" width="46" height="32" rx="16" stroke="${P.blue}"/>
      </g>`,
  },

  devices: {
    title: "Мои устройства",
    fallback: "📱",
    keys: ["btn-menu.devices"],
    svg: `
      <rect x="10" y="24" width="52" height="38" rx="6" fill="${P.blue}"/>
      <rect x="16" y="30" width="40" height="26" rx="3" fill="${P.cloud}"/>
      <path d="M6 66 H66 L62 75 H10 Z" fill="${P.blueDeep}"/>
      <rect x="66" y="18" width="28" height="64" rx="8" fill="${P.cyan}"/>
      <rect x="71" y="25" width="18" height="44" rx="3" fill="${P.cloud}"/>
      <circle cx="80" cy="75" r="3.5" fill="${P.cyanDeep}"/>`,
  },

  subscription: {
    title: "Подписка",
    fallback: "💎",
    keys: ["btn-menu.subscription"],
    svg: `
      <path d="M26 20 H74 L92 44 L50 88 L8 44 Z" fill="${P.cyan}"/>
      <path d="M26 20 H74 L92 44 H8 Z" fill="${P.cloud}"/>
      <path d="M8 44 H92 L50 88 Z" fill="${P.cyanDeep}" opacity="0.55"/>
      <path d="M50 20 L64 44 L50 88 L36 44 Z" fill="${P.cloud}" opacity="0.85"/>
      <path d="M26 20 L36 44 H8 Z" fill="${P.cloudShade}"/>`,
  },

  invite: {
    title: "Пригласить друга",
    fallback: "👥",
    keys: ["btn-menu.invite"],
    svg: `
      <circle cx="34" cy="34" r="15" fill="${P.blue}"/>
      <path d="M8 82 A26 26 0 0 1 60 82 Z" fill="${P.blue}"/>
      <circle cx="70" cy="40" r="13" fill="${P.cyan}"/>
      <path d="M48 82 A22 22 0 0 1 92 82 Z" fill="${P.cyan}"/>
      <path d="M48 82 A22 22 0 0 1 55 66 A26 26 0 0 1 60 82 Z" fill="${P.cyanDeep}"/>`,
  },

  support: {
    title: "Поддержка",
    fallback: "💬",
    keys: ["btn-menu.support"],
    svg: `
      <path d="M16 20 H84 A8 8 0 0 1 92 28 V62 A8 8 0 0 1 84 70 H44 L26 86 V70 H16 A8 8 0 0 1 8 62 V28 A8 8 0 0 1 16 20 Z" fill="${P.blue}"/>
      ${drop(50, 42, 1.15, P.cloud, P.cloudShade)}`,
  },

  "web-cabinet": {
    title: "Личный кабинет",
    fallback: "🌐",
    keys: ["btn-menu.web-cabinet"],
    svg: `
      <circle cx="50" cy="50" r="40" fill="${P.blue}"/>
      <path d="M50 10 A40 40 0 0 1 50 90 A40 40 0 0 1 50 10 Z" fill="${P.blueDeep}" opacity="0.35"/>
      <g stroke="${P.cloud}" stroke-width="6" fill="none">
        <circle cx="50" cy="50" r="40"/>
        <ellipse cx="50" cy="50" rx="17" ry="40"/>
        <path d="M12 36 H88 M12 64 H88"/>
      </g>`,
  },

  dashboard: {
    title: "Панель управления",
    fallback: "🎛",
    keys: ["btn-menu.dashboard"],
    svg: `
      <g stroke="${P.cloudShade}" stroke-width="9" stroke-linecap="round">
        <path d="M14 28 H86"/><path d="M14 50 H86"/><path d="M14 72 H86"/>
      </g>
      <circle cx="64" cy="28" r="13" fill="${P.blue}"/>
      <circle cx="34" cy="50" r="13" fill="${P.cyan}"/>
      <circle cx="70" cy="72" r="13" fill="${P.blue}"/>`,
  },

  trial: {
    title: "Пробный период",
    fallback: "🌧️",
    keys: ["btn-menu.trial", "btn-menu.trial-paid"],
    svg: `
      ${cloud(P.cloud, P.cloudShade, -8)}
      ${drop(30, 76, 0.72, P.cyan, P.cyanDeep)}
      ${drop(50, 84, 0.72, P.cyan, P.cyanDeep)}
      ${drop(70, 76, 0.72, P.cyan, P.cyanDeep)}`,
  },

  "how-connect": {
    title: "Как подключиться",
    fallback: "🧭",
    keys: ["btn-how-connect"],
    svg: `
      ${disc(P.blue, P.blueDeep)}
      <path d="M50 22 A28 28 0 0 1 50 78 A28 28 0 0 1 50 22 Z" fill="none" stroke="${P.cloud}" stroke-width="4" opacity="0.45"/>
      <path d="M68 32 L56 56 L32 68 L44 44 Z" fill="${P.cloud}"/>
      <path d="M56 56 L32 68 L44 44 Z" fill="${P.cyan}"/>
      <circle cx="50" cy="50" r="5" fill="${P.navy}"/>`,
  },

  warning: {
    title: "Подписка не работает",
    fallback: "⚠️",
    keys: [],
    svg: `
      <path d="M50 10 L94 86 A6 6 0 0 1 88 92 H12 A6 6 0 0 1 6 86 Z" fill="${P.gold}"/>
      <path d="M50 10 L94 86 A6 6 0 0 1 88 92 H50 Z" fill="${P.goldDeep}" opacity="0.45"/>
      <rect x="44" y="38" width="12" height="28" rx="6" fill="${P.navyDeep}"/>
      <circle cx="50" cy="76" r="7" fill="${P.navyDeep}"/>`,
  },

  // ---------- Устройства ----------

  delete: {
    title: "Удалить",
    fallback: "🗑",
    keys: ["btn-devices.delete-all"],
    svg: `
      <rect x="36" y="10" width="28" height="10" rx="5" fill="${P.redDeep}"/>
      <rect x="14" y="22" width="72" height="13" rx="6" fill="${P.red}"/>
      <path d="M22 38 H78 L72 86 A7 7 0 0 1 65 92 H35 A7 7 0 0 1 28 86 Z" fill="${P.red}"/>
      <g stroke="${P.redDeep}" stroke-width="6" stroke-linecap="round">
        <path d="M40 50 V80"/><path d="M60 50 V80"/>
      </g>`,
  },

  reissue: {
    title: "Перевыпустить / обновить",
    fallback: "🔄",
    keys: ["btn-devices.reissue", "btn-invite.reset-referral"],
    svg: `
      <path d="M50 16 A34 34 0 1 1 22 31" fill="none" stroke="${P.blue}" stroke-width="12" stroke-linecap="round"/>
      <path d="M50 4 L50 30 L30 17 Z" fill="${P.cyan}"/>`,
  },

  confirm: {
    title: "Подтвердить",
    fallback: "✅",
    keys: [
      "btn-devices.confirm-delete",
      "btn-devices.confirm-reissue",
      "btn-subscription.promocode-confirm",
    ],
    svg: `
      ${disc(P.green, P.greenDeep)}
      ${check(P.cloud, 12)}`,
  },

  cancel: {
    title: "Отмена",
    fallback: "❌",
    keys: ["btn-common.cancel", "btn-common.notification-close", "btn-devices.cancel-reissue"],
    svg: `
      ${disc(P.red, P.redDeep)}
      ${cross(P.cloud, 12)}`,
  },

  // ---------- Реферальная программа ----------

  copy: {
    title: "Скопировать ссылку",
    fallback: "📋",
    keys: ["btn-invite.copy", "btn-proxy-copy"],
    svg: `
      <rect x="12" y="12" width="52" height="62" rx="9" fill="${P.cyan}"/>
      <rect x="36" y="26" width="52" height="62" rx="9" fill="${P.blue}"/>
      <g stroke="${P.cloud}" stroke-width="7" stroke-linecap="round">
        <path d="M48 46 H76"/><path d="M48 60 H76"/><path d="M48 74 H64"/>
      </g>`,
  },

  send: {
    title: "Отправить",
    fallback: "📩",
    keys: ["btn-invite.send", "btn-proxy-share"],
    svg: `
      <path d="M92 12 L8 46 L36 58 Z" fill="${P.cloud}"/>
      <path d="M92 12 L36 58 L44 90 L58 68 Z" fill="${P.blue}"/>
      <path d="M36 58 L44 90 L58 68 Z" fill="${P.blueDeep}"/>`,
  },

  qr: {
    title: "QR-код",
    fallback: "🔳",
    keys: ["btn-invite.qr"],
    svg: `
      <g fill="${P.blue}">
        <path d="M10 10 H42 V42 H10 Z M18 18 V34 H34 V18 Z" fill-rule="evenodd"/>
        <path d="M58 10 H90 V42 H58 Z M66 18 V34 H82 V18 Z" fill-rule="evenodd"/>
        <path d="M10 58 H42 V90 H10 Z M18 66 V82 H34 V66 Z" fill-rule="evenodd"/>
      </g>
      <g fill="${P.cyan}">
        <rect x="58" y="58" width="13" height="13"/>
        <rect x="77" y="58" width="13" height="13"/>
        <rect x="58" y="77" width="13" height="13"/>
        <rect x="77" y="77" width="13" height="13"/>
      </g>`,
  },

  points: {
    title: "Баллы",
    fallback: "⭐",
    keys: ["btn-invite.withdraw-points"],
    svg: `
      ${disc(P.violet, P.violetDeep)}
      <path d="M50 26 L59 44 L79 47 L64 61 L68 81 L50 71 L32 81 L36 61 L21 47 L41 44 Z" fill="${P.cloud}"/>`,
  },

  about: {
    title: "Подробнее",
    fallback: "❓",
    keys: ["btn-invite.about"],
    svg: `
      ${disc(P.blue, P.blueDeep)}
      <path d="M38 38 A12 12 0 1 1 50 56 V62" fill="none" stroke="${P.cloud}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="50" cy="76" r="6.5" fill="${P.cloud}"/>`,
  },

  // ---------- Подписка и оплата ----------

  buy: {
    title: "Купить подписку",
    fallback: "💰",
    keys: ["btn-subscription.new"],
    svg: `
      <path d="M10 30 H78 A12 12 0 0 1 90 42 V76 A12 12 0 0 1 78 88 H22 A12 12 0 0 1 10 76 Z" fill="${P.blue}"/>
      <path d="M10 34 A10 10 0 0 1 20 24 L64 12 A8 8 0 0 1 74 20 L76 30 H10 Z" fill="${P.cyan}"/>
      <rect x="62" y="52" width="34" height="18" rx="9" fill="${P.cloud}"/>
      <circle cx="72" cy="61" r="5" fill="${P.blueDeep}"/>`,
  },

  renew: {
    title: "Продлить",
    fallback: "🔁",
    keys: ["btn-subscription.renew"],
    svg: `
      <rect x="10" y="20" width="80" height="72" rx="12" fill="${P.blue}"/>
      <rect x="10" y="20" width="80" height="20" rx="12" fill="${P.blueDeep}"/>
      <rect x="26" y="8" width="10" height="22" rx="5" fill="${P.cloudShade}"/>
      <rect x="64" y="8" width="10" height="22" rx="5" fill="${P.cloudShade}"/>
      <path d="M50 50 A18 18 0 1 1 35 58" fill="none" stroke="${P.cloud}" stroke-width="9" stroke-linecap="round"/>
      <path d="M50 42 L50 60 L37 51 Z" fill="${P.cyan}"/>`,
  },

  change: {
    title: "Изменить тариф",
    fallback: "🔀",
    keys: ["btn-subscription.change"],
    svg: `
      <g stroke="${P.blue}" stroke-width="11" stroke-linecap="round" fill="none">
        <path d="M20 36 H70"/>
      </g>
      <path d="M84 36 L60 22 L60 50 Z" fill="${P.blue}"/>
      <g stroke="${P.cyan}" stroke-width="11" stroke-linecap="round" fill="none">
        <path d="M80 68 H30"/>
      </g>
      <path d="M16 68 L40 54 L40 82 Z" fill="${P.cyan}"/>`,
  },

  promocode: {
    title: "Промокод",
    fallback: "🎟",
    keys: ["btn-subscription.promocode"],
    svg: `
      <path d="M14 24 H86 A6 6 0 0 1 92 30 V42 A9 9 0 0 0 92 58 V70 A6 6 0 0 1 86 76 H14 A6 6 0 0 1 8 70 V58 A9 9 0 0 0 8 42 V30 A6 6 0 0 1 14 24 Z" fill="${P.gold}"/>
      <path d="M50 28 V72" stroke="${P.goldDeep}" stroke-width="5" stroke-linecap="round" stroke-dasharray="7 8"/>
      <circle cx="29" cy="50" r="7" fill="${P.goldDeep}"/>
      <path d="M64 42 L72 50 L64 58" fill="none" stroke="${P.goldDeep}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>`,
  },

  pay: {
    title: "Оплатить",
    fallback: "💳",
    keys: ["btn-subscription.pay"],
    svg: `
      <rect x="6" y="22" width="88" height="58" rx="10" fill="${P.blue}"/>
      <rect x="6" y="34" width="88" height="14" fill="${P.navy}"/>
      <rect x="16" y="58" width="26" height="9" rx="4.5" fill="${P.cloud}"/>
      <circle cx="68" cy="63" r="9" fill="${P.gold}"/>
      <circle cx="80" cy="63" r="9" fill="${P.cyan}" opacity="0.85"/>`,
  },

  gift: {
    title: "Получить бесплатно",
    fallback: "🎁",
    keys: ["btn-subscription.get"],
    svg: `
      <rect x="10" y="36" width="80" height="16" rx="5" fill="${P.cyan}"/>
      <path d="M16 52 H84 V84 A8 8 0 0 1 76 92 H24 A8 8 0 0 1 16 84 Z" fill="${P.blue}"/>
      <rect x="42" y="36" width="16" height="56" fill="${P.gold}"/>
      <path d="M50 36 C50 36 30 36 30 24 A10 10 0 0 1 50 24 A10 10 0 0 1 70 24 C70 36 50 36 50 36 Z" fill="${P.gold}"/>
      <circle cx="50" cy="30" r="5" fill="${P.goldDeep}"/>`,
  },

  plan: {
    title: "Тарифы",
    fallback: "🗂",
    keys: ["btn-subscription.plan"],
    svg: `
      <path d="M50 8 L94 30 L50 52 L6 30 Z" fill="${P.cloud}"/>
      <path d="M50 34 L94 56 L50 78 L6 56 Z" fill="${P.cyan}"/>
      <path d="M50 56 L94 78 L50 96 L6 78 Z" fill="${P.blue}"/>`,
  },

  // ---------- Навигация ----------

  back: {
    title: "Назад",
    fallback: "⬅️",
    keys: [
      "btn-back.general",
      "btn-subscription.back-plans",
      "btn-subscription.back-duration",
      "btn-subscription.back-payment-method",
    ],
    svg: `
      ${disc(P.slate, P.slateDeep)}
      <path d="M58 30 L38 50 L58 70" fill="none" stroke="${P.cloud}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>`,
  },

  home: {
    title: "Главное меню",
    fallback: "🏠",
    keys: ["btn-back.menu", "btn-back.menu-return"],
    svg: `
      <rect x="20" y="42" width="60" height="50" rx="6" fill="${P.blue}"/>
      <path d="M50 6 L96 48 H82 L50 20 L18 48 H4 Z" fill="${P.cyan}"/>
      <rect x="40" y="60" width="20" height="32" rx="3" fill="${P.cloud}"/>`,
  },

  // ---------- Иконки для текста сообщений ----------

  profile: {
    title: "Профиль (шапка сообщения)",
    fallback: "👤",
    keys: [],
    svg: `
      ${disc(P.blue, P.blueDeep)}
      <circle cx="50" cy="40" r="15" fill="${P.cloud}"/>
      <path d="M24 82 A27 27 0 0 1 76 82 Z" fill="${P.cloud}"/>`,
  },

  shield: {
    title: "Защита / статус",
    fallback: "🛡",
    keys: [],
    svg: `
      <path d="M50 6 L88 20 V50 C88 72 70 88 50 94 C30 88 12 72 12 50 V20 Z" fill="${P.blue}"/>
      <path d="M50 6 L88 20 V50 C88 72 70 88 50 94 Z" fill="${P.blueDeep}" opacity="0.4"/>
      ${check(P.cloud, 11)}`,
  },

  traffic: {
    title: "Трафик",
    fallback: "🌐",
    keys: [],
    svg: `
      <g stroke-linecap="round" stroke-linejoin="round" fill="none" stroke-width="11">
        <path d="M32 84 V26" stroke="${P.cyan}"/>
        <path d="M68 16 V74" stroke="${P.blue}"/>
      </g>
      <path d="M32 8 L52 32 H12 Z" fill="${P.cyan}"/>
      <path d="M68 92 L48 68 H88 Z" fill="${P.blue}"/>`,
  },

  clock: {
    title: "Срок действия",
    fallback: "⏳",
    keys: [],
    svg: `
      ${disc(P.cloud, P.cloudShade)}
      <circle cx="50" cy="50" r="42" fill="none" stroke="${P.blue}" stroke-width="8"/>
      <g stroke="${P.navy}" stroke-width="9" stroke-linecap="round">
        <path d="M50 26 V52"/><path d="M50 52 L68 62"/>
      </g>`,
  },

  logo: {
    title: "Rain VPN (бренд-марка)",
    fallback: "🌧",
    keys: [],
    svg: `
      ${cloud(P.cloud, P.cloudShade, -10)}
      ${drop(26, 74, 0.62, P.blue, P.blueDeep)}
      ${drop(50, 82, 0.62, P.cyan, P.cyanDeep)}
      ${drop(74, 74, 0.62, P.blue, P.blueDeep)}`,
  },
};
