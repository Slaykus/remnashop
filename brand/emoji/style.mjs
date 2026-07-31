// Общий стилевой слой премиум-пака Rain VPN.
//
// Отличие от первой версии: вместо двух плоских заливок каждая форма получает
// градиентную рампу, тёмную подложку-тень, верхний блик и цветное свечение.
// Именно этот набор и читается как «объёмная» иконка, а не как плоский глиф.

export const TAU = Math.PI * 2;

// Все анимации периодичны по t из [0,1) — иначе петля даст рывок на стыке.
export const wave = (t, phase = 0) => Math.sin((t + phase) * TAU);
export const pulse = (t, phase = 0) => (wave(t, phase) + 1) / 2; // 0..1

// Короткая вспышка раз за цикл: узкий гауссов горб вокруг фазы `at`.
export const flash = (t, at = 0, width = 0.12) => {
  let d = Math.abs(((t - at + 0.5) % 1) - 0.5);
  return Math.exp(-((d / width) ** 2));
};

export const RAMPS = {
  blue: ["#8DCCFF", "#3B82E8", "#1B54AB"],
  cyan: ["#B4F0FF", "#5FD3F5", "#249FCE"],
  cloud: ["#FFFFFF", "#E6EFFA", "#C2D4E9"],
  gold: ["#FFE79B", "#F7BA45", "#CE8A1C"],
  green: ["#9CF3CC", "#3FD48A", "#1B9C60"],
  red: ["#FFB3AA", "#F2685E", "#BE3227"],
  violet: ["#D3C1FF", "#9B7BF5", "#6244CE"],
  slate: ["#7E9AC0", "#41618C", "#263C5C"],
};

export const GLOW = {
  blue: "#4C9AE8",
  cyan: "#6FD3F0",
  gold: "#F5C451",
  green: "#3FD48A",
  red: "#F2685E",
  violet: "#9B7BF5",
  cloud: "#BFD9F5",
};

const SHADOW = "#08121F";

// Градиент направлен по диагонали: свет сверху-слева, уплотнение снизу-справа.
// Так формы читаются объёмными даже без обводки.
const rampDefs = Object.entries(RAMPS)
  .map(
    ([name, [a, b, c]]) => `
    <linearGradient id="g-${name}" x1="0.15" y1="0" x2="0.85" y2="1">
      <stop offset="0" stop-color="${a}"/>
      <stop offset="0.52" stop-color="${b}"/>
      <stop offset="1" stop-color="${c}"/>
    </linearGradient>`,
  )
  .join("");

const glowDefs = Object.entries(GLOW)
  .map(
    ([name, c]) => `
    <radialGradient id="glow-${name}">
      <stop offset="0" stop-color="${c}" stop-opacity="0.55"/>
      <stop offset="0.55" stop-color="${c}" stop-opacity="0.18"/>
      <stop offset="1" stop-color="${c}" stop-opacity="0"/>
    </radialGradient>`,
  )
  .join("");

export const DEFS = `<defs>
  ${rampDefs}
  ${glowDefs}
  <radialGradient id="spec">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.85"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>
    <stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.55"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
  </linearGradient>
  <filter id="soft" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="3.2"/>
  </filter>
  <filter id="softer" x="-80%" y="-80%" width="260%" height="260%">
    <feGaussianBlur stdDeviation="6"/>
  </filter>
</defs>`;

/** Тёмная размытая подложка под формой — «сажает» иконку на плоскость. */
export const shade = (body, dy = 5, opacity = 0.45) =>
  `<g transform="translate(0 ${dy})" opacity="${opacity}" filter="url(#soft)"
      fill="${SHADOW}" stroke="none">${body}</g>`;

/**
 * Тёмный ореол под глифом.
 *
 * Раньше здесь было цветное свечение — оно смотрелось на тёмном фоне превью,
 * но эмодзи живёт на цветной кнопке, где свечение не читается и лишь съедает
 * поле канвы. Тёмный ореол, наоборот, отделяет иконку от любого фона:
 * и от синей кнопки, и от зелёной, и от светлой темы клиента.
 *
 * Сигнатура сохранена, чтобы не править три десятка мест вызова; имя цвета
 * теперь игнорируется.
 */
export const glow = (_name, cx = 50, cy = 50, r = 46, opacity = 1) =>
  `<circle cx="${cx}" cy="${cy}" r="${(r * 0.82).toFixed(1)}" fill="${SHADOW}"
     opacity="${Math.min(0.5, opacity * 0.45).toFixed(3)}" filter="url(#softer)"/>`;

/**
 * Светлая обводка силуэта — главный приём читаемости на цветной кнопке.
 * Рекомендация самих требований Telegram к стикерам: прозрачный фон,
 * белая обводка, тёмная тень.
 */
export const outline = (d, w = 3.2, opacity = 0.92) =>
  `<path d="${d}" fill="none" stroke="#FFFFFF" stroke-opacity="${opacity}"
     stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"/>`;

/** Верхний блик. Ставится поверх заливки, повторяя её верхнюю кромку. */
export const spec = (cx, cy, rx, ry, opacity = 1, rotate = 0) =>
  `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="url(#spec)"
     opacity="${opacity.toFixed(3)}" transform="rotate(${rotate} ${cx} ${cy})"/>`;

/** Тонкая светлая кромка сверху — имитация отражённого света. */
export const rim = (d, opacity = 0.5, w = 2.2) =>
  `<path d="${d}" fill="none" stroke="#FFFFFF" stroke-opacity="${opacity}"
     stroke-width="${w}" stroke-linecap="round"/>`;

export const g = (transform, body, extra = "") =>
  `<g transform="${transform}" ${extra}>${body}</g>`;

/**
 * Покачивание глифа.
 *
 * Множитель здесь неслучаен. В кнопке эмодзи рендерится примерно в 20px, то
 * есть канва 100 сжимается в пять раз: амплитуда в один пиксель превращается
 * в 0.2 и физически незаметна. Читается только крупное движение — поэтому
 * заданная амплитуда усиливается втрое.
 */
export const BOB_GAIN = 3.2;
export const bob = (t, amp = 1.6, phase = 0) =>
  `translate(0 ${(wave(t, phase) * amp * BOB_GAIN).toFixed(3)})`;
