import React, { useMemo, useState } from "react";
import {
  inr, fmtTime, fmtDay, fmtDayLong, fmtMinutes, dayOffset, nightsOf,
  priceKind, PRICE_LABEL, modeOf,
} from "../utils/format";
import { downloadPlanPdf } from "../utils/pdfReport";

const arr = (v) => (Array.isArray(v) ? v : []);

const MODE_META = {
  flight: { icon: "✈️", label: "Flights" },
  train: { icon: "🚆", label: "Trains" },
  bus: { icon: "🚌", label: "Buses" },
};

function PriceBadge({ item }) {
  const kind = priceKind(item);
  return <span className={`tg-badge tg-badge-${kind}`}>{PRICE_LABEL[kind]}</span>;
}

// departure ──── duration ──── arrival
function Timeline({ fromTime, fromPlace, fromSub, toTime, toPlace, toSub, middle, sub }) {
  const offset = dayOffset(fromTime, toTime);
  return (
    <div className="tg-timeline">
      <div className="tg-tl-end">
        <b className="tg-time">{fmtTime(fromTime)}</b>
        <span className="tg-place">{fromPlace || "—"}</span>
        {fromSub && <small>{fromSub}</small>}
      </div>
      <div className="tg-tl-mid">
        <span className="tg-duration">{middle || "—"}</span>
        <div className="tg-line"><i /></div>
        <small>{sub}</small>
      </div>
      <div className="tg-tl-end tg-tl-right">
        <b className="tg-time">
          {fmtTime(toTime)}
          {offset > 0 && <sup className="tg-plus">+{offset}</sup>}
        </b>
        <span className="tg-place">{toPlace || "—"}</span>
        {toSub && <small>{toSub}</small>}
      </div>
    </div>
  );
}

function FlightCard({ flight, index }) {
  const legs = arr(flight.legs);
  return (
    <article className="tg-trip-card">
      <header className="tg-trip-head">
        <div>
          <span className="tg-chip">Option {index + 1}</span>
          <h4>{legs[0]?.airline || flight.airline || "Flight"}{flight.provider ? <small> · via {flight.provider}</small> : null}</h4>
        </div>
        <div className="tg-price">
          <b>{inr(flight.total_price)}</b>
          <small>round trip · {inr(flight.price_per_person)} / person</small>
          <PriceBadge item={flight} />
        </div>
      </header>

      {legs.length > 0 ? (
        legs.map((leg) => (
          <div className="tg-leg" key={leg.direction}>
            <div className="tg-leg-title">
              <span>{leg.direction === "return" ? "↩ Return" : "Outbound ↗"}</span>
              <span>{fmtDay(leg.departure_time)}</span>
              <span className="tg-flightno">{arr(leg.flight_numbers).join(" · ")}</span>
            </div>
            <Timeline
              fromTime={leg.departure_time} fromPlace={leg.from_code}
              toTime={leg.arrival_time} toPlace={leg.to_code}
              middle={leg.duration_text}
              sub={leg.stops ? `${leg.stops} stop${leg.stops > 1 ? "s" : ""}${arr(leg.layover_airports).length ? " · " + leg.layover_airports.join(", ") : ""}` : "Non-stop"}
            />
          </div>
        ))
      ) : (
        <div className="tg-leg">
          <div className="tg-leg-title"><span>Route</span></div>
          <p className="tg-muted">
            {flight.source_airport || "—"} → {flight.destination_airport || "—"}
            {flight.travel_time ? ` · ${flight.travel_time}` : ""}
          </p>
          <p className="tg-muted tg-small">This provider did not return clock times for this fare.</p>
        </div>
      )}
      {flight.airport_note && <p className="tg-note">ℹ️ {flight.airport_note}</p>}
    </article>
  );
}

