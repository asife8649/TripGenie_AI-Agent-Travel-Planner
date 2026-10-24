import React from "react";
import { useState } from "react";
import api from "../api";
import PlanResult from "../components/PlanResult";

const initial = {
  source: "",
  destination: "",
  budget_per_person: 10000,
  travelers: 2,
  days: 3,
  departure_date: "",
  return_date: "",
  transport_option: "both",
};

export default function Planner() {
  const [form, setForm] = useState(initial);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const update = (key, value) => {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const generate = async (e) => {
    e.preventDefault();

    if (form.return_date && form.departure_date && form.return_date < form.departure_date) {
      setError("Return date cannot be earlier than departure date.");
      return;
    }

    setLoading(true);
    setError("");
    setSaved(false);
    setPlan(null);

    try {
      const payload = {
        source: form.source.trim(),
        destination: form.destination.trim(),
        budget_per_person: Number(form.budget_per_person),
        travelers: Number(form.travelers),
        days: Number(form.days),
        transport_option: form.transport_option,
        departure_date: form.departure_date,
        return_date: form.return_date,
      };

      const { data } = await api.post("/trips/plan", payload);

      setPlan(data);
    } catch (err) {
      const detail = err.response?.data?.detail;

      if (Array.isArray(detail)) {
        setError(
          detail
            .map((item) => item.msg || "Invalid input")
            .join(", ")
        );
      } else {
        setError(detail || "Could not generate the travel plan.");
      }
    } finally {
      setLoading(false);
    }
  };

  const save = async () => {
    if (!plan || saving || saved) return;

    try {
      setSaving(true);
      setError("");

      await api.post("/trips/save", {
        ...form,
        budget_per_person: Number(form.budget_per_person),
        travelers: Number(form.travelers),
        days: Number(form.days),
        total_estimated_cost: plan.total_estimated_cost ?? null,
        remaining_budget: plan.remaining_budget ?? null,
      });

      setSaved(true);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Could not save this trip."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="container">
      <section className="hero">
        <span className="eyebrow">AI MULTI-AGENT TRAVEL PLANNER</span>

        <h1>Plan your perfect trip in minutes.</h1>

        <p>
          Enter your route, budget and travel dates. TripGenie combines
          transport, hotels, real attractions, budget information and a
          day-wise itinerary.
        </p>
      </section>

      <form className="planner-form" onSubmit={generate}>
        <label>
          From
          <input
            required
            value={form.source}
            onChange={(e) => update("source", e.target.value)}
            placeholder="Kolkata"
          />
        </label>

        <label>
          Destination
          <input
            required
            value={form.destination}
            onChange={(e) => update("destination", e.target.value)}
            placeholder="Murshidabad"
          />
        </label>

        <label>
          Budget per person (₹)
          <input
            required
            type="number"
            min="1"
            value={form.budget_per_person}
            onChange={(e) =>
              update("budget_per_person", e.target.value)
            }
          />
        </label>

        <label>
          Travelers
          <input
            required
            type="number"
            min="1"
            value={form.travelers}
            onChange={(e) => update("travelers", e.target.value)}
          />
        </label>

        <label>
          Days
          <input
            required
            type="number"
            min="1"
            value={form.days}
            onChange={(e) => update("days", e.target.value)}
          />
        </label>

        <label>
          Departure date
          <input
            required
            type="date"
            value={form.departure_date}
            onChange={(e) =>
              update("departure_date", e.target.value)
            }
          />
        </label>

        <label>
          Return date
          <input
            required
            type="date"
            value={form.return_date}
            min={form.departure_date || undefined}
            onChange={(e) =>
              update("return_date", e.target.value)
            }
          />
        </label>

        <label>
          Transport
          <select
            value={form.transport_option}
            onChange={(e) =>
              update("transport_option", e.target.value)
            }
          >
            <option value="flight">Flight</option>
            <option value="train">Train</option>
            <option value="bus">Bus</option>
            <option value="both">Train + Bus</option>
            <option value="all">Flight + Train + Bus</option>
          </select>
        </label>

        <button
          className="primary generate"
          type="submit"
          disabled={loading}
        >
          {loading ? "Planning your trip..." : "✨ Generate My Trip"}
        </button>
      </form>

      {error && (
        <div className="error container-msg">
          {error}
        </div>
      )}

      {plan && (
        <>
          <div className="save-row">
            <button className="primary" onClick={save} disabled={saving || saved}>
              {saving ? "Saving..." : saved ? "✓ Trip Saved" : "💾 Save This Trip"}
            </button>

            {saved && (
              <span className="success">
                Saved successfully!
              </span>
            )}
          </div>

          <PlanResult plan={plan} />
        </>
      )}
    </main>
  );
}
