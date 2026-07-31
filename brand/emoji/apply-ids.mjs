// Подставляет id премиум-эмодзи в assets/translations/*/custom.ftl.
//
//   node apply-ids.mjs            # применить
//   node apply-ids.mjs --check    # только показать, что изменится
//
// Правит исключительно участок между маркерами `# >>> rain-emoji` и
// `# <<< rain-emoji`. Скрипт идемпотентен: повторный запуск заменяет ранее
// вставленные теги, а не наслаивает их. Иконки с пустым id пропускаются —
// такие ключи остаются на обычных Unicode-эмодзи.

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { ICONS } from "./pack.mjs";
import { MESSAGE_EMOJI } from "./wiring.mjs";

const ROOT = dirname(fileURLToPath(import.meta.url));
const REPO = join(ROOT, "..", "..");
const LOCALES = ["ru", "en"];

const CHECK = process.argv.includes("--check");

const START = "# >>> rain-emoji";
const END = "# <<< rain-emoji";

// Уже вставленный тег — снимаем его, чтобы прогон был идемпотентным.
const LEADING_TAG =
  /^(?:<e id="\d+">[^<]*<\/e>|<tg-emoji emoji-id="\d+">[^<]*<\/tg-emoji>)\s*/;

// Ведущий Unicode-эмодзи вместе с вариационными селекторами, ZWJ-связками
// и модификаторами тона кожи: 🤷‍♂️ — это один «эмодзи» из пяти кодпоинтов.
const LEADING_EMOJI =
  /^(?:\p{Extended_Pictographic}(?:️|‍\p{Extended_Pictographic}|[\u{1F3FB}-\u{1F3FF}])*|[\u{1F1E6}-\u{1F1FF}]{2})+\s*/u;

const idsPath = join(ROOT, "ids.json");
if (!existsSync(idsPath)) {
  console.error("ids.json не найден. Создайте его из ids.example.json.");
  process.exit(1);
}
const ids = JSON.parse(readFileSync(idsPath, "utf8"));

// ftl-ключ -> { id, fallback }
const byKey = new Map();
for (const [name, icon] of Object.entries(ICONS)) {
  const id = String(ids[name] ?? "").trim();
  if (!id) continue;
  if (!/^\d+$/.test(id)) {
    console.error(`ids.json: у «${name}» id не число — ${JSON.stringify(ids[name])}`);
    process.exit(1);
  }
  for (const key of icon.keys ?? []) {
    byKey.set(key, { id, fallback: icon.fallback, name });
  }
}

if (byKey.size === 0) {
  console.log("В ids.json ещё нет ни одного id — нечего подставлять.");
  process.exit(0);
}

let totalChanged = 0;
const missed = new Set(byKey.keys());

for (const locale of LOCALES) {
  const file = join(REPO, "assets", "translations", locale, "custom.ftl");
  if (!existsSync(file)) continue;

  const src = readFileSync(file, "utf8");
  const from = src.indexOf(START);
  const to = src.indexOf(END);
  if (from === -1 || to === -1 || to < from) {
    console.error(`${locale}/custom.ftl: маркеры rain-emoji не найдены — пропуск.`);
    continue;
  }

  const head = src.slice(0, from);
  const tail = src.slice(to);
  // Файлы локалей приходят с разными переводами строк (ru — LF, en — CRLF);
  // склейка своим EOL перепишет весь участок и замусорит диф.
  const eol = src.includes("\r\n") ? "\r\n" : "\n";
  const lines = src.slice(from, to).split(/\r?\n/);

  let current = null; // текущее top-level сообщение, для ключей вида a.b
  let changed = 0;

  const out = lines.map((line) => {
    const top = line.match(/^([A-Za-z][\w-]*)\s*=\s*(.*)$/);
    const attr = line.match(/^(\s+)\.([\w-]*)\s*=\s*(.*)$/);

    let key = null;
    let indent = "";
    let value = null;
    let prefix = "";

    if (top) {
      current = top[1];
      key = top[1];
      value = top[2];
      prefix = `${top[1]} = `;
    } else if (attr && current) {
      key = `${current}.${attr[2]}`;
      indent = attr[1];
      value = attr[3];
      prefix = `${indent}.${attr[2]} = `;
    } else {
      return line;
    }

    const hit = byKey.get(key);
    if (!hit) return line;
    missed.delete(key);

    // Значение переносится на следующие строки (мультистрочный селектор) —
    // ведущего эмодзи в этой строке нет, вставлять некуда.
    if (value.trim() === "") {
      console.warn(`  ${locale}: ${key} — многострочное значение, пропущено`);
      return line;
    }

    const stripped = value.replace(LEADING_TAG, "").replace(LEADING_EMOJI, "");
    const next = `${prefix}<e id="${hit.id}">${hit.fallback}</e> ${stripped}`;
    if (next !== line) changed += 1;
    return next;
  });

  if (changed && !CHECK) writeFileSync(file, head + out.join(eol) + tail, "utf8");
  console.log(`${locale}/custom.ftl: ${changed} ключ(ей)${CHECK ? " (проверка)" : ""}`);
  totalChanged += changed;
}

