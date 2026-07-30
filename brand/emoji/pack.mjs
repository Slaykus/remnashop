// Сборка пака: отрисовка (ядро + утилита) склеивается с проводкой.
// Порядок здесь — это и порядок загрузки в @Stickers, и порядок MAPPING.md.

import { DEFS } from "./style.mjs";
import { ICONS_CORE } from "./icons-core.mjs";
import { ICONS_UTIL } from "./icons-util.mjs";
import { WIRING } from "./wiring.mjs";

const merge = (group, tier) =>
  Object.entries(group).map(([name, icon]) => {
    const w = WIRING[name];
    if (!w) throw new Error(`нет проводки для иконки «${name}» — допишите wiring.mjs`);
    return [name, { ...icon, ...w, tier }];
  });

const entries = [...merge(ICONS_CORE, "ядро"), ...merge(ICONS_UTIL, "утилита")];

const unused = Object.keys(WIRING).filter((n) => !entries.some(([k]) => k === n));
if (unused.length) {
  throw new Error(`проводка есть, а иконки нет: ${unused.join(", ")}`);
}

export const ICONS = Object.fromEntries(entries);

export const wrapFrame = (body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">${DEFS}${body}</svg>`;
