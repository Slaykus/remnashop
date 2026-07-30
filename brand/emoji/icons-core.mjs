// Rain VPN — брендовое ядро пака.
//
// Все 14 иконок собраны из одного словаря примитивов: капля (единица),
// облако (сервис), дуга (защита), кольцо (цикл), струя (поток), узел (точка).
// Заимствованных символов здесь нет — алмаз, речевое облачко и телефон
// заменены брендовыми конструкциями.
//
// Тон сдержанный: неглубокие амплитуды, медленные нарастания вместо вспышек,
// палитра ограничена облачно-синим рядом; золото — только на «Подключиться».

import { DEFS, bob, g, glow, pulse, rim, shade, spec, wave } from "./style.mjs";
import { CLOUD, cloudBody, dome, drop, dropAt } from "./primitives.mjs";

export const ICONS_CORE = {
  // ── 1. Подключиться: разряд из облака пробивает купол, и тот загорается ──
  connect: {
    title: "Подключиться",
    fallback: "⚡",
    concept: "разряд из облака пробивает защитный купол — момент соединения",
    render: (t) => {
      const strike = pulse(t); // медленное нарастание вместо вспышки
      return `
        ${glow("gold", 50, 44, 42, 0.16 + strike * 0.28)}
        ${g(bob(t, 0.9), cloudBody("url(#g-cloud)", -18, 0.78))}
        <g opacity="${(0.78 + strike * 0.22).toFixed(3)}">
          <path d="M55 38 L38 62 H49 L45 80 L64 56 H52 Z" fill="url(#g-gold)"/>
          ${rim("M54 41 L41 58", 0.3 + strike * 0.35, 2.2)}
        </g>
        <g opacity="${(0.55 + strike * 0.45).toFixed(3)}">
          ${dropAt(50, 88, 0.78, "cyan")}
        </g>`;
    },
  },

  // ── 2. Подписка: капля со счётчиком срока внутри ──
  subscription: {
    title: "Подписка",
    fallback: "💎",
    concept: "капля, внутри кольцо-счётчик срока — период, а не драгоценность",
    render: (t) => {
      const rot = t * 360;
      const C = 2 * Math.PI * 15;
      const ticks = Array.from({ length: 12 }, (_, i) => {
        const a = (i / 12) * Math.PI * 2 - Math.PI / 2;
        const r1 = 19.5, r2 = 22.5;
        return `<line x1="${(50 + Math.cos(a) * r1).toFixed(2)}" y1="${(54 + Math.sin(a) * r1).toFixed(2)}"
                 x2="${(50 + Math.cos(a) * r2).toFixed(2)}" y2="${(54 + Math.sin(a) * r2).toFixed(2)}"
                 stroke="#1B54AB" stroke-opacity="0.5" stroke-width="2.2" stroke-linecap="round"/>`;
      }).join("");
      return `
        ${glow("blue", 50, 52, 44, 0.28)}
        ${g(
          bob(t, 0.9),
          `
          ${shade(`<path d="${drop(3.05)}" transform="translate(50 54)"/>`, 5, 0.45)}
          <g transform="translate(50 54)"><path d="${drop(3.05)}" fill="url(#g-blue)"/></g>
          ${spec(40, 34, 9, 6, 0.6, -25)}
          ${ticks}
          <circle cx="50" cy="54" r="15" fill="none" stroke="#0F3B7A" stroke-opacity="0.35" stroke-width="4"/>
          <g transform="rotate(${rot.toFixed(2)} 50 54)">
            <circle cx="50" cy="54" r="15" fill="none" stroke="#FFFFFF" stroke-opacity="0.92"
                    stroke-width="4" stroke-linecap="round"
                    stroke-dasharray="${(C * 0.68).toFixed(2)} ${C.toFixed(2)}"/>
          </g>`,
        )}`;
    },
  },

  // ── 3. Пробный период: контурная капля, налитая лишь частично ──
  trial: {
    title: "Пробный период",
    fallback: "🌧️",
    concept: "капля-контур, заполненная снизу — доступ начат, но не полный",
    render: (t) => {
      const level = 62 + wave(t) * 3.5; // уровень мягко дышит
      return `
        ${glow("cyan", 50, 52, 42, 0.24)}
        ${g(
          bob(t, 0.9),
          `
          <clipPath id="cl-trial"><path d="${drop(3.1)}" transform="translate(50 55)"/></clipPath>
          <g clip-path="url(#cl-trial)">
            <rect x="10" y="${level.toFixed(2)}" width="80" height="60" fill="url(#g-cyan)"/>
            <ellipse cx="50" cy="${level.toFixed(2)}" rx="26" ry="3.2" fill="#B4F0FF" opacity="0.85"/>
          </g>
          <g transform="translate(50 55)">
            <path d="${drop(3.1)}" fill="none" stroke="#8DCCFF" stroke-opacity="0.9"
                  stroke-width="3.4" stroke-linecap="round"
                  stroke-dasharray="9 7" stroke-dashoffset="${(-t * 32).toFixed(2)}"/>
          </g>
          ${spec(41, 40, 7, 5, 0.5, -25)}`,
        )}`;
    },
  },

  // ── 4. Мои устройства: капли разного размера на общей дуге ──
  devices: {
    title: "Мои устройства",
    fallback: "📱",
    concept: "три капли на общей дуге — устройства под одной подпиской",
    render: (t) => `
      ${glow("blue", 50, 52, 42, 0.24)}
      ${dome(50, 78, 36, "#3B82E8", 5, 0.85)}
      ${dropAt(24, 62 + wave(t, 0.0) * 1.6, 1.05, "cyan")}
      ${dropAt(50, 50 + wave(t, 0.33) * 1.6, 1.45, "blue")}
      ${dropAt(76, 62 + wave(t, 0.66) * 1.6, 1.05, "cyan")}`,
  },

  // ── 5. Пригласить друга: капля делится надвое — рост сети ──
  invite: {
    title: "Пригласить друга",
    fallback: "👥",
    concept: "капля разделяется на две — приглашённый становится своей единицей",
    render: (t) => {
      const k = pulse(t);
      const spread = 15 + k * 6;
      const L = (50 - spread).toFixed(1);
      const R = (50 + spread).toFixed(1);
      // Перемычки рисуются заливкой, а не тонкой линией: только так на 20px
      // видно, что капля именно делится, а не что рядом лежат три капли.
      const neck = `<path d="M42 30 C42 48 ${L} 44 ${L} 62 L${R} 62 C${R} 44 58 48 58 30 Z"
                      fill="url(#g-blue)" opacity="${(0.9 - k * 0.35).toFixed(2)}"/>`;
      return `
        ${glow("blue", 50, 52, 44, 0.26)}
        ${g(
          bob(t, 0.7),
          `
          ${neck}
          ${dropAt(50, 28, 1.35, "cloud")}
          ${dropAt(50 - spread, 66, 1.45, "blue")}
          ${dropAt(50 + spread, 66, 1.45, "cyan")}`,
        )}`;
    },
  },

  // ── 6. Поддержка: капля как речевая форма с дугой-вопросом ──
  support: {
    title: "Поддержка",
    fallback: "💬",
    concept: "капля, развёрнутая хвостом вниз-влево — реплика; внутри знак вопроса",
    render: (t) => {
      const p = pulse(t);
      return `
        ${glow("blue", 50, 48, 44, 0.24 + p * 0.14)}
        ${g(
          bob(t, 1.0),
          `
          ${shade(`<g transform="translate(52 46) rotate(215)"><path d="${drop(3.3)}"/></g>`, 5, 0.45)}
          <g transform="translate(52 46) rotate(215)">
            <path d="${drop(3.3)}" fill="url(#g-blue)"/>
          </g>
          ${spec(40, 34, 12, 7, 0.45, -20)}
          <path d="M44 40 A8.5 8.5 0 1 1 53 53 V57" fill="none" stroke="#FFFFFF"
                stroke-opacity="0.95" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="53" cy="68" r="4.4" fill="#FFFFFF" opacity="0.95"/>`,
        )}`;
    },
  },

  // ── 7. Личный кабинет: купол, сплетённый из дождевых струй ──
  "web-cabinet": {
    title: "Личный кабинет",
    fallback: "🌐",
    concept: "сфера, собранная из дождевых струй — сервис целиком",
    render: (t) => {
      const streaks = [-26, -13, 0, 13, 26]
        .map((dx, i) => {
          const h = 34 - Math.abs(dx) * 0.75;
          const o = 0.45 + pulse(t, i * 0.2) * 0.5;
          return `<path d="M${50 + dx} ${50 - h} V${50 + h}" stroke="#B4F0FF"
                   stroke-opacity="${o.toFixed(2)}" stroke-width="3" stroke-linecap="round"/>`;
        })
        .join("");
      return `
        ${glow("cyan", 50, 50, 44, 0.26)}
        ${g(
          bob(t, 0.7),
          `
          <circle cx="50" cy="50" r="35" fill="url(#g-blue)" opacity="0.9"/>
          <circle cx="50" cy="50" r="35" fill="none" stroke="#8DCCFF" stroke-opacity="0.8" stroke-width="3.5"/>
          <clipPath id="cl-web"><circle cx="50" cy="50" r="33"/></clipPath>
          <g clip-path="url(#cl-web)">${streaks}
            <ellipse cx="50" cy="50" rx="33" ry="13" fill="none" stroke="#E6EFFA"
                     stroke-opacity="0.55" stroke-width="2.6"/>
          </g>
          ${spec(38, 34, 13, 8, 0.4, -22)}`,
        )}`;
    },
  },

  // ── 8. Панель управления: облако и струи-регуляторы под ним ──
  dashboard: {
    title: "Панель управления",
    fallback: "🎛",
    concept: "облако с потоками разной длины — управление параметрами сервиса",
    render: (t) => {
      const lens = [30, 20, 25];
      const bars = lens
        .map((L, i) => {
          const y = 60 + i * 13;
          const w = L + wave(t, i * 0.3) * 4;
          return `<path d="M18 ${y} H${(18 + w).toFixed(1)}" stroke="#5FD3F5" stroke-opacity="0.9"
                    stroke-width="6" stroke-linecap="round"/>
                  ${dropAt(18 + w + 8, y, 0.62, "cloud")}`;
        })
        .join("");
      return `
        ${glow("blue", 50, 50, 44, 0.22)}
        ${cloudBody("url(#g-cloud)", -16, 0.7)}
        ${bars}`;
    },
  },

  // ── 9. Трафик: встречные потоки капель ──
  traffic: {
    title: "Трафик",
    fallback: "🌐",
    concept: "две встречные струи капель — исходящий и входящий поток",
    render: (t) => {
      // Остриё капли задаёт направление: вниз — входящий поток, вверх — исходящий.
      const col = (x, dir, ramp, phase) =>
        [0, 1, 2]
          .map((i) => {
            const k = (t + phase + i / 3) % 1;
            const y = dir > 0 ? 18 + k * 64 : 82 - k * 64;
            const o = Math.min(1, Math.sin(Math.PI * k) * 2.4);
            return `<g transform="rotate(${dir > 0 ? 180 : 0} ${x} ${y.toFixed(2)})">
                ${dropAt(x, y, 0.85, ramp, o)}
              </g>`;
          })
          .join("");
      return `
        ${glow("cyan", 50, 50, 44, 0.24)}
        ${col(33, 1, "blue", 0)}
        ${col(67, -1, "cyan", 0.5)}`;
    },
  },

  // ── 10. Тарифы: облака нарастающей плотности ──
  plan: {
    title: "Тарифы",
    fallback: "🗂",
    concept: "три облака нарастающей плотности — линейка тарифов",
    render: (t) => {
      // Три облака по общей базовой линии, растущие слева направо — линейка
      // тарифов. Серый исключён: тускнеет не цвет, а размер и насыщенность.
      const tier = (cx, cy, s, fill, o, phase) => `
        <g transform="translate(${cx - 50 * s} ${cy + wave(t, phase) * 0.9}) scale(${s})" opacity="${o}">
          ${shade(`<path d="${CLOUD}"/>`, 5, 0.35)}
          <path d="${CLOUD}" fill="${fill}"/>
          ${rim("M34 40 A19 19 0 0 1 65 33", 0.5)}
        </g>`;
      return `
        ${glow("blue", 52, 52, 44, 0.22)}
        ${tier(20, 38, 0.42, "url(#g-cloud)", 1, 0)}
        ${tier(50, 24, 0.6, "url(#g-cyan)", 1, 0.3)}
        ${tier(80, 6, 0.8, "url(#g-blue)", 1, 0.6)}`;
    },
  },

  // ── 11. Баллы: капли, собранные в чашу ──
  points: {
    title: "Баллы",
    fallback: "⭐",
    concept: "капли, накопленные в чаше — баланс баллов",
    render: (t) => {
      const k = (t * 1) % 1;
      const fallY = 16 + k * 34;
      const fo = Math.min(1, Math.sin(Math.PI * k) * 2.4);
      return `
        ${glow("cyan", 50, 58, 42, 0.24)}
        ${dropAt(50, fallY, 0.8, "cloud", fo)}
        <path d="M18 58 A32 32 0 0 0 82 58 Z" fill="url(#g-blue)"/>
        <path d="M18 58 H82" stroke="#B4F0FF" stroke-opacity="0.85" stroke-width="3.4" stroke-linecap="round"/>
        ${dropAt(38, 68, 0.72, "cyan")}
        ${dropAt(56, 66, 0.85, "cyan")}
        ${dropAt(48, 78, 0.62, "cloud", 0.85)}`;
    },
  },

  // ── 12. Продлить: водный цикл — капля идёт по кольцу и выпадает снова ──
  renew: {
    title: "Продлить",
    fallback: "🔁",
    concept: "круговорот воды: капля испаряется и выпадает вновь — возобновление",
    render: (t) => {
      const a = t * Math.PI * 2 - Math.PI / 2;
      const R = 27;
      const x = 50 + Math.cos(a) * R;
      const y = 52 + Math.sin(a) * R;
      // Капля бледнеет в верхней части круга — «испаряется», и вновь наливается внизу.
      const o = 0.35 + 0.65 * ((Math.sin(a) + 1) / 2);
      return `
        ${glow("cyan", 50, 52, 44, 0.24)}
        <circle cx="50" cy="52" r="${R}" fill="none" stroke="#1B54AB" stroke-opacity="0.4" stroke-width="5"/>
        <circle cx="50" cy="52" r="${R}" fill="none" stroke="#5FD3F5" stroke-opacity="0.85"
                stroke-width="5" stroke-linecap="round"
                stroke-dasharray="${(2 * Math.PI * R * 0.3).toFixed(1)} ${(2 * Math.PI * R).toFixed(1)}"
                transform="rotate(${(t * 360).toFixed(1)} 50 52)"/>
        ${cloudBody("url(#g-cloud)", -18, 0.46)}
        ${dropAt(x, y, 1.05, "cyan", o)}`;
    },
  },

  // ── 13. Защита: купол над каплями ──
  shield: {
    title: "Защита",
    fallback: "🛡",
    concept: "купол, принимающий на себя дождь — трафик под защитой",
    render: (t) => {
      const p = pulse(t);
      return `
        ${glow("blue", 50, 52, 44, 0.22 + p * 0.16)}
        ${dropAt(26, 22 + wave(t, 0.1) * 2, 0.7, "cloud", 0.75)}
        ${dropAt(50, 16 + wave(t, 0.45) * 2, 0.7, "cloud", 0.75)}
        ${dropAt(74, 22 + wave(t, 0.8) * 2, 0.7, "cloud", 0.75)}
        ${shade(`<path d="M14 62 A36 36 0 0 1 86 62 Z"/>`, 5, 0.4)}
        <path d="M14 62 A36 36 0 0 1 86 62 Z" fill="url(#g-blue)"/>
        ${dome(50, 62, 36, "#B4F0FF", 4, 0.55 + p * 0.3)}
        ${spec(38, 46, 14, 7, 0.4, -20)}
        <path d="M50 66 V86" stroke="#3B82E8" stroke-width="6" stroke-linecap="round"/>`;
    },
  },

  // ── 14. Бренд-марка: облако с дождём ──
  logo: {
    title: "Rain VPN",
    fallback: "🌧",
    concept: "фирменная марка: облако и три капли",
    render: (t) => {
      const rain = (x, y0, phase) => {
        const k = (t + phase) % 1;
        const o = Math.min(1, Math.sin(Math.PI * k) * 2.2);
        return dropAt(x, y0 + k * 24, 0.66, "cyan", o);
      };
      return `
        ${glow("cyan", 50, 46, 44, 0.26)}
        ${g(bob(t, 0.8), cloudBody("url(#g-cloud)", -14, 0.9))}
        ${rain(30, 60, 0)}
        ${rain(50, 64, 0.36)}
        ${rain(70, 60, 0.68)}`;
    },
  },
};

export const wrapFrame = (body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">${DEFS}${body}</svg>`;
