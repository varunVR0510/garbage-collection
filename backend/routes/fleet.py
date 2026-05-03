from fastapi import APIRouter, Query
from datetime import datetime
from typing import Optional
import pandas as pd

from ml.route_geometry import routes_dataframe, district_for_route
from ml.predictor import predictor
from ml.demographics import features_for as demographic_features_for

router = APIRouter()


def _parse_date(date_str: Optional[str]) -> datetime:
    if date_str:
        try:
            return datetime.fromisoformat(date_str)
        except Exception:
            pass
    return datetime.now()

# Standard truck capacities for Austin Resource Recovery
CAPACITY_BY_OP_TYPE = {
    "Auto": 12.0,   # Automated side-loader
    "Semi": 20.0,   # Semi-automated rear-loader
}


def _predicted_load_per_district(date: datetime) -> dict:
    """Predict expected daily tonnage per district using the trained model."""
    if not predictor.model or not predictor.feature_order:
        return {}
    districts = [f"District {i}" for i in range(1, 11)]
    ts = pd.Timestamp(date)
    rows = []
    for d in districts:
        max_cap_lbs = predictor.get_max_capacity_tons(d) / 0.0005
        rolling = max_cap_lbs * 0.4
        demo = demographic_features_for(d)
        rows.append((d, {
            'district_encoded': predictor.district_mapping.get(d, 0),
            'day_of_week': ts.dayofweek,
            'month': ts.month,
            'is_weekend': 1 if ts.dayofweek in [5, 6] else 0,
            'rolling_7_load_weight': rolling,
            **demo,
        }))
    X = pd.DataFrame([{k: r.get(k, 0.0) for k in predictor.feature_order} for _, r in rows])
    preds = predictor.model.predict(X)
    return {d: float(p) * 0.0005 for (d, _), p in zip(rows, preds)}


def _build_fleet(when: Optional[datetime] = None):
    df = routes_dataframe()
    if df.empty:
        return []

    when = when or datetime.now()
    today_name = when.strftime('%A')
    df['district'] = df['GARB_RT'].apply(district_for_route)
    df['GARB_DAY'] = df['GARB_DAY'].astype(str).str.strip()
    df['OP_TYPE'] = df['OP_TYPE'].astype(str).str.strip()

    predicted_loads = _predicted_load_per_district(when)
    routes_per_district = df['district'].value_counts().to_dict()

    fleet = []
    for _, r in df.iterrows():
        op = r['OP_TYPE']
        cap = CAPACITY_BY_OP_TYPE.get(op, 12.0)
        district = r['district']
        day = r['GARB_DAY']
        is_today = (day == today_name)

        # Distribute the district's predicted tonnage across its routes
        n_routes = routes_per_district.get(district, 1) or 1
        district_tons = predicted_loads.get(district, 0.0)
        load = round(district_tons / n_routes, 2) if is_today else 0.0
        load = min(load, cap)

        if is_today and load >= cap * 0.85:
            status = "returning"
        elif is_today and load > 0:
            status = "on-route"
        else:
            status = "idle"

        fleet.append({
            "id": str(r['GARB_RT']),
            "type": "Auto Side-Loader" if op == "Auto" else ("Semi Rear-Loader" if op == "Semi" else op or "Unknown"),
            "opType": op,
            "capacity": cap,
            "load": load,
            "status": status,
            "district": district,
            "garbDay": day,
            "scheduledToday": is_today,
            "supervisor": str(r.get('GARB_SUP', '') or ''),
            "route": f"{district} · {day}" if district else day,
        })

    fleet.sort(key=lambda t: (not t["scheduledToday"], t["id"]))
    return fleet


def get_real_fleet(when: Optional[datetime] = None):
    """Compatibility shim used by routing.py."""
    return _build_fleet(when)


@router.get("/status")
def get_fleet_status(date: Optional[str] = Query(None)):
    return _build_fleet(_parse_date(date))


@router.get("/assignments")
def get_fleet_assignments(date: Optional[str] = Query(None)):
    return [
        {
            "vehicleId": t["id"],
            "assignedZone": t["district"] if t["scheduledToday"] else "Off-duty",
            "status": t["status"],
            "garbDay": t["garbDay"],
        }
        for t in _build_fleet(_parse_date(date))
    ]


@router.get("/utilization")
def get_fleet_utilization(date: Optional[str] = Query(None)):
    when = _parse_date(date)
    fleet = _build_fleet(when)
    today_fleet = [t for t in fleet if t["scheduledToday"]]
    total_cap = sum(t["capacity"] for t in today_fleet)
    total_load = sum(t["load"] for t in today_fleet)
    pct = (total_load / total_cap * 100.0) if total_cap > 0 else 0.0
    return {
        "utilizationPercentage": round(pct, 1),
        "activeVehicles": len(today_fleet),
        "totalVehicles": len(fleet),
        "todayName": when.strftime('%A'),
    }
