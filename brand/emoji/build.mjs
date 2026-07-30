// Сборка премиум-пака Rain VPN: SVG-кадры -> PNG -> WEBM (VP9 + альфа).
//
// Требования Telegram к видео-эмодзи: ровно 100x100, VP9, не длиннее 3 с,
// до 30 FPS, не тяжелее 256 КБ, без аудиодорожки. Скрипт проверяет вес
// каждого файла и падает, если лимит превышен.
//
//   npm install && node build.mjs
//   node build.mjs --preview   # только превью, без кодирования

import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Resvg } from "@resvg/resvg-js";

import { ICONS, wrapFrame } from "./pack.mjs";
import { DEFS } from "./style.mjs";

const ROOT = dirname(fileURLToPath(import.meta.url));
const WEBM = join(ROOT, "webm");
const TMP = join(ROOT, ".frames");

const FPS = 30;
const SECONDS = 1.5;
const FRAMES = FPS * SECONDS;
const LIMIT_KB = 256;
const PREVIEW_ONLY = process.argv.includes("--preview");

const png = (svg, size = 100) =>
  new Resvg(svg, { fitTo: { mode: "width", value: size } }).render().asPng();

const names = Object.keys(ICONS);
const report = [];

if (!PREVIEW_ONLY) {
  mkdirSync(WEBM, { recursive: true });

  for (const name of names) {
    rmSync(TMP, { recursive: true, force: true });
    mkdirSync(TMP, { recursive: true });

    for (let i = 0; i < FRAMES; i++) {
      writeFileSync(
        join(TMP, `f${String(i).padStart(3, "0")}.png`),
        png(wrapFrame(ICONS[name].render(i / FRAMES))),
      );
    }

    const out = join(WEBM, `${name}.webm`);
    rmSync(out, { force: true });
    // yuva420p сохраняет альфу отдельным потоком; -an убирает звук.
    execFileSync(
      "ffmpeg",
      [
        "-hide_banner", "-loglevel", "error",
        "-framerate", String(FPS),
        "-i", join(TMP, "f%03d.png"),
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuva420p",
        "-b:v", "0", "-crf", "34",
        "-auto-alt-ref", "0",
        "-an",
        out,
      ],
      { stdio: "inherit" },
    );

    report.push({ name, kb: statSync(out).size / 1024 });
  }

  rmSync(TMP, { recursive: true, force: true });
}

// ── Превью: фазы петли построчно ──
const STEPS = 6;
const CELL = 104;
const sheetW = 190 + STEPS * CELL;
const sheetH = names.length * CELL + 56;

const rows = names
  .map((name, r) => {
    const icon = ICONS[name];
    const cells = Array.from({ length: STEPS }, (_, c) => {
      return `<g transform="translate(${190 + c * CELL} 0)">
          <rect x="2" y="2" width="100" height="100" rx="14" fill="#16283F"/>
          <g transform="translate(2 2)">${icon.render(c / STEPS)}</g>
        </g>`;
    }).join("");
    return `<g transform="translate(0 ${r * CELL + 40})">
        <text x="16" y="50" font-family="Segoe UI, sans-serif" font-size="15" fill="#E6EFFA">${name}</text>
        <text x="16" y="70" font-family="Segoe UI, sans-serif" font-size="11" fill="#7F97B4">${icon.fallback} ${icon.title}</text>
        <text x="16" y="88" font-family="Segoe UI, sans-serif" font-size="10" fill="#54708F">${icon.tier}</text>
        ${cells}
      </g>`;
  })
  .join("");

