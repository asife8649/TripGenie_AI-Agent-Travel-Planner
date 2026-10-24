import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api";

export default function Register() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
  });

  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setMsg("");

    if (form.name.trim().length < 2) {
      setMsg("Please enter your full name.");
      return;
    }

    if (form.password.length < 6) {
      setMsg("Password must contain at least 6 characters.");
      return;
    }

    setLoading(true);

    try {
      await api.post("/auth/register", {
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
      });

      localStorage.setItem(
        "pendingEmail",
        form.email.trim().toLowerCase()
      );

      navigate("/verify-otp");

    } catch (err) {
      const detail = err.response?.data?.detail;

      if (Array.isArray(detail)) {
        setMsg(
          detail
            .map((item) => item.msg || "Invalid input")
            .join(", ")
        );
      } else {
        setMsg(detail || "Registration failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h1>Create Account</h1>

        <p>
          Join TripGenie and plan smarter trips.
        </p>

        <input
          required
          placeholder="Full name"
          value={form.name}
          onChange={(e) =>
            setForm({
              ...form,
              name: e.target.value,
            })
          }
        />

        <input
          required
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={(e) =>
            setForm({
              ...form,
              email: e.target.value,
            })
          }
        />

        <input
          required
          minLength={6}
          type="password"
          placeholder="Password (6+ characters)"
          value={form.password}
          onChange={(e) =>
            setForm({
              ...form,
              password: e.target.value,
            })
          }
        />

        <button
          className="primary"
          type="submit"
          disabled={loading}
        >
          {loading ? "Creating..." : "Create Account"}
        </button>

        {msg && (
          <div className="error">
            {msg}
          </div>
        )}

        <p>
          Already have an account?{" "}
          <Link to="/login">Login</Link>
        </p>
      </form>
    </main>
  );
}
