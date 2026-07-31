// Словарь брендовых примитивов Rain VPN.
//
// Ядро и утилитарный слой рисуются из одних и тех же форм — иначе пак
// расползётся на два разных набора. Здесь только геометрия; палитра,
// тени и блики живут в style.mjs.

import { outline, rim, shade, spec } from "./style.mjs";

export const CLOUD = "M30 66 A18 18 0 0 1 32 31 A22 22 0 0 1 71 37 A15 15 0 0 1 72 66 Z";

/** Капля — атом системы. Начало координат в центре тела, остриё вверх. */
export const drop = (s = 1) =>
  `M0 ${-13 * s} C${7 * s} ${-3 * s} ${10 * s} ${2 * s} ${10 * s} ${6 * s} ` +
  `A${10 * s} ${10 * s} 0 0 1 ${-10 * s} ${6 * s} C${-10 * s} ${2 * s} ${-7 * s} ${-3 * s} 0 ${-13 * s} Z`;

/** Готовая капля с бликом и светлой обводкой. */
export const dropAt = (x, y, s, ramp = "cyan", o = 1) => `
  <g transform="translate(${x} ${y})" opacity="${o.toFixed(3)}">
    <path d="${drop(s)}" fill="url(#g-${ramp})"/>
    ${outline(drop(s), Math.max(1.6, 2.4 * s), 0.85)}
    ${spec(-2.6 * s, -4.4 * s, 2.5 * s, 3.5 * s, 0.8)}
  </g>`;

/** Дуга-купол: защита. Рифмуется с дугами логотипа. */
export const dome = (cx, cy, r, color = "#8DCCFF", w = 5, o = 1) =>
  `<path d="M${cx - r} ${cy} A${r} ${r} 0 0 1 ${cx + r} ${cy}" fill="none"
     stroke="${color}" stroke-opacity="${o.toFixed(3)}" stroke-width="${w}" stroke-linecap="round"/>`;

/** Облако — сам сервис. */
export const cloudBody = (fill = "url(#g-cloud)", dy = 0, scale = 1) => `
  <g transform="translate(${50 - 50 * scale} ${dy}) scale(${scale})">
    ${shade(`<path d="${CLOUD}"/>`, 5, 0.4)}
    <path d="${CLOUD}" fill="${fill}"/>
    ${outline(CLOUD, 3.4 / scale, 0.55)}
    ${rim("M34 40 A19 19 0 0 1 65 33", 0.6)}
    ${spec(42, 42, 14, 7, 0.4, -18)}
  </g>`;

/**
 * Круглая плашка под утилитарный глиф. Утилита обязана читаться мгновенно,
 * поэтому здесь форма привычная — брендовой её делает палитра и пластика.
 */
export const disc = (ramp, r = 46, cx = 50, cy = 50) => `
  ${shade(`<circle cx="${cx}" cy="${cy}" r="${r}"/>`, 5, 0.45)}
  <circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#g-${ramp})"/>
  <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#FFFFFF"
          stroke-opacity="0.85" stroke-width="3.2"/>
  ${spec(cx - 12, cy - 16, r * 0.5, r * 0.3, 0.45, -20)}`;

/** Скруглённая карточка — основа для карты оплаты, билета, корзины. */
export const card = (x, y, w, h, r, ramp) => `
  ${shade(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}"/>`, 5, 0.45)}
  <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="url(#g-${ramp})"/>
  <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="none"
        stroke="#FFFFFF" stroke-opacity="0.8" stroke-width="3"/>`;
