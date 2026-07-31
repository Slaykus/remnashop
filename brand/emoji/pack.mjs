// Сборка пака: отрисовка (ядро + утилита) склеивается с проводкой.
// Порядок здесь — это и порядок загрузки в @Stickers, и порядок MAPPING.md.

import { DEFS } from "./style.mjs";
import { ICONS_CORE } from "./icons-core.mjs";
import { ICONS_EXTRA } from "./icons-extra.mjs";
import { ICONS_UTIL } from "./icons-util.mjs";
import { WIRING } from "./wiring.mjs";

const merge = (group, tier) =>
  Object.entries(group).map(([name, icon]) => {
    const w = WIRING[name];
    if (!w) throw new Error(`нет проводки для иконки «${name}» — допишите wiring.mjs`);
    return [name, { ...icon, ...w, tier }];
  });

// Дополнение идёт последним: так порядок MAPPING.md совпадает с порядком
// дозалива в уже существующий набор.
const entries = [
  ...merge(ICONS_CORE, "ядро"),
  ...merge(ICONS_UTIL, "утилита"),
  ...merge(ICONS_EXTRA, "дополнение"),
];

const unused = Object.keys(WIRING).filter((n) => !entries.some(([k]) => k === n));
if (unused.length) {
  throw new Error(`проводка есть, а иконки нет: ${unused.join(", ")}`);
}

export const ICONS = Object.fromEntries(entries);

/**
 * Небольшое общее увеличение глифа.
 *
 * Размер рендера эмодзи задаёт клиент, у бота управления им нет — но канва
 * наша, и раньше по её краю шло цветное свечение, которое на кнопке не
 * читалось и просто отъедало площадь. Свечение убрано, базовые формы
 * укрупнены, и остаток поля добирается этим масштабом.
 *
 * Больше брать нельзя: обводка внешнего силуэта начнёт срезаться краем.
 */
export const SCALE = 1.05;
export const scaled = (body) =>
  `<g transform="translate(50 50) scale(${SCALE}) translate(-50 -50)">${body}</g>`;

export const wrapFrame = (body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">${DEFS}${scaled(body)}</svg>`;