for (const key of missed) {
  console.warn(`не найден в custom.ftl: ${key}`);
}

// ── Тексты сообщений: правим встроенные файлы образа ──
// Здесь ключ уже известен, а эмодзи ищется по всему его блоку, а не только
// в начале строки: в сообщениях значки стоят внутри абзацев.
const idByIcon = new Map(Object.entries(ids).map(([n, v]) => [n, String(v).trim()]));

// Тег снимается перед подстановкой, поэтому повторный прогон не наслаивает.
const UNWRAP = /<e id="\d+">([^<]*)<\/e>|<tg-emoji emoji-id="\d+">([^<]*)<\/tg-emoji>/g;

let msgChanged = 0;
for (const locale of LOCALES) {
  for (const [fileName, keys] of Object.entries(MESSAGE_EMOJI)) {
    const file = join(REPO, "assets", "translations", locale, fileName);
    if (!existsSync(file)) continue;

    let src = readFileSync(file, "utf8");
    const eol = src.includes("\r\n") ? "\r\n" : "\n";
    const lines = src.split(/\r?\n/);

    let changedHere = 0;
    let current = null;
    let blockStart = -1;

    const blocks = [];
    lines.forEach((line, i) => {
      const m = line.match(/^(-?[A-Za-z][\w-]*)\s*=/);
      if (m) {
        if (current && keys[current]) blocks.push([current, blockStart, i]);
        current = m[1];
        blockStart = i;
      }
    });
    if (current && keys[current]) blocks.push([current, blockStart, lines.length]);

    // С конца: правка блока перезаписывает строки, и обход с начала сдвинул бы
    // индексы блоков, идущих следом.
    for (const [key, from, to] of blocks.reverse()) {
      let chunk = lines.slice(from, to).join(eol).replace(UNWRAP, (_, a, b) => a ?? b);
      for (const [emoji, icon] of keys[key]) {
        const id = idByIcon.get(icon);
        if (!id) continue;
        // Вариационный селектор U+FE0F может быть, а может и не быть.
        const bare = emoji.replace(/️/g, "");
        for (const variant of new Set([emoji, bare])) {
          if (!chunk.includes(variant)) continue;
          chunk = chunk.split(variant).join(`<e id="${id}">${emoji}</e>`);
          changedHere += 1;
          break;
        }
      }
      const rebuilt = chunk.split(eol);
      lines.splice(from, to - from, ...rebuilt);
    }

    if (changedHere && !CHECK) writeFileSync(file, lines.join(eol), "utf8");
    if (changedHere) {
      console.log(`${locale}/${fileName}: ${changedHere} значк(ов)${CHECK ? " (проверка)" : ""}`);
      msgChanged += changedHere;
    }
  }
}

console.log(
  `\n${CHECK ? "будет изменено" : "изменено"}: ` +
    `кнопок ${totalChanged}, значков в текстах ${msgChanged}`,
);
