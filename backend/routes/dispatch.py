from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import math

from routes.fleet import _build_fleet
from routes.predictions import get_zones_predictions
from ml.route_geometry import district_centroid
import db


DEPOT = (30.2672, -97.7431)


def _haversine_km(a, b) -> float:
    R = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def _eta_minutes_for_km(km: float) -> int:
    return int((km / 25.0) * 60)

router = APIRouter()


class DispatchIn(BaseModel):
    zone_id: str = Field(..., min_length=1, max_length=16)


@router.post("/assign")
def assign_truck(payload: DispatchIn):
    zones = get_zones_predictions()
    zone = next((z for z in zones if z['id'] == payload.zone_id), None)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone {payload.zone_id} not found")

    fleet = _build_fleet()
    target_district = zone['name']
    target_centroid = district_centroid(target_district)

    free_fleet = [t for t in fleet if not db.truck_already_dispatched_today(t['id'])]
    if not free_fleet:
        raise HTTPException(status_code=409, detail="No trucks available — all already dispatched today")

    # Nearest-free-truck dispatch: each truck scored by distance from its home-district centroid
    # to the target zone. Lower distance = lower fuel cost. Prefer trucks scheduled today,
    # then break ties by distance.
    def truck_score(t):
        truck_origin = district_centroid(t.get('district') or target_district)
        dist = _haversine_km(truck_origin, target_centroid)
        # Trucks scheduled today get a 5km "discount" — slight preference but distance still wins
        bonus = -5.0 if t.get('scheduledToday') else 0.0
        return dist + bonus

    free_fleet.sort(key=truck_score)
    truck = free_fleet[0]

    today_name = datetime.now().strftime('%A')
    is_weekend = today_name in ('Saturday', 'Sunday')
    matches_schedule = truck.get('garbDay') == today_name
    mode = 'emergency' if (is_weekend or not matches_schedule) else 'scheduled'

    # Rough ETA from depot to district centroid (haversine + 25 km/h)
    import math
    depot = (30.2672, -97.7431)
    dest = district_centroid(target_district)
    R = 6371
    lat1, lon1 = math.radians(depot[0]), math.radians(depot[1])
    lat2, lon2 = math.radians(dest[0]), math.radians(dest[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    km = R * c
    eta_min = int((km / 25.0) * 60)

    dispatch_id = db.log_dispatch(
        zone_id=payload.zone_id,
        zone_name=target_district,
        truck_id=truck['id'],
        truck_type=truck.get('type'),
        district=target_district,
        eta_minutes=eta_min,
        mode=mode,
    )

    return {
        "ok": True,
        "dispatch_id": dispatch_id,
        "truck_id": truck['id'],
        "truck_type": truck.get('type'),
        "district": target_district,
        "zone_id": payload.zone_id,
        "eta_minutes": eta_min,
        "distance_km": round(km, 1),
        "mode": mode,
        "truck_garb_day": truck.get('garbDay'),
        "today_name": today_name,
    }


@router.get("/today")
def list_today():
    return db.list_dispatches_today()


def _build_plan(date_str: Optional[str] = None):
    """Compute the optimal truck → zone assignment for high+medium zones using greedy
    nearest-neighbor matching. Returns the plan + a fuel-cost comparison vs naive
    'send each truck to its own home district' baseline."""
    zones = get_zones_predictions(date=date_str)
    priority = [z for z in zones if z['status'] in ('high', 'medium')]
    if not priority:
        return {"plan": [], "naive_km": 0.0, "smart_km": 0.0, "saved_km": 0.0, "saved_pct": 0.0, "saved_fuel_l": 0.0}

    fleet = _build_fleet()
    free_fleet = [t for t in fleet if not db.truck_already_dispatched_today(t['id'])]

    # Greedy: for each zone (highest fill first), pick the closest unused free truck
    priority.sort(key=lambda z: z['level'], reverse=True)
    available = list(free_fleet)
    plan = []
    smart_total_km = 0.0
    naive_total_km = 0.0

    for z in priority:
        target = district_centroid(z['name'])
        if not available:
            break
        # Smart: pick the closest truck
        scored = [
            (_haversine_km(district_centroid(t.get('district') or z['name']), target), t)
            for t in available
        ]
        scored.sort(key=lambda x: x[0])
        smart_km, truck = scored[0]
        available.remove(truck)
        smart_total_km += smart_km

        # Naive: pretend we sent a truck from the depot directly (no district pre-assignment knowledge)
        naive_km = _haversine_km(DEPOT, target)
        naive_total_km += naive_km

        plan.append({
            "zone_id": z['id'],
            "zone_name": z['name'],
            "fill_level": z['level'],
            "status": z['status'],
            "truck_id": truck['id'],
            "truck_type": truck.get('type'),
            "truck_home_district": truck.get('district'),
            "scheduled_today": bool(truck.get('scheduledToday')),
            "distance_km": round(smart_km, 1),
            "naive_km": round(naive_km, 1),
            "eta_minutes": _eta_minutes_for_km(smart_km),
        })

    saved_km = max(naive_total_km - smart_total_km, 0.0)
    saved_pct = (saved_km / naive_total_km * 100.0) if naive_total_km > 0 else 0.0
    return {
        "plan": plan,
        "naive_km": round(naive_total_km, 1),
        "smart_km": round(smart_total_km, 1),
        "saved_km": round(saved_km, 1),
        "saved_pct": round(saved_pct, 1),
        "saved_fuel_l": round(saved_km * 0.35, 1),
    }


@router.get("/plan")
def get_plan(date: Optional[str] = Query(None)):
    return _build_plan(date)


@router.post("/auto-assign")
def auto_assign(date: Optional[str] = Query(None)):
    """Apply the optimal plan: log a dispatch for every (zone, truck) pair."""
    result = _build_plan(date)
    if not result["plan"]:
        return {"ok": True, "dispatched": 0, "saved_km": 0.0, "saved_fuel_l": 0.0}

    today_name = datetime.now().strftime('%A')
    is_weekend = today_name in ('Saturday', 'Sunday')

    dispatched = 0
    for item in result["plan"]:
        if db.truck_already_dispatched_today(item['truck_id']):
            continue
        mode = 'emergency' if is_weekend or not item['scheduled_today'] else 'scheduled'
        db.log_dispatch(
            zone_id=item['zone_id'],
            zone_name=item['zone_name'],
            truck_id=item['truck_id'],
            truck_type=item['truck_type'],
            district=item['zone_name'],
            eta_minutes=item['eta_minutes'],
            mode=mode,
        )
        dispatched += 1

    return {
        "ok": True,
        "dispatched": dispatched,
        "saved_km": result['saved_km'],
        "saved_fuel_l": result['saved_fuel_l'],
        "saved_pct": result['saved_pct'],
    }
