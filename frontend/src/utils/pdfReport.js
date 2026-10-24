import jsPDF from "jspdf";
import * as AutoTableModule from "jspdf-autotable";
import {
  rs, fmtDateTime, fmtDay, fmtDayLong, fmtMinutes, nightsOf,
  priceKind, PRICE_LABEL, modeOf,
} from "./format";

// Works with both the ESM and CommonJS builds of jspdf-autotable.
const autoTable = [
  AutoTableModule.autoTable,
  AutoTableModule.default,
  AutoTableModule.default && AutoTableModule.default.default,
  AutoTableModule.default && AutoTableModule.default.autoTable,
].find((fn) => typeof fn === "function");

const C = {
  ink: [23, 29, 47],
  brand: [107, 92, 255],
  brandSoft: [238, 236, 255],
  soft: [246, 247, 252],
  line: [226, 230, 240],
  muted: [104, 116, 138],
  good: [22, 128, 75],
  bad: [189, 46, 60],
  amber: [176, 108, 0],
  white: [255, 255, 255],
};

// jsPDF's built-in fonts only cover Latin-1; replace symbols and drop the rest.
function T(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/₹/g, "Rs. ")
    .replace(/[→➜➔]/g, " to ")
    .replace(/[—–]/g, "-")
    .replace(/≈/g, "~")
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[^\x20-\x7E\u00A0-\u00FF]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const arr = (v) => (Array.isArray(v) ? v : []);

