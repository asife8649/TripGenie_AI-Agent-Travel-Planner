import React from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function VerifyOTP() {
  const [email, setEmail] = useState(localStorage.getItem("pendingEmail") || "");
  const [otp, setOtp] = useState("");
  const [msg, setMsg] = useState("");
  const navigate = useNavigate();

  const verify = async (e) => {
    e.preventDefault();
    try {
      await api.post("/auth/verify-otp", { email, otp });
      localStorage.removeItem("pendingEmail");
      navigate("/login");
    } catch (err) {
      setMsg(err.response?.data?.detail || "Verification failed");
    }
  };

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={verify}>
        <h1>📩 Verify Email</h1>
        <p>Enter the 6-digit OTP sent to your email.</p>
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" />
        <input className="otp" maxLength="6" value={otp} onChange={e => setOtp(e.target.value.replace(/\D/g, ""))} placeholder="000000" />
        <button className="primary">Verify OTP</button>
        {msg && <div className="error">{msg}</div>}
        <small>During development, the OTP is printed in the backend terminal unless SMTP is enabled.</small>
      </form>
    </main>
  );
}
