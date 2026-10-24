import React from "react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

export default function MyTrips() {
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const loadTrips = async () => {
    try {
      setLoading(true);
      setMsg("");

      const { data } = await api.get("/trips/mine");
      setTrips(Array.isArray(data) ? data : []);

    } catch (err) {
      const detail = err.response?.data?.detail;

      if (Array.isArray(detail)) {
        setMsg(
          detail
            .map((item) => item.msg || "Invalid input")
            .join(", ")
        );
      } else {
        setMsg(detail || "Could not load saved trips");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrips();
  }, []);

  const deleteTrip = async (id) => {
    const ok = window.confirm(
      "Delete this saved trip?"
    );

    if (!ok) return;

    try {
      await api.delete(`/trips/${id}`);
      await loadTrips();
    } catch (err) {
      setMsg(
        err.response?.data?.detail ||
        "Could not delete trip"
      );
    }
  };

  const money = (value) => {
    if (value === null || value === undefined || value === "") {
      return "Price unavailable";
    }

    const amount = Number(value);
    if (!Number.isFinite(amount)) {
      return "Price unavailable";
    }

    return `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  };

  return (
    <main className="container">
      <section className="hero compact">
        <span className="eyebrow">
          SAVED TRIPS
        </span>

        <h1>My Trips</h1>

        <p>
          Your saved TripGenie travel plans.
        </p>
      </section>

      {loading && (
        <div className="empty">
          Loading your trips...
        </div>
      )}

      {!loading && msg && (
        <div className="error container-msg">
          {msg}
        </div>
      )}

      {!loading && !msg && trips.length === 0 && (
        <div className="empty">
          <p>No saved trips yet.</p>

          <Link to="/planner">
            Create your first trip →
          </Link>
        </div>
      )}

      {!loading && trips.length > 0 && (
        <div className="trip-list">
          {trips.map((trip) => (
            <div
              className="trip-card"
              key={trip.id}
            >
              <span>🌴</span>

              <div>
                <h3>
                  {trip.source || "Your location"}
                  {" → "}
                  {trip.destination}
                </h3>

                <p>
                  {trip.days} days ·{" "}
                  {trip.travelers} travelers ·{" "}
                  Budget {money(trip.budget)}
                </p>

                <p>
                  Transport:{" "}
                  {trip.transport_option}
                </p>

                {(trip.departure_date || trip.return_date) && (
                  <p>Dates: {trip.departure_date || "—"} → {trip.return_date || "—"}</p>
                )}

                {trip.created_at && (
                  <small>
                    Saved:{" "}
                    {new Date(
                      trip.created_at
                    ).toLocaleString()}
                  </small>
                )}
              </div>

              <div>
                <b>
                  {money(
                    trip.total_estimated_cost
                  )}
                </b>

                <button
                  className="danger-button"
                  onClick={() =>
                    deleteTrip(trip.id)
                  }
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