export function downloadPlanPdf(plan) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();
  const M = 14;
  const BOTTOM = 18;
  let y = 0;

  const ensure = (h) => {
    if (y + h > H - BOTTOM) {
      doc.addPage();
      y = 16;
    }
  };

  const text = (str, x, yy, { size = 9, bold = false, color = C.ink, align = "left", maxWidth } = {}) => {
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.setFontSize(size);
    doc.setTextColor(...color);
    doc.text(T(str), x, yy, { align, maxWidth });
  };

  const section = (title, subtitle) => {
    ensure(20);
    doc.setFillColor(...C.brand);
    doc.roundedRect(M, y, 1.8, 7, 0.9, 0.9, "F");
    text(title, M + 5, y + 5.4, { size: 13, bold: true });
    y += 9;
    if (subtitle) {
      text(subtitle, M + 5, y + 1.5, { size: 8, color: C.muted, maxWidth: W - 2 * M - 5 });
      y += 6;
    }
    y += 1;
  };

  const clean = (cell) => {
    if (cell && typeof cell === "object" && !Array.isArray(cell) && "content" in cell) {
      return { ...cell, content: T(cell.content).replace(/ ?\n ?/g, "\n") };
    }
    return typeof cell === "string" ? cell : cell;
  };
  // T() collapses whitespace, so sanitise line-by-line to keep intentional line breaks.
  const cleanText = (cell) => {
    if (typeof cell === "string") return cell.split("\n").map(T).join("\n");
    return clean(cell);
  };

  const table = (opts) => {
    if (opts.head) opts = { ...opts, head: opts.head.map((row) => row.map(cleanText)) };
    if (opts.body) opts = { ...opts, body: opts.body.map((row) => row.map(cleanText)) };
    autoTable(doc, {
      startY: y,
      margin: { left: M, right: M, top: 16, bottom: BOTTOM },
      theme: "grid",
      styles: {
        font: "helvetica", fontSize: 8.2, cellPadding: 2.1, lineColor: C.line,
        lineWidth: 0.1, textColor: C.ink, valign: "middle", overflow: "linebreak",
      },
      headStyles: { fillColor: C.brand, textColor: C.white, fontStyle: "bold", halign: "left" },
      alternateRowStyles: { fillColor: C.soft },
      ...opts,
    });
    y = doc.lastAutoTable.finalY + 6;
  };

  const note = (str, color = C.muted) => {
    const lines = doc.splitTextToSize(T(str), W - 2 * M);
    ensure(lines.length * 4 + 2);
    doc.setFont("helvetica", "italic");
    doc.setFontSize(7.8);
    doc.setTextColor(...color);
    doc.text(lines, M, y);
    y += lines.length * 3.8 + 2;
  };

  // ------------------------------------------------------------------
  // Header band
  // ------------------------------------------------------------------
  doc.setFillColor(...C.ink);
  doc.rect(0, 0, W, 46, "F");
  doc.setFillColor(...C.brand);
  doc.rect(0, 46, W, 1.6, "F");

  text("TRIPGENIE", M, 13, { size: 9, bold: true, color: [176, 168, 255] });
  text("Your Travel Plan", M, 21, { size: 10, color: [200, 206, 224] });
  text(`${plan.source || ""}  to  ${plan.destination || ""}`, M, 33, { size: 21, bold: true, color: C.white, maxWidth: W - 2 * M });

  const dates = plan.departure_date
    ? `${fmtDayLong(plan.departure_date)}${plan.return_date ? "  -  " + fmtDayLong(plan.return_date) : ""}`
    : "Dates not set";
  text(dates, M, 41, { size: 9.5, color: [200, 206, 224] });
  y = 56;

  // ------------------------------------------------------------------
  // Summary tiles
  // ------------------------------------------------------------------
  const nights = nightsOf(plan);
  const tiles = [
    ["TRAVELLERS", String(plan.travelers ?? "-")],
    ["DURATION", `${plan.days} day${plan.days > 1 ? "s" : ""} / ${nights} night${nights === 1 ? "" : "s"}`],
    ["TOTAL BUDGET", rs(plan.total_budget)],
    ["ESTIMATED COST", rs(plan.total_estimated_cost)],
  ];
  const gap = 4;
  const tileW = (W - 2 * M - gap * 3) / 4;
  tiles.forEach(([label, value], i) => {
    const x = M + i * (tileW + gap);
    doc.setFillColor(...C.soft);
    doc.setDrawColor(...C.line);
    doc.roundedRect(x, y, tileW, 17, 2.5, 2.5, "FD");
    text(label, x + 3.5, y + 5.6, { size: 6.8, bold: true, color: C.muted });
    text(value, x + 3.5, y + 12.6, { size: 11, bold: true, maxWidth: tileW - 6 });
  });
  y += 23;

  // Budget bar
  const total = Number(plan.total_budget) || 0;
  const cost = Number(plan.total_estimated_cost);
  if (total > 0 && Number.isFinite(cost)) {
    const ratio = Math.min(1, Math.max(0, cost / total));
    const over = cost > total;
    doc.setFillColor(...C.line);
    doc.roundedRect(M, y, W - 2 * M, 3.6, 1.8, 1.8, "F");
    doc.setFillColor(...(over ? C.bad : C.good));
    doc.roundedRect(M, y, Math.max(3.6, (W - 2 * M) * ratio), 3.6, 1.8, 1.8, "F");
    const remaining = Number(plan.remaining_budget);
    const label = over
      ? `Over budget by ${rs(Math.abs(remaining))}`
      : `${rs(Math.abs(remaining))} remaining of ${rs(total)}`;
    text(label, M, y + 9, { size: 8.5, bold: true, color: over ? C.bad : C.good });
    text(`${Math.round(ratio * 100)}% of budget used`, W - M, y + 9, { size: 8, color: C.muted, align: "right" });
    y += 16;
  }

  // ------------------------------------------------------------------
  // Transport
  // ------------------------------------------------------------------
  const options = arr(plan.transport_options);
  const flights = options.filter((o) => modeOf(o) === "flight");
  const trains = options.filter((o) => modeOf(o) === "train");
  const buses = options.filter((o) => modeOf(o) === "bus");

  if (flights.length) {
    section("Flights", "Round-trip fares with airline, flight number and real departure / arrival times.");
    flights.slice(0, 3).forEach((f, idx) => {
      ensure(30);
      const kind = priceKind(f);
      text(
        `Option ${idx + 1}:  ${rs(f.total_price)} total  (${rs(f.price_per_person)} per person)  -  ${PRICE_LABEL[kind]}`,
        M, y + 3, { size: 9, bold: true, color: kind === "live" ? C.good : C.amber },
      );
      y += 6;
      const legs = arr(f.legs);
      if (legs.length) {
        table({
          head: [["Leg", "Airline / Flight", "From", "Departs", "To", "Arrives", "Duration", "Stops"]],
          body: legs.map((l) => [
            l.direction === "return" ? "Return" : "Outbound",
            `${l.airline || "-"}\n${arr(l.flight_numbers).join(", ")}`,
            l.from_code || "-",
            fmtDateTime(l.departure_time),
            l.to_code || "-",
            fmtDateTime(l.arrival_time),
            l.duration_text || "-",
            l.stops ? `${l.stops} stop${l.stops > 1 ? "s" : ""}${arr(l.layover_airports).length ? " (" + l.layover_airports.join(", ") + ")" : ""}` : "Non-stop",
          ]),
          columnStyles: { 0: { cellWidth: 17 }, 2: { cellWidth: 14 }, 3: { cellWidth: 34 }, 4: { cellWidth: 12 }, 5: { cellWidth: 34 }, 6: { cellWidth: 19 } },
        });
      } else {
        table({
          head: [["Route", "Duration", "Provider"]],
          body: [[`${f.source_airport || "-"} to ${f.destination_airport || "-"}`, f.travel_time || "-", f.provider || "-"]],
        });
      }
      if (f.airport_note) note(f.airport_note);
    });
  }

  const groundTable = (items, title, subtitle) => {
    if (!items.length) return;
    section(title, subtitle);
    const rows = items
      .slice()
      .sort((a, b) => (a.direction === "return") - (b.direction === "return"))
      .map((t) => {
        const kind = priceKind(t);
        const fareLines = arr(t.class_fares).length
          ? arr(t.class_fares).map((c) => `${c.class}: ${rs(c.fare)}`).join("\n")
          : "";
        return [
          t.direction === "return" ? "Return" : "Outbound",
          `${t.operator || (modeOf(t) === "train" ? "Train" : "Bus")}${t.vehicle_number ? "\n#" + t.vehicle_number : ""}`,
          `${t.from_name || "-"}\n${t.departure_time ? fmtDateTime(t.departure_time) : "Time not available"}`,
          `${t.to_name || "-"}\n${t.arrival_time ? fmtDateTime(t.arrival_time) : "Time not available"}`,
          t.travel_time || fmtMinutes(t.duration_minutes) || "-",
          `${rs(t.price_per_person)}${fareLines ? "\n" + fareLines : ""}\n(${PRICE_LABEL[kind]})`,
        ];
      });
    table({
      head: [["Leg", "Operator", "From / Departs", "To / Arrives", "Duration", "Fare per person"]],
      body: rows,
      columnStyles: { 0: { cellWidth: 17 }, 4: { cellWidth: 22 }, 5: { cellWidth: 36 } },
    });
    if (items.some((t) => priceKind(t) === "estimate")) {
      note("Fares marked 'Estimate' are distance-based approximations, not live quotes. Check the final fare on the official booking site.");
    }
  };

  groundTable(trains, "Trains", "Stations, clock times and fare per person.");
  groundTable(buses, "Buses", "Pick-up / drop points, times and fare per person.");

  arr(plan.transport_notes).forEach((n) => note(n, C.amber));

  // ------------------------------------------------------------------
  // Hotels
  // ------------------------------------------------------------------
  const hotels = arr(plan.hotels);
  if (hotels.length) {
    section("Hotels", `${nights} night${nights === 1 ? "" : "s"} - price shown per room per night.`);
    table({
      head: [["Hotel", "Rating", "Per room / night", "Stay", "Total", "Price type"]],
      body: hotels.slice(0, 8).map((h) => [
        `${h.hotel_name || "Hotel"}${h.address ? "\n" + String(h.address).slice(0, 70) : ""}`,
        h.rating ? `${h.rating}${h.user_rating_count ? " (" + h.user_rating_count + ")" : ""}` : "-",
        rs(h.price_per_room_night ?? h.price_per_night),
        `${h.nights ?? nights} night(s) x ${h.rooms ?? 1} room(s)`,
        h.total_price !== null && h.total_price !== undefined ? rs(h.total_price) : "-",
        PRICE_LABEL[priceKind(h)] || "Estimate",
      ]),
      columnStyles: { 0: { cellWidth: 56 }, 1: { cellWidth: 20 }, 3: { cellWidth: 28 } },
    });
    if (hotels.some((h) => priceKind(h) !== "live")) {
      note("Hotel prices that are not 'Live fare' are indicative or estimated. Confirm the real nightly rate before booking.");
    }
  }

  // ------------------------------------------------------------------
  // Budget
  // ------------------------------------------------------------------
  const b = plan.budget_breakdown;
  if (b) {
    section("Budget Breakdown");
    const kindText = (v) => (v ? " (estimate)" : "");
    table({
      head: [["Item", "Details", "Amount"]],
      body: [
        ["Transport", b.missing_transport_price ? "No usable fare found" : `Cheapest complete option${kindText(b.transport_is_estimate)}`, b.missing_transport_price ? "Not included" : rs(b.transport)],
        ["Hotel", `${b.hotel_nights} night(s) x ${b.hotel_rooms} room(s)${b.hotel_name ? " - " + b.hotel_name : ""}${b.hotel_price_type && b.hotel_price_type !== "live" ? " (estimate)" : ""}`, rs(b.hotel)],
        ["Food", "Rs. 800 per person per day", rs(b.food_estimate)],
        ["Local transport", "Rs. 500 per person per day", rs(b.local_transport_estimate)],
        [{ content: "Estimated total", styles: { fontStyle: "bold" } }, "", { content: rs(plan.total_estimated_cost), styles: { fontStyle: "bold" } }],
      ],
      columnStyles: { 2: { halign: "right", cellWidth: 34 } },
    });
    arr(b.notes).slice(0, 5).forEach((n) => note("- " + n));
  }

  // ------------------------------------------------------------------
  // Places
  // ------------------------------------------------------------------
  const places = arr(plan.places);
  if (places.length) {
    section("Places to Visit");
    table({
      head: [["Place", "Rating", "Address"]],
      body: places.slice(0, 10).map((p) => [
        p.place_name || "Attraction",
        p.rating ? `${p.rating} (${p.user_rating_count || 0})` : "-",
        String(p.address || "").slice(0, 90),
      ]),
      columnStyles: { 1: { cellWidth: 24 } },
    });
  }

  // ------------------------------------------------------------------
  // Itinerary
  // ------------------------------------------------------------------
  const itinerary = arr(plan.itinerary);
  if (itinerary.length) {
    section("Day-wise Itinerary");
    table({
      head: [["Day", "Plan"]],
      body: itinerary.map((d) => [
        `Day ${d.day_number}${d.date ? "\n" + fmtDay(d.date) : ""}`,
        arr(d.activities).map((a) => "- " + a).join("\n"),
      ]),
      columnStyles: { 0: { cellWidth: 28, fontStyle: "bold" } },
    });
  }

  // ------------------------------------------------------------------
  // Footer on every page
  // ------------------------------------------------------------------
  const pages = doc.getNumberOfPages();
  for (let i = 1; i <= pages; i++) {
    doc.setPage(i);
    doc.setDrawColor(...C.line);
    doc.setLineWidth(0.2);
    doc.line(M, H - 13, W - M, H - 13);
    text("Generated by TripGenie. Planning tool only - no tickets or rooms are booked. Verify prices before travel.", M, H - 8, { size: 7, color: C.muted });
    text(`Page ${i} of ${pages}`, W - M, H - 8, { size: 7.5, color: C.muted, align: "right" });
  }

  const safeName = T(`${plan.source || "trip"}-${plan.destination || ""}`).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  doc.save(`tripgenie-${safeName || "plan"}.pdf`);
}

export default downloadPlanPdf;
