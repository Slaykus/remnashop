// Забирает custom_emoji_id всего набора одним запросом и раскладывает их
// по именам иконок в ids.json.
//
//   node fetch-ids.mjs --set RainVPN --token <BOT_TOKEN>
//   node fetch-ids.mjs --set RainVPN --from set.json   # если getStickerSet вызвали сами
//
// Порядок стикеров в наборе может не совпадать с порядком MAPPING.md, поэтому
// сопоставление идёт по содержимому: файл из набора скачивается и сверяется по
// sha256 с локальным webm. Если Telegram файлы перекодировал и хеши разошлись,
// скрипт честно об этом скажет и сопоставит по порядку — тогда результат нужно
// проверить глазами по отчёту.

import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { ICONS } from "./pack.mjs";

const ROOT = dirname(fileURLToPath(import.meta.url));
const WEBM = join(ROOT, "webm");

const arg = (name) => {
  const i = process.argv.indexOf(`--${name}`);
  return i === -1 ? undefined : process.argv[i + 1];
};

const setName = arg("set");
const token = arg("token") ?? process.env.BOT_TOKEN;
const fromFile = arg("from");

if (!setName && !fromFile) {
  console.error("укажите --set <короткое_имя_набора> или --from <файл.json>");
  process.exit(1);
}

const api = async (method, params) => {
  const url = `https://api.telegram.org/bot${token}/${method}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(params),
  });
  const json = await res.json();
  if (!json.ok) throw new Error(`${method}: ${json.description}`);
  return json.result;
};

const sha = (buf) => createHash("sha256").update(buf).digest("hex");

// ── 1. Получаем набор ──
let stickerSet;
if (fromFile) {
  const raw = JSON.parse(readFileSync(fromFile, "utf8"));
  stickerSet = raw.result ?? raw;
} else {
  if (!token) {
    console.error("нет токена: передайте --token или задайте BOT_TOKEN в окружении");
    process.exit(1);
  }
  stickerSet = await api("getStickerSet", { name: setName });
}

const stickers = stickerSet.stickers ?? [];
console.log(`набор «${stickerSet.title ?? setName}»: ${stickers.length} эмодзи`);

const missingId = stickers.filter((s) => !s.custom_emoji_id).length;
if (missingId) {
  console.error(
    `у ${missingId} стикеров нет custom_emoji_id — похоже, это обычный стикерпак, а не набор эмодзи`,
  );
  process.exit(1);
}

// ── 2. Хеши локальных файлов ──
const localByHash = new Map();
const localNames = Object.keys(ICONS);
for (const name of localNames) {
  const p = join(WEBM, `${name}.webm`);
  if (!existsSync(p)) {
    console.error(`нет файла ${name}.webm — сначала выполните node build.mjs`);
    process.exit(1);
  }
  localByHash.set(sha(readFileSync(p)), name);
}

// ── 3. Сопоставление по содержимому ──
const ids = {};
const report = [];
let matched = 0;

if (token) {
  for (const [i, s] of stickers.entries()) {
    let name = null;
    try {
      const file = await api("getFile", { file_id: s.file_id });
      const res = await fetch(
        `https://api.telegram.org/file/bot${token}/${file.file_path}`,
      );
      const buf = Buffer.from(await res.arrayBuffer());
      name = localByHash.get(sha(buf)) ?? null;
    } catch (e) {
      // сеть или файл недоступны — упадём в сопоставление по порядку
    }
    if (name) matched += 1;
    report.push({ i, emoji: s.emoji, id: s.custom_emoji_id, name });
  }
} else {
  for (const [i, s] of stickers.entries()) {
    report.push({ i, emoji: s.emoji, id: s.custom_emoji_id, name: null });
  }
}

// ── 4. Нераспознанные: сначала переносим уже известные соответствия ──
// Кодировщик VP9 недетерминирован: пересборка даёт другие байты при той же
// картинке, и хеш локального файла перестаёт совпадать с загруженным. Тогда
// прежнее соответствие из ids.json надёжнее любого угадывания по порядку —
// достаточно убедиться, что такой id всё ещё есть в наборе.
const prevPath = join(ROOT, "ids.json");
if (existsSync(prevPath)) {
  const previous = JSON.parse(readFileSync(prevPath, "utf8"));
  const inSet = new Map(report.map((r) => [r.id, r]));
  const taken = new Set(report.filter((r) => r.name).map((r) => r.name));
  for (const [name, id] of Object.entries(previous)) {
    const prev = String(id ?? "").trim();
    if (!prev || taken.has(name)) continue;
    const row = inSet.get(prev);
    if (row && !row.name) {
      row.name = name;
      row.carried = true;
      taken.add(name);
      matched += 1;
    }
  }
}

// ── 5. Остаток добираем по порядку ──
const byContent = matched === stickers.length && matched === localNames.length;
if (!byContent) {
  console.warn(
    `\nпо содержимому опознано ${matched} из ${stickers.length} — остальные сопоставлены по порядку.`,
  );
  console.warn("проверьте отчёт ниже: порядок в наборе должен совпадать с MAPPING.md\n");
  const used = new Set(report.filter((r) => r.name).map((r) => r.name));
  const free = localNames.filter((n) => !used.has(n));
  for (const r of report) {
    if (!r.name) r.name = free.shift() ?? null;
  }
}

for (const r of report) {
  if (r.name) ids[r.name] = r.id;
}

for (const name of localNames) {
  if (!ids[name]) console.warn(`не найден в наборе: ${name}`);
}

writeFileSync(join(ROOT, "ids.json"), JSON.stringify(ids, null, 2) + "\n", "utf8");

console.log(
  `\n${"#".padEnd(4)}${"эмодзи".padEnd(8)}${"иконка".padEnd(20)}custom_emoji_id`,
);
for (const r of report) {
  const how = r.carried ? " (из прежнего ids.json)" : "";
  console.log(
    `${String(r.i + 1).padEnd(4)}${(r.emoji ?? "").padEnd(8)}${(r.name ?? "???").padEnd(20)}${r.id}${how}`,
  );
}
console.log(
  `\nids.json записан: ${Object.keys(ids).length} из ${localNames.length}` +
    (byContent ? " (сопоставление по содержимому — надёжно)" : " (сверьте порядок!)"),
);
