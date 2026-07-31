// Rain VPN — дополнение к паку.
//
// Эти иконки дозаливаются в уже существующий набор, поэтому идентификаторы
// ранее загруженных эмодзи не меняются.
//
// Четыре статуса реферальной программы различаются по двум независимым
// признакам — есть ли дождь и есть ли разряд. Такая матрица читается даже в
// кнопочные 20 пикселей, где отличить «плотность облака» уже невозможно.
//
//   Облако — чистое облако
//   Туча   — облако с разрядом, без дождя
//   Дождь  — облако с каплями, без разряда
//   Шторм  — облако с каплями и разрядом, тёмное

import { bob, g, glow, outline, pulse, shade, spec, wave } from "./style.mjs";
import { CLOUD, cloudBody, dropAt } from "./primitives.mjs";

const BOLT = "M56 44 L38 66 H49 L45 84 L64 60 H52 Z";

const bolt = (o = 1) => `
  <g opacity="${o.toFixed(2)}">
    <path d="${BOLT}" fill="url(#g-gold)"/>
    ${outline(BOLT, 2.6, 0.8)}
  </g>`;

/** Капля дождя с замкнутым по фазе циклом падения. */
const rain = (t, x, y0, phase, s = 0.6, dist = 22) => {
  const k = (t + phase) % 1;
  const o = Math.min(1, Math.sin(Math.PI * k) * 2.2);
  return dropAt(x, y0 + k * dist, s, "cyan", o);
};

