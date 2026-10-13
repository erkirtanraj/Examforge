// Brand theme: maps Tailwind's blue (main) and cyan (accent) palettes to CSS variables.
const SHADES = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
const DEFAULTS = {
  blue: ["239 246 255", "219 234 254", "191 219 254", "147 197 253", "96 165 250", "59 130 246", "37 99 235", "29 78 216", "30 64 175", "30 58 138", "23 37 84"],
  cyan: ["236 254 255", "207 250 254", "165 243 252", "103 232 249", "34 211 238", "6 182 212", "8 145 178", "14 116 144", "21 94 117", "22 78 99", "8 51 68"],
};
export const DEFAULT_THEME = { preset: "ocean", primary: "#2563eb", accent: "#06b6d4" };
export const PRESETS = [
  { id: "ocean", name: "Ocean", primary: "#2563eb", accent: "#06b6d4" },
  { id: "emerald", name: "Emerald", primary: "#059669", accent: "#a3e635" },
  { id: "saffron", name: "Saffron", primary: "#ea580c", accent: "#facc15" },
  { id: "royal", name: "Royal", primary: "#7c3aed", accent: "#f472b6" },
  { id: "teal", name: "Teal", primary: "#0d9488", accent: "#38bdf8" },
  { id: "crimson", name: "Crimson", primary: "#be123c", accent: "#fb923c" },
];

const rgbToHsl = (r, g, b) => {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min, s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h / 6, s, l];
};
const hslToRgb = (h, s, l) => {
  if (!s) return [l, l, l].map((v) => Math.round(v * 255));
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const f = (t) => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; };
  return [f(h + 1 / 3), f(h), f(h - 1 / 3)].map((v) => Math.round(v * 255));
};
const hexRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

// Build an 11-shade scale whose anchor shade equals `hex`, following the default palette's lightness curve.
function scale(hex, palette, anchorShade) {
  const defL = DEFAULTS[palette].map((t) => rgbToHsl(...t.split(" ").map(Number))[2]);
  const a = SHADES.indexOf(anchorShade);
  const [h, s, l] = rgbToHsl(...hexRgb(hex));
  return SHADES.map((_, i) => {
    if (i === a) return hexRgb(hex).join(" ");
    const L = i < a
      ? l + ((defL[a] - defL[i]) / (defL[a] - 0.97)) * (0.97 - l)
      : l - ((defL[a] - defL[i]) / (defL[a] - 0.12)) * (l - 0.12);
    return hslToRgb(h, s, Math.min(0.98, Math.max(0.08, L))).join(" ");
  });
}

export function themeVars(theme) {
  const t = { ...DEFAULT_THEME, ...(theme || {}) };
  const blue = t.primary.toLowerCase() === DEFAULT_THEME.primary ? DEFAULTS.blue : scale(t.primary, "blue", 600);
  const cyan = t.accent.toLowerCase() === DEFAULT_THEME.accent ? DEFAULTS.cyan : scale(t.accent, "cyan", 500);
  const vars = {};
  SHADES.forEach((sh, i) => { vars[`--c-blue-${sh}`] = blue[i]; vars[`--c-cyan-${sh}`] = cyan[i]; });
  return vars;
}

export function applyTheme(theme) {
  const root = document.documentElement.style;
  Object.entries(themeVars(theme)).forEach(([k, v]) => root.setProperty(k, v));
}
