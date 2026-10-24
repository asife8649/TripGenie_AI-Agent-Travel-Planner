# TripGenie — AI Agent Travel Planner

This is a planning-only application. It does not book tickets, reserve hotel rooms, or process payments. Provider availability, prices, and quotas depend on the configured API accounts.

## 1. Supabase database

1. Open your Supabase project → **SQL Editor**.
2. Run `database/schema.sql`.
3. In **Project Settings → Database → Connect**, copy the PostgreSQL connection URI. Use the exact connection option/host recommended by Supabase for your network (direct or session pooler).
4. Create `backend/.env` by copying `backend/.env.example`; set `DATABASE_URL` with your actual password. URL-encode special characters in the password if required. Never commit or share `.env`.

The earlier `password authentication failed for user postgres` error is a credentials/connection-string issue, not a React/CORS issue. Correct the Supabase database password or URI before testing authenticated endpoints.

## 2. Backend

Windows PowerShell:

```powershell
cd "F:\TripGenie_AI Multi-Agent Travel Planner\backend"
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit backend/.env with your real Supabase URL and SECRET_KEY
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/health`.

## 3. Frontend

Open a second PowerShell window:

```powershell
cd "F:\TripGenie_AI Multi-Agent Travel Planner\frontend"
npm install
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

`VITE_API_URL` defaults to `http://127.0.0.1:8000`. If you change the backend URL, update `frontend/.env` and restart Vite. For deployment, set it to your Render backend URL (without a trailing slash).

## 4. API provider setup

See **`API_SETUP_GUIDE.md`** for the full step-by-step guide. Summary:

- `GOOGLE_MAPS_API_KEY` — Places API (New) + Routes API: attractions, photos, **real hotel names/ratings/photos**, train/bus **stations and times** (where Google has the schedule).
- `SERPAPI_KEY` *(optional)* — **live hotel nightly prices** (Google Hotels engine). Without it hotel prices are labelled estimates.
- `IGNAV_API_KEY` / `FLIGHT_API_KEY` — flights with airline, flight number, **departure/arrival times**, stops and fare.
- `RAIL_API_KEY` + `RAIL_API_HOST` *(optional, paid RapidAPI listing)* — real train list and class fares. Without it, fares are distance-based estimates.
- Bus fares have no public API: Google route if available, otherwise a labelled estimate and a redBus link.

Every price is tagged **Live fare**, **Google price range**, **Indicative** or **Estimate** in the UI and the PDF.

## 5. OTP email

For local development, leave `SMTP_ENABLED=false`; the OTP is printed in the backend terminal. To send actual emails, configure `SMTP_ENABLED=true`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM` in `backend/.env`. Never share these secrets.

## 6. Troubleshooting

- `password authentication failed`: fix `DATABASE_URL` / Supabase database password.
- `401 Invalid or expired token`: log in again; JWT expires after 60 minutes. Ensure frontend stores `access_token` as `token`.
- `Could not generate travel plan`: inspect backend terminal logs for provider/API errors and quota information.
- CORS: local origins `localhost:5173` and `127.0.0.1:5173` are allowed by default. For deployment, set `FRONTEND_ORIGINS` on Render to your exact Vercel frontend origin(s), comma-separated, and redeploy the backend.
- Schema mismatch: run the SQL schema/migration in Supabase. Do not use the old MySQL `CREATE DATABASE` schema with this PostgreSQL backend.

## Security

Never upload `.env`, provider API keys, database passwords, SMTP passwords, private keys, or certificates to chat/GitHub. `.env.example` contains placeholders only.