export const ICONS_EXTRA = {
  // ── Статусы реферальной программы ──
  "tier-cloud": {
    title: "Статус: Облако",
    concept: "чистое облако — первая ступень реферальной программы",
    render: (t) => `
      ${glow("cloud", 50, 50, 44, 0.3)}
      ${g(bob(t, 1.1), cloudBody("url(#g-cloud)", 8, 1))}`,
  },

  "tier-thunder": {
    title: "Статус: Туча",
    concept: "облако с разрядом, без дождя — вторая ступень",
    render: (t) => `
      ${glow("gold", 50, 52, 44, 0.24 + pulse(t) * 0.24)}
      ${g(bob(t, 1.0), cloudBody("url(#g-cloud)", -10, 0.94))}
      ${bolt(0.85 + pulse(t) * 0.15)}`,
  },

  "tier-rain": {
    title: "Статус: Дождь",
    concept: "облако с каплями, без разряда — третья ступень",
    render: (t) => `
      ${glow("cyan", 50, 50, 44, 0.3)}
      ${g(bob(t, 1.0), cloudBody("url(#g-cloud)", -14, 0.94))}
      ${rain(t, 30, 58, 0)}
      ${rain(t, 50, 62, 0.36)}
      ${rain(t, 70, 58, 0.68)}`,
  },

  "tier-storm": {
    title: "Статус: Шторм",
    concept: "тёмное облако с каплями и разрядом — высшая ступень",
    render: (t) => `
      ${glow("violet", 50, 50, 46, 0.34 + pulse(t) * 0.2)}
      ${g(bob(t, 1.0), cloudBody("url(#g-slate)", -16, 0.94))}
      ${rain(t, 26, 56, 0.1, 0.55, 20)}
      ${rain(t, 74, 56, 0.55, 0.55, 20)}
      <g transform="translate(0 -4) scale(0.92) translate(4 4)">
        ${bolt(0.9 + pulse(t) * 0.1)}
      </g>`,
  },

  // ── Прочее, чего не хватало в текстах ──
  stats: {
    title: "Статистика",
    concept: "три растущих столбца — сводка по рефералам",
    render: (t) => {
      const bar = (x, base, i) => {
        const h = base + wave(t, i * 0.28) * 9;
        const y = 84 - h;
        return `
          <rect x="${x}" y="${y.toFixed(1)}" width="18" height="${h.toFixed(1)}" rx="6"
                fill="url(#g-${["cloud", "cyan", "blue"][i]})"/>
          <rect x="${x}" y="${y.toFixed(1)}" width="18" height="${h.toFixed(1)}" rx="6"
                fill="none" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="3"/>`;
      };
      return `
        ${glow("blue", 50, 54, 44, 0.3)}
        ${bar(14, 26, 0)}
        ${bar(41, 42, 1)}
        ${bar(68, 58, 2)}`;
    },
  },

  sparkle: {
    title: "Как получить награду",
    concept: "искра — раздел с условиями награды",
    render: (t) => {
      const p = pulse(t);
      const star = (cx, cy, r, o) => `
        <g transform="translate(${cx} ${cy}) rotate(${(t * 180).toFixed(1)})" opacity="${o}">
          <path d="M0 ${-r} Q${r * 0.22} ${-r * 0.22} ${r} 0 Q${r * 0.22} ${r * 0.22} 0 ${r}
                   Q${-r * 0.22} ${r * 0.22} ${-r} 0 Q${-r * 0.22} ${-r * 0.22} 0 ${-r} Z"
                fill="url(#g-gold)"/>
          <path d="M0 ${-r} Q${r * 0.22} ${-r * 0.22} ${r} 0 Q${r * 0.22} ${r * 0.22} 0 ${r}
                   Q${-r * 0.22} ${r * 0.22} ${-r} 0 Q${-r * 0.22} ${-r * 0.22} 0 ${-r} Z"
                fill="none" stroke="#FFFFFF" stroke-opacity="0.85" stroke-width="2.6"/>
        </g>`;
      return `
        ${glow("gold", 50, 50, 46, 0.3 + p * 0.24)}
        ${star(46, 46, 32 + p * 4, 1)}
        ${star(78, 24, 13 + p * 3, 0.95)}
        ${star(24, 78, 10, 0.85)}`;
    },
  },

  node: {
    title: "Сервер 4G/LTE",
    concept: "узел с расходящимся сигналом — отдельный сервер для мобильных сетей",
    render: (t) => {
      const wavesOut = [0, 1].map((i) => {
        const k = (t + i * 0.5) % 1;
        const r = 20 + k * 22;
        const o = Math.min(1, Math.sin(Math.PI * k) * 1.8) * 0.85;
        return `<g opacity="${o.toFixed(2)}">
            <path d="M${50 - r} 54 A${r} ${r} 0 0 1 ${50 + r} 54" fill="none"
                  stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="9" stroke-linecap="round"/>
            <path d="M${50 - r} 54 A${r} ${r} 0 0 1 ${50 + r} 54" fill="none"
                  stroke="#5FD3F5" stroke-width="5" stroke-linecap="round"/>
          </g>`;
      });
      return `
        ${glow("cyan", 50, 56, 44, 0.3)}
        ${wavesOut.join("")}
        ${shade(`<rect x="34" y="54" width="32" height="34" rx="9"/>`, 5, 0.45)}
        <rect x="34" y="54" width="32" height="34" rx="9" fill="url(#g-blue)"/>
        <rect x="34" y="54" width="32" height="34" rx="9" fill="none"
              stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="3.2"/>
        <circle cx="50" cy="71" r="6" fill="#FFFFFF"/>
        ${spec(43, 60, 7, 4, 0.6, -20)}`;
    },
  },

  restricted: {
    title: "Доступ ограничен",
    concept: "перечёркнутый круг — доступ к серверу закрыт",
    render: (t) => {
      const p = pulse(t);
      const r = 36 + p * 2.5;
      return `
        ${glow("red", 50, 52, 46, 0.3 + p * 0.24)}
        ${shade(`<circle cx="50" cy="50" r="${r}"/>`, 5, 0.45)}
        <circle cx="50" cy="50" r="${r.toFixed(1)}" fill="none" stroke="url(#g-red)" stroke-width="14"/>
        <circle cx="50" cy="50" r="${r.toFixed(1)}" fill="none" stroke="#FFFFFF"
                stroke-opacity="0.9" stroke-width="3.2"/>
        <circle cx="50" cy="50" r="${(r - 14).toFixed(1)}" fill="none" stroke="#FFFFFF"
                stroke-opacity="0.9" stroke-width="3.2"/>
        <g transform="rotate(-45 50 50)">
          <rect x="${(50 - r).toFixed(1)}" y="43" width="${(r * 2).toFixed(1)}" height="14" rx="7"
                fill="url(#g-red)"/>
          <rect x="${(50 - r).toFixed(1)}" y="43" width="${(r * 2).toFixed(1)}" height="14" rx="7"
                fill="none" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="3.2"/>
        </g>`;
    },
  },
};
