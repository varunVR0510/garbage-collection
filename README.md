# Austin SmartWaste — AI-Powered Waste Collection Dashboard

A full-stack smart-waste-management system for the City of Austin: predicts daily waste tonnage per district, classifies zones into priority levels, and computes fuel-optimal collection routes using OR-Tools VRP. Built on real Austin Open Data.

- **Frontend**: Next.js 16 + React 19 + Tailwind + Recharts + Leaflet
- **Backend**: FastAPI + SQLite + XGBoost + OR-Tools + Shapely
- **Data**: 350K+ historical waste records (`cleaned_waste_data.csv`) + 184 real Austin route polygons (`backend/data/austin_routes_2015.xlsx`) + per-district demographics (`backend/data/district_demographics.json`)

---

## Prerequisites

- **Node.js 18+** (for the frontend)
- **Python 3.11** (for the backend)
- **Git**

---

## Setup (one-time)

### 1. Clone the repo

```bash
git clone https://github.com/varunVR0510/garbage-collection.git
cd garbage-collection
```

### 2. Install frontend dependencies

```bash
npm install
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

If you're on Windows and `pip install ortools` fails, run `python -m pip install --upgrade pip` first.

---

## Running the application

You need **two terminals** open.

### Terminal 1 — Backend (port 8000)

```bash
cd backend
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Terminal 2 — Frontend (port 3000)

```bash
npm run dev
```

You should see:
```
▲ Next.js 16.x
- Local:   http://localhost:3000
✓ Ready
```

### Open the dashboard

Visit **http://localhost:3000** in your browser.

---

## First-time data seeding

The XGBoost model ships pre-trained, but the SQLite database (`smartwaste.db`) is created fresh on first backend startup. To populate it with model metadata:

1. Go to **Analytics** page → click **"Trigger Model Retraining (Feedback Loop)"** button.
2. After ~10 seconds the model retrains on the full 350K-row dataset and writes `r2`/`MAE`/`n_samples` into the DB.
3. The sidebar will switch from "Model: untrained" to "Avg error: ±2.4 T · Moderate".

You can also seed it via curl:
```bash
curl -X POST http://localhost:8000/api/model/retrain
```

---

## Smoke test (verify everything works)

After both servers are running, try these flows:

| Flow | Where | What you should see |
|---|---|---|
| Date picker | Header (top right) | Click → calendar pops up. Pick any date — all KPIs/chart/map/fleet update. |
| Total Predicted Waste | Dashboard KPI | ~994 T on a Monday (matches the chart's "selected" point exactly). |
| 7-Day Forecast chart | Dashboard | Bars (historical avg) + Line (AI forecast). Sat/Sun are 0; Monday spikes. |
| Real route polygons | Map page | 184 colored polygons across actual Austin geography, click any to inspect. |
| Per-truck routing | Routes page | Click any truck in the left sidebar — timeline updates with that truck's multi-stop tour. |
| Smart Dispatch Plan | Routes page (when high-priority zones exist) | Greedy nearest-neighbor matching with km/L savings vs naive baseline. |
| Auto-Dispatch All | Routes page | One-click bulk dispatch — fills the "Today's Dispatches" log. |
| Citizen feedback | curl `POST /api/feedback` | Posts get reflected in Analytics → Recent Collections. |

---

## API endpoints

Full Swagger UI: **http://localhost:8000/docs**

Key endpoints (all accept `?date=YYYY-MM-DD`):

- `GET /api/dashboard/kpi` — 6 KPI cards
- `GET /api/dashboard/chart` — 7-day forecast (yesterday + today + next 5 days, weekend-zeroed)
- `GET /api/zones` — 10 districts with predicted tons, status, density
- `GET /api/alerts` — Auto-generated alerts for high/medium zones
- `GET /api/fleet/status` — 184 trucks with district, day, load, status
- `GET /api/routes/optimized` — City-wide VRP timeline
- `GET /api/routes/summary` — Distance/fuel/time + saved-vs-naive
- `GET /api/routes/truck/{id}` — Per-truck multi-stop tour
- `GET /api/schedule/weekly` — Mon–Fri schedule grid (real GARB_DAY data)
- `GET /api/dispatch/plan` — Optimal truck-zone assignment plan
- `POST /api/dispatch/auto-assign` — Apply the plan (bulk dispatch)
- `POST /api/dispatch/assign` — Single zone dispatch (nearest free truck)
- `GET /api/dispatch/today` — Today's dispatch log
- `POST /api/model/retrain` — Retrain XGBoost; writes `r2`/MAE to SQLite
- `GET /api/model/status` — Latest training metrics
- `POST /api/feedback` — Submit actual collection tonnage
- `GET /api/metrics`, `/api/fuel`, `/api/collections` — Analytics page data

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│  Next.js Frontend (port 3000)                      │
│  ├── /            Dashboard (KPIs + chart + map)   │
│  ├── /map         Prediction Map (route polygons)  │
│  ├── /routes      Fleet & Smart Dispatch Plan      │
│  └── /analytics   Performance + Retrain            │
└────────────┬───────────────────────────────────────┘
             │  fetch('/api/...')
┌────────────▼───────────────────────────────────────┐
│  FastAPI Backend (port 8000)                       │
│  ├── routes/dashboard.py    forecast + KPIs        │
│  ├── routes/predictions.py  XGBoost zone scoring   │
│  ├── routes/routing.py      OR-Tools VRP solver    │
│  ├── routes/dispatch.py     Smart truck assignment │
│  ├── routes/fleet.py        184-truck fleet model  │
│  ├── routes/analytics.py    MAE, fuel, collections │
│  ├── routes/schedule.py     Mon-Fri schedule grid  │
│  ├── routes/model.py        Retrain endpoint       │
│  ├── routes/feedback.py     Citizen feedback API   │
│  ├── ml/train.py            XGBoost training       │
│  ├── ml/predictor.py        Live prediction        │
│  ├── ml/route_geometry.py   KMeans on polygons     │
│  ├── ml/demographics.py     District profile       │
│  └── db.py                  SQLite layer           │
└────────────┬───────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────┐
│  Data + Models                                     │
│  ├── cleaned_waste_data.csv      (350K rows)       │
│  ├── backend/data/austin_routes_2015.xlsx (184 routes) │
│  ├── backend/data/district_demographics.json       │
│  ├── backend/ml/model.joblib     (pre-trained)     │
│  └── backend/smartwaste.db       (created on boot) │
└────────────────────────────────────────────────────┘
```

---

## Common problems

| Issue | Fix |
|---|---|
| `ModuleNotFoundError: ortools` | `pip install ortools` |
| `model.joblib not found` | Click "Trigger Retraining" once or run `python backend/ml/train.py` |
| Frontend shows blank map | Ensure backend is running on port 8000 (CORS is open in dev) |
| Sidebar says "Model: untrained" | Click Retrain in Analytics page once |
| Port 8000 in use | `taskkill /F /IM python.exe` (Windows) or `lsof -ti:8000 \| xargs kill` (Mac/Linux) |
| Hydration mismatch warning | Ensure browser is fully refreshed (Ctrl+Shift+R) |

---

## License

Data: City of Austin Open Data Portal (public domain).
Code: MIT.
