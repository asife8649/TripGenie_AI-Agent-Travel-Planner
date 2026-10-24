import React from "react";
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../api";

export default function Login() {
  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setMsg("");
    setLoading(true);

    try {
      const { data } = await api.post("/auth/login", {
        email: form.email.trim().toLowerCase(),
        password: form.password,
      });

      localStorage.setItem("token", data.access_token);
      localStorage.setItem(
        "user",
        JSON.stringify(data.user)
      );

      navigate("/planner");

    } catch (err) {
      const detail = err.response?.data?.detail;

      if (Array.isArray(detail)) {
        setMsg(
          detail
            .map((item) => item.msg || "Invalid input")
            .join(", ")
        );
      } else {
        setMsg(detail || "Login failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h1>Welcome Back ✈️</h1>

        <p>
          Login to create your next travel plan.
        </p>

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
          type="password"
          placeholder="Password"
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
          {loading ? "Logging in..." : "Login"}
        </button>

        {msg && (
          <div className="error">
            {msg}
          </div>
        )}

        <p>
          <Link to="/forgot-password">
            Forgot password?
          </Link>
        </p>

        <p>
          New user?{" "}
          <Link to="/register">
            Create an account
          </Link>
        </p>
      </form>
    </main>
  );
}