function GroundCard({ item }) {
  const mode = modeOf(item);
  const classFares = arr(item.class_fares);
  const noSchedule = !item.departure_time;
  const segments = arr(item.segments);
  return (
    <article className="tg-trip-card tg-ground">
      <header className="tg-trip-head">
        <div>
          <h4>
            {MODE_META[mode]?.icon} {item.operator || (mode === "train" ? "Train" : "Bus")}
            {item.vehicle_number && <span className="tg-flightno">#{item.vehicle_number}</span>}
          </h4>
          {item.changes > 0 && <small className="tg-muted">{item.changes} change{item.changes > 1 ? "s" : ""}</small>}
        </div>
        <div className="tg-price">
          <b>{inr(item.price_per_person)}<em> / person</em></b>
          <small>{inr(item.total_price)} total</small>
          <PriceBadge item={item} />
        </div>
      </header>

      {noSchedule ? (
        <div className="tg-noschedule">
          <b>≈ {item.travel_time?.replace("≈ ", "") || "—"}</b>
          <span>Timetable not available from the route provider. Check exact departure times on the official site below.</span>
        </div>
      ) : (
        <Timeline
          fromTime={item.departure_time} fromPlace={item.from_name} fromSub={fmtDay(item.departure_time)}
          toTime={item.arrival_time} toPlace={item.to_name} toSub={fmtDay(item.arrival_time)}
          middle={item.travel_time || fmtMinutes(item.duration_minutes)}
          sub={item.distance_km ? `${Math.round(item.distance_km)} km` : ""}
        />
      )}

      {segments.length > 1 && (
        <details className="tg-details">
          <summary>Route details ({segments.length} legs)</summary>
          {segments.map((s, i) => (
            <p key={i}>
              <b>{s.line_short || s.line_name || s.vehicle_type}</b> · {s.from_name} {fmtTime(s.departure_time)} → {s.to_name} {fmtTime(s.arrival_time)}
            </p>
          ))}
        </details>
      )}

      {classFares.length > 0 && (
        <div className="tg-fares">
          {classFares.map((c) => (
            <span key={c.class} className="tg-fare-chip">
              <b>{c.class}</b> {inr(c.fare)}
            </span>
          ))}
        </div>
      )}
      {item.price_source && <p className="tg-muted tg-small">Fare source: {item.price_source}</p>}
    </article>
  );
}

function HotelCard({ hotel, nights, isBudgetPick, photoUrl }) {
  const kind = priceKind(hotel);
  const perRoom = hotel.price_per_room_night ?? hotel.price_per_night;
  const img = hotel.image_url || (hotel.photo_names?.[0] ? photoUrl(hotel.photo_names[0], 700) : null);
  const link = hotel.booking_url || hotel.google_maps_url;
  return (
    <article className="tg-hotel">
      <div className="tg-hotel-img" style={img ? { backgroundImage: `url("${img}")` } : undefined}>
        {!img && <span>🏨</span>}
        {isBudgetPick && <em className="tg-pick">Used for budget</em>}
      </div>
      <div className="tg-hotel-body">
        <h4>{hotel.hotel_name}</h4>
        <p className="tg-hotel-meta">
          {hotel.rating ? <span className="tg-rating">⭐ {hotel.rating}</span> : null}
          {hotel.user_rating_count ? <span>{Number(hotel.user_rating_count).toLocaleString("en-IN")} reviews</span> : null}
          {hotel.hotel_class ? <span>{hotel.hotel_class}</span> : null}
        </p>
        {hotel.address && <p className="tg-muted tg-small tg-clamp">{hotel.address}</p>}
        <div className="tg-hotel-price">
          <div>
            <b>{inr(perRoom)}</b>
            <small> / room / night</small>
          </div>
          <span className={`tg-badge tg-badge-${kind}`}>{PRICE_LABEL[kind]}</span>
        </div>
        <p className="tg-muted tg-small">
          {hotel.total_price != null
            ? <>{hotel.nights ?? nights} night(s) × {hotel.rooms ?? 1} room(s) = <b>{inr(hotel.total_price)}</b></>
            : "Same-day trip — no stay needed"}
        </p>
        <div className="tg-links">
          {hotel.google_maps_url && <a href={hotel.google_maps_url} target="_blank" rel="noreferrer">🗺️ Map</a>}
          {link && link !== hotel.google_maps_url && <a href={link} target="_blank" rel="noreferrer">View / book ↗</a>}
        </div>
      </div>
    </article>
  );
}

export default function PlanResult({ plan }) {
  // Hooks must run before any early return.
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [photoIndex, setPhotoIndex] = useState(0);
  const [tab, setTab] = useState(null);

  const options = arr(plan?.transport_options);
  const grouped = useMemo(() => ({
    flight: options.filter((o) => modeOf(o) === "flight"),
    train: options.filter((o) => modeOf(o) === "train"),
    bus: options.filter((o) => modeOf(o) === "bus"),
  }), [options]);

  if (!plan) return null;

  const hotels = arr(plan.hotels);
  const places = arr(plan.places);
  const itinerary = arr(plan.itinerary);
  const b = plan.budget_breakdown;
  const nights = nightsOf(plan);

  const apiBase = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const photoUrl = (name, width = 1200) =>
    `${apiBase}/places/photo?photo_name=${encodeURIComponent(name)}&max_width=${width}`;

  const availableModes = ["flight", "train", "bus"].filter((m) => grouped[m].length > 0);
  const activeTab = availableModes.includes(tab) ? tab : availableModes[0];

  const total = Number(plan.total_budget) || 0;
  const cost = Number(plan.total_estimated_cost);
  const ratio = total > 0 && Number.isFinite(cost) ? Math.min(100, Math.max(0, (cost / total) * 100)) : 0;
  const remaining = plan.remaining_budget;
  const over = Number(remaining) < 0;

  const breakdownRows = b
    ? [
        { label: "Transport", note: b.missing_transport_price ? "no fare found" : b.transport_is_estimate ? "estimate" : "quoted", value: b.missing_transport_price ? null : b.transport, color: "#6b5cff" },
        { label: "Hotel", note: `${b.hotel_nights} night(s) · ${b.hotel_rooms} room(s)${b.hotel_price_type && b.hotel_price_type !== "live" ? " · estimate" : ""}`, value: b.hotel, color: "#14b8a6" },
        { label: "Food", note: "₹800 / person / day", value: b.food_estimate, color: "#f59e0b" },
        { label: "Local travel", note: "₹500 / person / day", value: b.local_transport_estimate, color: "#ec4899" },
      ]
    : [];
  const rowsTotal = breakdownRows.reduce((s, r) => s + (Number(r.value) || 0), 0) || 1;

  const links = plan.transport_search_links || {};

  const renderGround = (items) => {
    const out = items.filter((i) => i.direction !== "return");
    const back = items.filter((i) => i.direction === "return");
    return (
      <>
        {out.length > 0 && (
          <>
            <h5 className="tg-dir">Outbound · {fmtDayLong(plan.departure_date)}</h5>
            {out.map((it, i) => <GroundCard item={it} key={`o${i}`} />)}
          </>
        )}
        {back.length > 0 && (
          <>
            <h5 className="tg-dir">Return · {fmtDayLong(plan.return_date)}</h5>
            {back.map((it, i) => <GroundCard item={it} key={`r${i}`} />)}
          </>
        )}
      </>
    );
  };

  return (
    <div id="print-area" className="result tg-result">
      {/* ---------------- Hero ---------------- */}
      <section className="tg-hero">
        <div className="tg-hero-top">
          <span className="eyebrow tg-eyebrow">YOUR AI TRIP PLAN</span>
          <button className="tg-pdf-btn" onClick={() => downloadPlanPdf(plan)}>📄 Download PDF</button>
        </div>
        <div className="tg-route">
          <div>
            <small>FROM</small>
            <h2>{plan.source}</h2>
          </div>
          <div className="tg-route-line"><span>✈</span></div>
          <div className="tg-route-right">
            <small>TO</small>
            <h2>{plan.destination}</h2>
          </div>
        </div>
        <div className="tg-chips">
          {plan.departure_date && <span>📅 {fmtDay(plan.departure_date)}{plan.return_date ? ` → ${fmtDay(plan.return_date)}` : ""}</span>}
          <span>👥 {plan.travelers} traveller{plan.travelers > 1 ? "s" : ""}</span>
          <span>🌙 {plan.days} day{plan.days > 1 ? "s" : ""} / {nights} night{nights === 1 ? "" : "s"}</span>
          <span>💼 {inr(plan.budget_per_person)} per person</span>
        </div>
      </section>

      {/* ---------------- Budget ---------------- */}
      <section className="tg-card tg-budget">
        <div className="tg-budget-top">
          <div>
            <small className="tg-label">ESTIMATED TRIP COST</small>
            <h3>{inr(plan.total_estimated_cost)} <span>of {inr(plan.total_budget)}</span></h3>
          </div>
          {remaining !== null && remaining !== undefined && (
            <div className={`tg-remaining ${over ? "over" : "ok"}`}>
              {over ? `⚠️ ${inr(Math.abs(remaining))} over budget` : `✅ ${inr(remaining)} left`}
            </div>
          )}
        </div>
        <div className="tg-bar"><i className={over ? "over" : ""} style={{ width: `${ratio}%` }} /></div>

        {b && (
          <>
            <div className="tg-stack">
              {breakdownRows.map((r) => (
                <i key={r.label} style={{ width: `${((Number(r.value) || 0) / rowsTotal) * 100}%`, background: r.color }} />
              ))}
            </div>
            <div className="tg-break">
              {breakdownRows.map((r) => (
                <div key={r.label}>
                  <span><i style={{ background: r.color }} />{r.label}</span>
                  <b>{r.value === null ? "Not included" : inr(r.value)}</b>
                  <small>{r.note}</small>
                </div>
              ))}
            </div>
            {arr(b.notes).length > 0 && (
              <ul className="tg-notes">
                {arr(b.notes).map((n, i) => <li key={i}>{n}</li>)}
              </ul>
            )}
          </>
        )}
      </section>

      {/* ---------------- Transport ---------------- */}
      <section className="tg-card">
        <div className="tg-section-head">
          <h3>🧭 Transport</h3>
          {availableModes.length > 0 && (
            <div className="tg-tabs" role="tablist">
              {availableModes.map((m) => (
                <button key={m} role="tab" aria-selected={activeTab === m}
                  className={activeTab === m ? "active" : ""} onClick={() => setTab(m)}>
                  {MODE_META[m].icon} {MODE_META[m].label} <em>{grouped[m].length}</em>
                </button>
              ))}
            </div>
          )}
        </div>

        {availableModes.length === 0 ? (
          <div className="tg-empty">
            <b>No transport options were returned.</b>
            <p>Use the official search links below to compare fares and timings.</p>
          </div>
        ) : activeTab === "flight" ? (
          grouped.flight.slice(0, 6).map((f, i) => <FlightCard flight={f} index={i} key={i} />)
        ) : (
          renderGround(grouped[activeTab])
        )}

        {arr(plan.transport_notes).map((n, i) => <p className="tg-note" key={i}>ℹ️ {n}</p>)}

        <div className="tg-search-links">
          <a href={links.flight || "https://www.google.com/travel/flights"} target="_blank" rel="noreferrer">✈️ Compare flights ↗</a>
          <a href={links.train || "https://www.irctc.co.in/nget/train-search"} target="_blank" rel="noreferrer">🚆 IRCTC ↗</a>
          <a href={links.bus || "https://www.redbus.in/"} target="_blank" rel="noreferrer">🚌 redBus ↗</a>
        </div>
      </section>

      {/* ---------------- Hotels ---------------- */}
      <section className="tg-card">
        <div className="tg-section-head">
          <h3>🏨 Where to stay</h3>
          {links.hotel && <a className="tg-ghost" href={links.hotel} target="_blank" rel="noreferrer">Search all hotels ↗</a>}
        </div>
        {hotels.length === 0 ? (
          <div className="tg-empty"><b>No hotels returned.</b></div>
        ) : (
          <div className="tg-hotel-grid">
            {hotels.map((h, i) => (
              <HotelCard key={`${h.hotel_name}-${i}`} hotel={h} nights={nights} photoUrl={photoUrl}
                isBudgetPick={b?.hotel_name && b.hotel_name === h.hotel_name} />
            ))}
          </div>
        )}
        {hotels.some((h) => priceKind(h) !== "live") && (
          <p className="tg-note">ℹ️ Prices not marked “Live fare” are estimates or Google price ranges. Add a SERPAPI_KEY on the backend for live nightly rates.</p>
        )}
      </section>

      {/* ---------------- Places ---------------- */}
      <section className="tg-card">
        <h3>📍 Places to visit</h3>
        <p className="tg-muted tg-small">Tap a place to browse its photos.</p>
        {places.length === 0 ? (
          <div className="tg-empty">No attractions were returned.</div>
        ) : (
          <div className="tg-place-grid">
            {places.map((place, i) => {
              const cover = place.photo_names?.[0];
              return (
                <button type="button" className="tg-place" key={`${place.place_name}-${i}`}
                  onClick={() => { setSelectedPlace(place); setPhotoIndex(0); }}>
                  <span className="tg-place-img" style={cover ? { backgroundImage: `url("${photoUrl(cover, 500)}")` } : undefined}>
                    {!cover && "📷"}
                  </span>
                  <span className="tg-place-info">
                    <b>{place.place_name}</b>
                    <small>⭐ {place.rating ?? "N/A"} · {place.user_rating_count ?? 0} reviews</small>
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* ---------------- Itinerary ---------------- */}
      <section className="tg-card">
        <h3>🗓️ Day-wise itinerary</h3>
        {itinerary.length === 0 ? (
          <div className="tg-empty">No itinerary generated.</div>
        ) : (
          <ol className="tg-days">
            {itinerary.map((day) => (
              <li key={day.day_number}>
                <span className="tg-dot">{day.day_number}</span>
                <div>
                  <h4>{day.title}</h4>
                  {day.date && <small className="tg-muted">{fmtDayLong(day.date)}</small>}
                  <ul>{arr(day.activities).map((a, i) => <li key={i}>{a}</li>)}</ul>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      {/* ---------------- Photo modal ---------------- */}
      {selectedPlace && (
        <div className="photo-modal-backdrop" role="presentation" onClick={() => setSelectedPlace(null)}>
          <section className="photo-modal" role="dialog" aria-modal="true"
            aria-label={`${selectedPlace.place_name} photos`} onClick={(e) => e.stopPropagation()}>
            <div className="photo-modal-head">
              <div>
                <span className="eyebrow">EXPLORE BEFORE YOU GO</span>
                <h3>{selectedPlace.place_name}</h3>
                <p>⭐ {selectedPlace.rating ?? "N/A"} · {selectedPlace.address || selectedPlace.description || "Tourist attraction"}</p>
              </div>
              <button type="button" className="photo-close" onClick={() => setSelectedPlace(null)} aria-label="Close photos">✕</button>
            </div>
            {Array.isArray(selectedPlace.photo_names) && selectedPlace.photo_names.length > 0 ? (
              <>
                <div className="photo-viewer">
                  <img src={photoUrl(selectedPlace.photo_names[photoIndex])}
                    alt={`${selectedPlace.place_name} photo ${photoIndex + 1}`}
                    onError={(e) => { e.currentTarget.style.display = "none"; }} />
                </div>
                <div className="photo-controls">
                  <button type="button" disabled={photoIndex === 0} onClick={() => setPhotoIndex((i) => i - 1)}>← Previous</button>
                  <span>Photo {photoIndex + 1} of {selectedPlace.photo_names.length}</span>
                  <button type="button" disabled={photoIndex >= selectedPlace.photo_names.length - 1} onClick={() => setPhotoIndex((i) => i + 1)}>Next →</button>
                </div>
                <div className="photo-thumbnails">
                  {selectedPlace.photo_names.map((name, i) => (
                    <button type="button" key={name} className={i === photoIndex ? "thumbnail active" : "thumbnail"}
                      onClick={() => setPhotoIndex(i)} aria-label={`Show photo ${i + 1}`}>
                      <img src={photoUrl(name, 300)} alt="" loading="lazy" />
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <div className="photo-empty">
                <span>📷</span>
                <b>Photos aren't available from the current place result.</b>
                <p>Open the Google Maps listing to see visitor photos for this location.</p>
                {selectedPlace.google_maps_url && (
                  <a className="primary photo-map-button" href={selectedPlace.google_maps_url} target="_blank" rel="noreferrer">Open photos in Google Maps ↗</a>
                )}
              </div>
            )}
            {selectedPlace.google_maps_url && (
              <a className="map-link modal-map-link" href={selectedPlace.google_maps_url} target="_blank" rel="noreferrer">Open location in Google Maps ↗</a>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