writeFileSync(
  join(ROOT, "preview-phases.png"),
  png(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${sheetW}" height="${sheetH}" viewBox="0 0 ${sheetW} ${sheetH}">
      ${DEFS}<rect width="${sheetW}" height="${sheetH}" fill="#0F1C2E"/>
      <text x="16" y="26" font-family="Segoe UI, sans-serif" font-size="17" font-weight="600"
            fill="#EEF4FB">Rain VPN — премиум-пак, ${names.length} иконок</text>
      ${rows}</svg>`,
    sheetW,
  ),
);

// ── Превью: крупная сетка одним кадром ──
const COLS = 6;
const bigH = 40 + Math.ceil(names.length / COLS) * 150;
const big = names
  .map(
    (name, i) => `<g transform="translate(${20 + (i % COLS) * 150} ${30 + Math.floor(i / COLS) * 150})">
      <rect width="134" height="134" rx="22" fill="#16283F"/>
      <g transform="translate(7 7) scale(1.2)">${ICONS[name].render(0.2)}</g>
    </g>`,
  )
  .join("");

writeFileSync(
  join(ROOT, "preview-grid.png"),
  png(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${20 + COLS * 150}" height="${bigH}" viewBox="0 0 ${20 + COLS * 150} ${bigH}">
      ${DEFS}<rect width="${20 + COLS * 150}" height="${bigH}" fill="#0F1C2E"/>${big}</svg>`,
    20 + COLS * 150,
  ),
);

// ── Анимированное превью: единственный способ оценить движение всего пака ──
{
  const S = 92;
  const COLS_A = 6;
  const ROWS_A = Math.ceil(names.length / COLS_A);
  const W = COLS_A * S;
  const H = ROWS_A * S;
  rmSync(TMP, { recursive: true, force: true });
  mkdirSync(TMP, { recursive: true });

  // Каждый второй кадр: для превью хватает, а GIF выходит вдвое легче.
  let n = 0;
  for (let i = 0; i < FRAMES; i += 2) {
    const cells = names
      .map(
        (name, k) => `<g transform="translate(${(k % COLS_A) * S} ${Math.floor(k / COLS_A) * S})">
          <g transform="translate(6 6) scale(0.8)">${ICONS[name].render(i / FRAMES)}</g>
        </g>`,
      )
      .join("");
    writeFileSync(
      join(TMP, `s${String(n++).padStart(3, "0")}.png`),
      png(
        `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
          ${DEFS}<rect width="${W}" height="${H}" fill="#16283F"/>${cells}</svg>`,
        W,
      ),
    );
  }

  const gif = join(ROOT, "preview-motion.gif");
  rmSync(gif, { force: true });
  execFileSync(
    "ffmpeg",
    [
      "-hide_banner", "-loglevel", "error",
      "-framerate", String(FPS / 2),
      "-i", join(TMP, "s%03d.png"),
      "-filter_complex",
      "[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3",
      "-loop", "0",
      gif,
    ],
    { stdio: "inherit" },
  );
  rmSync(TMP, { recursive: true, force: true });
  console.log(`preview-motion.gif — ${(statSync(gif).size / 1024).toFixed(0)} КБ\n`);
}

// ── Таблица соответствий: генерируется, руками не правится ──
const table = names
  .map((n) => {
    const { title, fallback, keys, tier, concept } = ICONS[n];
    const k = (keys ?? []).map((x) => `\`${x}\``).join("<br>") || "—";
    return `| \`${n}.webm\` | ${tier} | ${title} | ${fallback} | ${concept ?? "—"} | ${k} |`;
  })
  .join("\n");

writeFileSync(
  join(ROOT, "MAPPING.md"),
  `<!-- Генерируется build.mjs. Правьте icons-*.mjs и wiring.mjs, не этот файл. -->

# Пак Rain VPN → ключи переводов

Порядок строк совпадает с порядком загрузки в @Stickers: заливайте файлы
сверху вниз, тогда заполнять \`ids.json\` удобнее.

| Файл | Слой | Назначение | Запасной эмодзи | Что изображено | Ключи \`custom.ftl\` |
|---|---|---|---|---|---|
${table}
`,
);

if (report.length) {
  console.log("webm:");
  let over = 0;
  for (const r of report) {
    const bad = r.kb > LIMIT_KB;
    if (bad) over += 1;
    console.log(`  ${r.name.padEnd(18)} ${r.kb.toFixed(1)} КБ${bad ? "  ПРЕВЫШЕН ЛИМИТ" : ""}`);
  }
  const total = report.reduce((s, r) => s + r.kb, 0);
  console.log(`  ${"итого".padEnd(18)} ${total.toFixed(0)} КБ`);
  if (over) {
    console.error(`\n${over} файл(ов) тяжелее ${LIMIT_KB} КБ — Telegram их не примет.`);
    process.exit(1);
  }
}

console.log(`\n${names.length} иконок, ${FRAMES} кадров, ${SECONDS}s петля`);
