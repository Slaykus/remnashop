// Rain VPN — утилитарный слой пака.
//
// Здесь узнаваемость важнее метафоры: «назад», «отмена», «QR» обязаны
// читаться мгновенно, поэтому силуэты привычные. Брендовыми их делают
// палитра, градиентная пластика, свечение и капля как акцентная деталь —
// она есть почти в каждой иконке, но нигде не мешает распознаванию.

import { DEFS, bob, g, glow, outline, pulse, rim, shade, spec, wave } from "./style.mjs";
import { card, cloudBody, disc, dome, drop, dropAt } from "./primitives.mjs";

const white = (d, w = 11) =>
  `<path d="${d}" fill="none" stroke="#FFFFFF" stroke-width="${w}"
     stroke-linecap="round" stroke-linejoin="round"/>`;

export const ICONS_UTIL = {
  back: {
    title: "Назад",
    render: (t) => {
      const dx = -wave(t) * 1.4;
      return `
        ${glow("blue", 50, 52, 42, 0.16)}
        ${disc("slate")}
        <g transform="translate(${dx.toFixed(2)} 0)">${white("M58 30 L38 50 L58 70")}</g>`;
    },
  },

  home: {
    title: "Главное меню",
    render: (t) => {
      const p = pulse(t);
      return `
        ${glow("blue", 50, 52, 42, 0.2 + p * 0.1)}
        ${g(
          bob(t, 0.9),
          `
          ${shade(`<path d="M50 12 L92 48 H84 V86 H16 V48 H8 Z"/>`, 5, 0.45)}
          <path d="M50 12 L92 48 H84 V86 H16 V48 H8 Z" fill="url(#g-blue)"/>
          <path d="M50 12 L92 48 H8 Z" fill="url(#g-cyan)"/>
          ${outline("M50 12 L92 48 H84 V86 H16 V48 H8 Z", 3.4, 0.9)}
          <g opacity="${(0.85 + p * 0.15).toFixed(2)}">${dropAt(50, 64, 1.15, "cloud")}</g>`,
        )}`;
    },
  },

  cancel: {
    title: "Отмена",
    render: (t) => `
      ${glow("red", 50, 52, 44, 0.22 + pulse(t) * 0.12)}
      ${g(bob(t, 0.8), `${disc("red")}${white("M36 36 L64 64 M64 36 L36 64")}`)}`,
  },

  confirm: {
    title: "Подтвердить",
    render: (t) => `
      ${glow("green", 50, 52, 44, 0.22 + pulse(t) * 0.14)}
      ${g(bob(t, 0.8), `${disc("green")}${white("M32 51 L44 63 L69 38")}`)}`,
  },

  copy: {
    title: "Скопировать",
    render: (t) => {
      const d = wave(t) * 1.2;
      return `
        ${glow("blue", 50, 50, 42, 0.18)}
        ${card(10, 12, 52, 62, 9, "cyan")}
        <g transform="translate(${d.toFixed(2)} ${(-d).toFixed(2)})">
          ${card(36, 26, 54, 62, 9, "blue")}
          ${dropAt(63, 46, 0.9, "cloud")}
          <g stroke="#FFFFFF" stroke-opacity="0.85" stroke-width="5" stroke-linecap="round">
            <path d="M48 66 H78"/>
          </g>
        </g>`;
    },
  },

  send: {
    title: "Отправить",
    render: (t) => {
      const k = pulse(t);
      const dx = k * 3;
      return `
        ${glow("cyan", 50, 50, 42, 0.2)}
        <g opacity="${(0.85 - k * 0.45).toFixed(2)}">
          ${dropAt(20 - dx * 2, 74, 0.6, "cyan")}
        </g>
        <g transform="translate(${dx.toFixed(2)} ${(-dx).toFixed(2)})">
          ${shade(`<path d="M92 12 L8 46 L38 58 Z"/>`, 5, 0.45)}
          <path d="M92 12 L8 46 L38 58 Z" fill="url(#g-cloud)"/>
          <path d="M92 12 L38 58 L46 90 L60 68 Z" fill="url(#g-blue)"/>
          ${rim("M88 15 L40 55", 0.45, 2.2)}
        </g>`;
    },
  },

  qr: {
    title: "QR-код",
    render: (t) => {
      const eye = (x, y) => `
        <rect x="${x}" y="${y}" width="30" height="30" rx="7" fill="url(#g-blue)"/>
        <rect x="${x}" y="${y}" width="30" height="30" rx="7" fill="none"
              stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="3"/>
        <rect x="${x + 8}" y="${y + 8}" width="14" height="14" rx="3" fill="#0F1C2E"/>`;
      const p = pulse(t);
      return `
        ${glow("blue", 50, 50, 42, 0.18)}
        ${eye(8, 8)} ${eye(62, 8)} ${eye(8, 62)}
        <g fill="url(#g-cyan)">
          <rect x="62" y="62" width="12" height="12" rx="2.5"/>
          <rect x="80" y="62" width="12" height="12" rx="2.5"/>
          <rect x="62" y="80" width="12" height="12" rx="2.5"/>
          <rect x="46" y="46" width="12" height="12" rx="2.5"/>
        </g>
        <g opacity="${(0.75 + p * 0.25).toFixed(2)}">${dropAt(86, 86, 0.72, "cloud")}</g>`;
    },
  },

  promocode: {
    title: "Промокод",
    render: (t) => {
      const p = pulse(t);
      return `
        ${glow("gold", 50, 50, 42, 0.2 + p * 0.12)}
        ${g(
          bob(t, 0.8),
          `
          ${shade(
            `<path d="M14 26 H86 A6 6 0 0 1 92 32 V42 A9 9 0 0 0 92 60 V70 A6 6 0 0 1 86 76 H14 A6 6 0 0 1 8 70 V60 A9 9 0 0 0 8 42 V32 A6 6 0 0 1 14 26 Z"/>`,
            5,
            0.45,
          )}
          <path d="M14 26 H86 A6 6 0 0 1 92 32 V42 A9 9 0 0 0 92 60 V70 A6 6 0 0 1 86 76 H14 A6 6 0 0 1 8 70 V60 A9 9 0 0 0 8 42 V32 A6 6 0 0 1 14 26 Z"
                fill="url(#g-gold)"/>
          ${rim("M18 31 H80", 0.45, 2.2)}
          <path d="M56 30 V72" stroke="#8A5A10" stroke-opacity="0.45" stroke-width="4"
                stroke-linecap="round" stroke-dasharray="6 7"/>
          ${dropAt(32, 51, 1.1, "cloud")}`,
        )}`;
    },
  },

  pay: {
    title: "Оплатить",
    render: (t) => {
      const p = pulse(t);
      return `
        ${glow("blue", 50, 50, 42, 0.18)}
        ${g(
          bob(t, 0.8),
          `
          ${card(6, 22, 88, 56, 10, "blue")}
          <rect x="6" y="34" width="88" height="13" fill="#0F2E5C" opacity="0.8"/>
          ${rim("M12 28 H80", 0.4, 2.2)}
          <rect x="16" y="58" width="24" height="8" rx="4" fill="#FFFFFF" opacity="0.75"/>
          <g opacity="${(0.8 + p * 0.2).toFixed(2)}">${dropAt(74, 60, 0.95, "cyan")}</g>`,
        )}`;
    },
  },

  buy: {
    title: "Купить подписку",
    render: (t) => `
      ${glow("blue", 50, 54, 42, 0.18)}
      ${g(
        bob(t, 0.9),
        `
        <path d="M34 34 V26 A16 16 0 0 1 66 26 V34" fill="none" stroke="#8DCCFF"
              stroke-width="6" stroke-linecap="round"/>
        ${shade(`<path d="M16 34 H84 L90 88 A4 4 0 0 1 86 92 H14 A4 4 0 0 1 10 88 Z"/>`, 5, 0.45)}
        <path d="M16 34 H84 L90 88 A4 4 0 0 1 86 92 H14 A4 4 0 0 1 10 88 Z" fill="url(#g-blue)"/>
        ${outline("M16 34 H84 L90 88 A4 4 0 0 1 86 92 H14 A4 4 0 0 1 10 88 Z", 3.4, 0.9)}
        ${dropAt(50, 62, 1.25, "cloud")}`,
      )}`,
  },

  gift: {
    title: "Получить бесплатно",
    render: (t) => {
      const p = pulse(t);
      return `
        ${glow("cyan", 50, 54, 42, 0.2 + p * 0.12)}
        ${g(
          bob(t, 0.9),
          `
          ${dropAt(38, 22, 0.85, "cyan", 0.9)}
          ${dropAt(62, 22, 0.85, "cyan", 0.9)}
          ${card(10, 34, 80, 16, 5, "cloud")}
          ${shade(`<path d="M16 50 H84 V84 A8 8 0 0 1 76 92 H24 A8 8 0 0 1 16 84 Z"/>`, 5, 0.45)}
          <path d="M16 50 H84 V84 A8 8 0 0 1 76 92 H24 A8 8 0 0 1 16 84 Z" fill="url(#g-blue)"/>
          ${outline("M16 50 H84 V84 A8 8 0 0 1 76 92 H24 A8 8 0 0 1 16 84 Z", 3.4, 0.9)}
          <rect x="43" y="34" width="14" height="58" fill="url(#g-cyan)"/>`,
        )}`;
    },
  },

  change: {
    title: "Изменить тариф",
    render: (t) => {
      const s = wave(t) * 2;
      return `
        ${glow("blue", 50, 50, 42, 0.18)}
        <g transform="translate(0 ${s.toFixed(2)})">
          <path d="M18 36 H68" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="16" stroke-linecap="round"/>
          <path d="M18 36 H68" stroke="#3B82E8" stroke-width="10" stroke-linecap="round"/>
          ${outline("M86 36 L62 22 V50 Z", 3.2, 0.9)}
          <path d="M86 36 L62 22 V50 Z" fill="url(#g-blue)"/>
        </g>
        <g transform="translate(0 ${(-s).toFixed(2)})">
          <path d="M82 68 H32" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="16" stroke-linecap="round"/>
          <path d="M82 68 H32" stroke="#5FD3F5" stroke-width="10" stroke-linecap="round"/>
          ${outline("M14 68 L38 54 V82 Z", 3.2, 0.9)}
          <path d="M14 68 L38 54 V82 Z" fill="url(#g-cyan)"/>
        </g>`;
    },
  },

  delete: {
    title: "Удалить",
    render: (t) => {
      const tilt = wave(t) * 3;
      return `
        ${glow("red", 50, 54, 42, 0.2)}
        <g transform="rotate(${tilt.toFixed(2)} 50 30)">
          <rect x="36" y="10" width="28" height="9" rx="4.5" fill="url(#g-red)"/>
          <rect x="12" y="21" width="76" height="13" rx="6.5" fill="url(#g-red)"/>
        </g>
        ${shade(`<path d="M22 38 H78 L72 86 A7 7 0 0 1 65 92 H35 A7 7 0 0 1 28 86 Z"/>`, 5, 0.45)}
        <path d="M22 38 H78 L72 86 A7 7 0 0 1 65 92 H35 A7 7 0 0 1 28 86 Z" fill="url(#g-red)"/>
        <g stroke="#7A1F16" stroke-opacity="0.45" stroke-width="5" stroke-linecap="round">
          <path d="M40 50 V78"/><path d="M60 50 V78"/>
        </g>`;
    },
  },

  reissue: {
    title: "Перевыпустить",
    render: (t) => {
      const rot = t * 360;
      const R = 30;
      const a = (t * 360 - 90) * (Math.PI / 180);
      return `
        ${glow("cyan", 50, 50, 42, 0.2)}
        <circle cx="50" cy="50" r="${R}" fill="none" stroke="#1B54AB" stroke-opacity="0.4" stroke-width="7"/>
        <circle cx="50" cy="50" r="${R}" fill="none" stroke="url(#g-cyan)" stroke-width="7"
                stroke-linecap="round"
                stroke-dasharray="${(2 * Math.PI * R * 0.62).toFixed(1)} ${(2 * Math.PI * R).toFixed(1)}"
                transform="rotate(${rot.toFixed(1)} 50 50)"/>
        ${dropAt(50 + Math.cos(a) * R, 50 + Math.sin(a) * R, 0.85, "cloud")}`;
    },
  },

  clock: {
    title: "Срок действия",
    render: (t) => {
      const min = t * 360;
      return `
        ${glow("blue", 50, 50, 42, 0.18)}
        ${disc("cloud", 38)}
        <circle cx="50" cy="50" r="38" fill="none" stroke="url(#g-blue)" stroke-width="7"/>
        <g stroke="#1B3A63" stroke-width="7" stroke-linecap="round">
          <path d="M50 28 V50"/>
        </g>
        <g transform="rotate(${min.toFixed(1)} 50 50)">
          <path d="M50 50 V22" stroke="#3B82E8" stroke-width="5" stroke-linecap="round"/>
        </g>
        <circle cx="50" cy="50" r="4.5" fill="#1B3A63"/>`;
    },
  },

  profile: {
    title: "Профиль",
    render: (t) => `
      ${glow("blue", 50, 52, 42, 0.2)}
      ${g(
        bob(t, 0.9),
        `
        ${disc("blue")}
        <g transform="translate(50 34) scale(1.15)">
          <path d="${drop(1)}" fill="#FFFFFF"/>
        </g>
        <path d="M26 82 A25 25 0 0 1 74 82 Z" fill="#FFFFFF"/>`,
      )}`,
  },

  warning: {
    title: "Внимание",
    render: (t) => {
      const p = pulse(t);
      return `
        ${glow("gold", 50, 56, 44, 0.2 + p * 0.25)}
        ${shade(`<path d="M50 10 L94 86 A6 6 0 0 1 88 92 H12 A6 6 0 0 1 6 86 Z"/>`, 5, 0.45)}
        <path d="M50 10 L94 86 A6 6 0 0 1 88 92 H12 A6 6 0 0 1 6 86 Z" fill="url(#g-gold)"/>
        ${rim("M50 16 L86 78", 0.3, 2.2)}
        <g opacity="${(0.85 + p * 0.15).toFixed(2)}">
          <rect x="44" y="40" width="12" height="28" rx="6" fill="#5A3606"/>
          <circle cx="50" cy="78" r="7" fill="#5A3606"/>
        </g>`;
    },
  },

  about: {
    title: "Подробнее",
    // Буква «i», а не знак вопроса: вопрос уже занят у «Поддержки» и
    // «Как подключиться», три одинаковых по смыслу значка путали.
    render: (t) => `
      ${glow("blue", 50, 52, 44, 0.3)}
      ${g(
        bob(t, 1),
        `
        ${disc("blue")}
        <circle cx="50" cy="30" r="6.5" fill="#FFFFFF"/>
        <rect x="43.5" y="43" width="13" height="30" rx="6.5" fill="#FFFFFF"/>`,
      )}`,
  },

  "connect-reserve": {
    title: "Подключиться (резерв)",
    render: (t) => {
      const d = wave(t) * 1.5;
      return `
        ${glow("cyan", 50, 50, 42, 0.2)}
        <g transform="rotate(-45 50 50)" fill="none" stroke-linecap="round">
          <g transform="translate(${(-d).toFixed(2)} 0)">
            <rect x="12" y="34" width="46" height="32" rx="16" stroke="#FFFFFF"
                  stroke-opacity="0.9" stroke-width="17"/>
            <rect x="12" y="34" width="46" height="32" rx="16" stroke="url(#g-cyan)" stroke-width="11"/>
          </g>
          <g transform="translate(${d.toFixed(2)} 0)">
            <rect x="42" y="34" width="46" height="32" rx="16" stroke="#FFFFFF"
                  stroke-opacity="0.9" stroke-width="17"/>
            <rect x="42" y="34" width="46" height="32" rx="16" stroke="url(#g-blue)" stroke-width="11"/>
          </g>
        </g>`;
    },
  },

  "how-connect": {
    title: "Как подключиться",
    // Маршрут из точек читался как навигация, а не как инструкция, и был залит
    // тем же синим, что и кнопка, — на синей кнопке линия исчезала полностью.
    // Теперь прямая отсылка к кнопке «Подключиться» плюс знак вопроса.
    render: (t) => {
      const p = pulse(t);
      return `
        ${glow("blue", 50, 50, 44, 0.3)}
        ${g(
          bob(t, 0.7),
          `
          <g transform="translate(-8 0) scale(0.82)">
            ${cloudBody("url(#g-cloud)", -6, 1)}
          </g>
          <g opacity="${(0.85 + p * 0.15).toFixed(2)}">
            <path d="M40 40 L24 62 H34 L30 82 L48 56 H36 Z" fill="url(#g-gold)"/>
            ${outline("M40 40 L24 62 H34 L30 82 L48 56 H36 Z", 2.6, 0.75)}
          </g>
          <g transform="translate(70 58)">
            <circle cx="0" cy="0" r="24" fill="url(#g-blue)"/>
            <circle cx="0" cy="0" r="24" fill="none" stroke="#FFFFFF"
                    stroke-opacity="0.9" stroke-width="3.2"/>
            <path d="M-9 -7 A9 9 0 1 1 0 6 V9" fill="none" stroke="#FFFFFF"
                  stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="0" cy="17" r="4.2" fill="#FFFFFF"/>
          </g>`,
        )}`;
    },
  },
};

export const wrapFrame = (body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">${DEFS}${body}</svg>`;
