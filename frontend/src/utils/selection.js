// Turns the user's choices (travel mode, specific train/bus/flight, class, hotel)
// into a live budget. Used by the result page AND the PDF so both always agree.
import { modeOf, priceKind, nightsOf } from "./format";

const arr = (v) => (Array.isArray(v) ? v : []);
const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
export const MODES = ["flight", "train", "bus"];

export function groupTransport(plan) {
  const options = arr(plan?.transport_options);
  const g = { flight: [], train: { outbound: [], return: [] }, bus: { outbound: [], return: [] } };
  options.forEach((o) => {
    const m = modeOf(o);
    if (m === "flight") g.flight.push(o);
    else if (m === "train" || m === "bus") (o.direction === "return" ? g[m].return : g[m].outbound).push(o);
  });
  return g;
}

// Price of one option for the chosen class (SL / 3A / Non-AC ...)
export function priceOf(item, cls, travelers) {
  const t = Math.max(1, Number(travelers) || 1);
  const fares = arr(item?.class_fares).filter((f) => num(Number(f.fare)));
  if (fares.length) {
    const chosen = fares.find((f) => f.class === cls) || fares.reduce((a, b) => (Number(b.fare) < Number(a.fare) ? b : a));
    return { perPerson: Number(chosen.fare), total: Number(chosen.fare) * t, cls: chosen.class };
  }
  const per = num(item?.price_per_person);
  const total = num(item?.total_price) ?? (per !== null ? per * t : null);
  return { perPerson: per ?? (total !== null ? total / t : null), total, cls: null };
}

function bestIndex(list, travelers) {
  let best = 0;
  let bestTotal = Infinity;
  list.forEach((item, i) => {
    const p = priceOf(item, undefined, travelers).total;
    if (p !== null && p < bestTotal) {
      bestTotal = p;
      best = i;
    }
  });
  return best;
}

function pickItems(plan, g, mode, st) {
  const travelers = plan.travelers;
  const items = [];
  const choose = (list, key, direction) => {
    if (!list.length) return;
    const idx = Math.min(st.pick?.[key] ?? bestIndex(list, travelers), list.length - 1);
    const item = list[idx];
    const chosenCls = st.cls?.[`${key}:${idx}`];
    const price = priceOf(item, chosenCls, travelers);
    items.push({ item, key, idx, direction, mode, ...price, kind: priceKind(item) });
  };
  if (mode === "flight") choose(g.flight, "flight", "both");
  else {
    choose(g[mode].outbound, `${mode}:outbound`, "outbound");
    choose(g[mode].return, `${mode}:return`, "return");
  }
  return items;
}

export function resolveSelection(plan, st = {}) {
  const g = groupTransport(plan);
  const travelers = Number(plan.travelers) || 1;
  const modesAvailable = MODES.filter((m) => (m === "flight" ? g.flight.length : g[m].outbound.length + g[m].return.length) > 0);

  // cost of each mode with the current picks (for the "Travel by" chooser)
  const modeSummary = {};
  modesAvailable.forEach((m) => {
    const items = pickItems(plan, g, m, st);
    const totals = items.map((i) => i.total);
    modeSummary[m] = {
      total: totals.length && totals.every((t) => t !== null) ? totals.reduce((a, b) => a + b, 0) : null,
      items,
    };
  });

  let mode = st.mode && modesAvailable.includes(st.mode) ? st.mode : null;
  if (!mode) {
    const priced = modesAvailable.filter((m) => modeSummary[m].total !== null);
    mode = (priced.length ? priced : modesAvailable).sort((a, b) => (modeSummary[a].total ?? Infinity) - (modeSummary[b].total ?? Infinity))[0] || null;
  }
  const cheapestMode = modesAvailable.filter((m) => modeSummary[m].total !== null)
    .sort((a, b) => modeSummary[a].total - modeSummary[b].total)[0] || null;

  const items = mode ? modeSummary[mode].items : [];
  const pricedItems = items.filter((i) => i.total !== null);
  const transport = pricedItems.length ? pricedItems.reduce((s, i) => s + i.total, 0) : null;
  const returnMissing = mode && mode !== "flight" && !!plan.return_date && !items.some((i) => i.direction === "return");
  const transportIsEstimate = pricedItems.some((i) => i.kind !== "live");

  // ---- hotel ----
  const hotels = arr(plan.hotels);
  const nights = nightsOf(plan);
  const b = plan.budget_breakdown || {};
  let hotelIdx = st.hotel;
  if (hotelIdx === undefined || hotelIdx === null || hotelIdx >= hotels.length) {
    const byName = hotels.findIndex((h) => b.hotel_name && h.hotel_name === b.hotel_name);
    hotelIdx = byName >= 0 ? byName : hotels.length ? 0 : null;
  }
  const hotel = hotelIdx !== null ? hotels[hotelIdx] : null;
  const rooms = hotel?.rooms ?? b.hotel_rooms ?? Math.max(1, Math.ceil(travelers / 2));
  const perRoom = num(hotel?.price_per_room_night) ?? num(hotel?.price_per_night);
  const hotelTotal = hotel
    ? nights > 0 ? (num(hotel.total_price) ?? (perRoom !== null ? perRoom * rooms * nights : 0)) : 0
    : num(b.hotel) ?? 0;
  const hotelKind = hotel ? priceKind(hotel) : b.hotel_price_type || "estimate";

  const food = num(b.food_estimate) ?? 800 * travelers * plan.days;
  const local = num(b.local_transport_estimate) ?? 500 * travelers * plan.days;
  const total = (transport ?? 0) + hotelTotal + food + local;
  const remaining = (Number(plan.total_budget) || 0) - total;

  const notes = [];
  if (mode && transport !== null) {
    notes.push(`Transport = ${mode} ${items.length > 1 ? "(outbound + return)" : "(round trip)"} as selected${transportIsEstimate ? " — includes estimated/indicative fares" : ""}.`);
  } else notes.push("No priced transport option is selected, so transport is not included.");
  if (returnMissing) notes.push("No return option was found, so only the outbound fare is counted.");
  if (hotel) notes.push(`Hotel = ${hotel.hotel_name} for ${nights} night(s)${hotelKind !== "live" ? " — estimated price" : ""}.`);
  notes.push("Food ₹800 and local transport ₹500 per person per day. Entry fees and shopping are not included.");

  const budget_breakdown = {
    ...b,
    transport,
    transport_mode: mode,
    transport_is_estimate: transportIsEstimate,
    missing_transport_price: transport === null,
    return_missing: !!returnMissing,
    hotel: hotelTotal,
    hotel_name: hotel?.hotel_name ?? b.hotel_name,
    hotel_price_type: hotelKind,
    hotel_per_room_night: perRoom ?? b.hotel_per_room_night,
    hotel_nights: nights,
    hotel_rooms: rooms,
    food_estimate: food,
    local_transport_estimate: local,
    notes,
  };

  return {
    mode, modesAvailable, modeSummary, cheapestMode, items, hotelIdx, g,
    plan: {
      ...plan,
      total_estimated_cost: Math.round(total * 100) / 100,
      remaining_budget: Math.round(remaining * 100) / 100,
      budget_breakdown,
      selection: { mode, items, hotel },
    },
  };
}
