import React, { useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [stage, setStage] = useState("request");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const requestOtp = async (event) => {
    event.preventDefault();
    setLoading(true); setMessage(""); setError("");
    try {
      const { data } = await api.post("/auth/forgot-password", { email: email.trim().toLowerCase() });
      setMessage(data.message || "If the account exists, a reset OTP has been created.");
      setStage("reset");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not request a reset OTP.");
    } finally { setLoading(false); }
  };

  const resetPassword = async (event) => {
    event.preventDefault();
    setLoading(true); setMessage(""); setError("");
    try {
      const { data } = await api.post("/auth/reset-password", {
        email: email.trim().toLowerCase(), otp: otp.trim(), new_password: newPassword,
      });
      setMessage(data.message || "Password reset successfully. You can now log in.");
      setStage("done");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not reset password.");
    } finally { setLoading(false); }
  };

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={stage === "request" ? requestOtp : resetPassword}>
        <h1>Reset password</h1>
        <p>Request a one-time code, then choose a new password.</p>
        <label>Email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" disabled={stage !== "request"} />
        {stage !== "request" && <>
          <label>6-digit OTP</label>
          <input className="otp" required inputMode="numeric" maxLength={6} value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))} placeholder="000000" disabled={stage === "done"} />
          <label>New password</label>
          <input type="password" required minLength={6} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="At least 6 characters" disabled={stage === "done"} />
        </>}
        {stage !== "done" && <button className="primary" type="submit" disabled={loading}>{loading ? "Please wait..." : stage === "request" ? "Send reset OTP" : "Reset password"}</button>}
        {message && <div className="success">{message}</div>}
        {error && <div className="error">{error}</div>}
        <small>We'll email a 6-digit code if this address is registered. Check your spam folder too.</small>
        <p><Link to="/login">Back to login</Link></p>
      </form>
    </main>
  );
}
