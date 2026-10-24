// Shared formatting helpers for the result page and the PDF.

export function inr(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" && /₹|\bINR\b/i.test(value)) return value;
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

// jsPDF's built-in fonts have no ₹ glyph, so the PDF uses "Rs."
export function rs(value) {
  const text = inr(value);
  return text.replace("₹", "Rs. ");
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// Parse "2026-11-05T06:10:00" as a *local clock time* (no timezone shifting).
export function parseLocal(iso) {
  const m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (!m) return null;
  return { y: +m[1], mo: +m[2], d: +m[3], hh: m[4] !== undefined ? +m[4] : null, mm: m[5] !== undefined ? +m[5] : null };
}

export function fmtTime(iso) {
  const p = parseLocal(iso);
  if (!p || p.hh === null) return "—";
  const h12 = p.hh % 12 === 0 ? 12 : p.hh % 12;
  return `${h12}:${String(p.mm).padStart(2, "0")} ${p.hh >= 12 ? "PM" : "AM"}`;
}

export function fmtDay(iso) {
  const p = parseLocal(iso);
  if (!p) return "";
  const wd = WEEKDAYS[new Date(p.y, p.mo - 1, p.d).getDay()];
  return `${wd}, ${p.d} ${MONTHS[p.mo - 1]}`;
}

export function fmtDayLong(iso) {
  const p = parseLocal(iso);
  if (!p) return "";
  return `${fmtDay(iso)} ${p.y}`;
}

export function fmtDateTime(iso) {
  if (!parseLocal(iso)) return "—";
  return `${fmtDay(iso)} · ${fmtTime(iso)}`;
}

export function dayOffset(depIso, arrIso) {
  const a = parseLocal(depIso);
  const b = parseLocal(arrIso);
  if (!a || !b) return 0;
  const da = Date.UTC(a.y, a.mo - 1, a.d);
  const db = Date.UTC(b.y, b.mo - 1, b.d);
  return Math.round((db - da) / 86400000);
}

export function fmtMinutes(min) {
  const n = Number(min);
  if (!Number.isFinite(n) || n <= 0) return null;
  const h = Math.floor(n / 60);
  const m = Math.round(n % 60);
  if (h && m) return `${h} hr ${m} min`;
  if (h) return `${h} hr`;
  return `${m} min`;
}

// Normalises how trustworthy a price is, across every provider.
export function priceKind(item) {
  const t = item?.price_type;
  if (t === "live" || t === "google_range" || t === "estimate" || t === "indicative" || t === "unavailable") return t;
  const s = String(item?.price_status || "").toLowerCase();
  if (s === "verified") return "live";
  if (s) return "indicative";
  return Number.isFinite(Number(item?.total_price)) ? "indicative" : "unavailable";
}

export const PRICE_LABEL = {
  live: "Live fare",
  google_range: "Google price range",
  estimate: "Estimate",
  indicative: "Indicative quote",
  unavailable: "Price unavailable",
};

export function nightsOf(plan) {
  const a = parseLocal(plan?.departure_date);
  const b = parseLocal(plan?.return_date);
  if (a && b) {
    const n = Math.round((Date.UTC(b.y, b.mo - 1, b.d) - Date.UTC(a.y, a.mo - 1, a.d)) / 86400000);
    if (n >= 0) return n;
  }
  return Math.max(0, Number(plan?.days || 1) - 1);
}

export function modeOf(item) {
  const m = item?.mode || item?.transport_type;
  if (m === "flight" || m === "train" || m === "bus") return m;
  return m === "mixed_public_transit" || m === "public_transit" ? "train" : m || "other";
}
