// Рендер исходников из icons.mjs в PNG 100x100 — формат, который принимает
// @Stickers при создании набора кастом-эмодзи.
//
//   npm install
//   node build.mjs
//
// Результат: png/<name>.png + contact-sheet.svg для быстрого просмотра пака.

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Resvg } from "@resvg/resvg-js";

import { ICONS } from "./icons.mjs";

const ROOT = dirname(fileURLToPath(import.meta.url));
const OUT = join(ROOT, "png");

const wrap = (body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">${body}</svg>`;

mkdirSync(OUT, { recursive: true });

const names = Object.keys(ICONS);

for (const name of names) {
  const svg = wrap(ICONS[name].svg);
  const png = new Resvg(svg, { fitTo: { mode: "width", value: 100 } })
    .render()
    .asPng();
  writeFileSync(join(OUT, `${name}.png`), png);
  writeFileSync(join(ROOT, "svg", `${name}.svg`), svg);
}

// Контактный лист: все иконки в сетке на тёмном фоне бота, плюс тот же ряд
// в 22px — реальный размер эмодзи в кнопке. Мелкий ряд важнее крупного:
// именно так пак увидит пользователь.
const COLS = 8;
const CELL = 116;
const rows = Math.ceil(names.length / COLS);
const W = COLS * CELL + 40;
const H = rows * (CELL + 26) + 60;

const cells = names
  .map((name, i) => {
    const cx = (i % COLS) * CELL;
    const cy = Math.floor(i / COLS) * (CELL + 26);
    const label = name.length > 15 ? `${name.slice(0, 14)}…` : name;
    return `
      <g transform="translate(${cx} ${cy})">
        <rect x="6" y="6" width="${CELL - 12}" height="${CELL - 12}" rx="14" fill="#16283F"/>
        <g transform="translate(${(CELL - 76) / 2} ${(CELL - 76) / 2}) scale(0.76)">${ICONS[name].svg}</g>
        <g transform="translate(${CELL / 2 - 11} ${CELL - 2}) scale(0.22)">${ICONS[name].svg}</g>
        <text x="${CELL / 2 + 18}" y="${CELL + 16}" font-family="Segoe UI, sans-serif" font-size="11"
              fill="#8FA6C0" text-anchor="start">${label}</text>
      </g>`;
  })
  .join("");

const sheet = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <rect width="${W}" height="${H}" fill="#0F1C2E"/>
  <text x="24" y="38" font-family="Segoe UI, sans-serif" font-size="20" font-weight="600" fill="#EEF4FB">
    Rain VPN — премиум-эмодзи (${names.length} шт.)
  </text>
  <g transform="translate(12 56)">${cells}</g>
</svg>`;

writeFileSync(join(ROOT, "contact-sheet.svg"), sheet);
writeFileSync(
  join(ROOT, "contact-sheet.png"),
  new Resvg(sheet, { fitTo: { mode: "width", value: W } }).render().asPng(),
);

// Таблица соответствий генерируется из icons.mjs, чтобы не разъезжаться с ним.
const table = names
  .map((n) => {
    const { title, fallback, keys } = ICONS[n];
    const k = (keys ?? []).map((x) => `\`${x}\``).join("<br>") || "—";
    return `| \`${n}.png\` | ${title} | ${fallback} | ${k} |`;
  })
  .join("\n");

writeFileSync(
  join(ROOT, "MAPPING.md"),
  `<!-- Генерируется build.mjs. Правьте icons.mjs, не этот файл. -->

# Пак Rain VPN → ключи переводов

Порядок строк совпадает с порядком загрузки в @Stickers: заливайте файлы
сверху вниз, тогда \`ids.json\` заполняется тем же порядком.

| Файл | Назначение | Запасной эмодзи | Ключи \`custom.ftl\` |
|---|---|---|---|
${table}
`,
);

console.log(`rendered ${names.length} icons -> png/, MAPPING.md updated`);
