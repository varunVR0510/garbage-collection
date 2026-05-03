from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from routes.fleet import _build_fleet
from routes.predictions import get_zones_predictions
from ml.route_geometry import district_centroid
import db

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

    # 1. Truck assigned to this district AND scheduled today AND not already dispatched
    candidates_today = [
        t for t in fleet
        if t.get('district') == target_district
        and t.get('scheduledToday')
        and not db.truck_already_dispatched_today(t['id'])
    ]

    # 2. Otherwise any truck in this district not already dispatched
    if not candidates_today:
        candidates_today = [
            t for t in fleet
            if t.get('district') == target_district
            and not db.truck_already_dispatched_today(t['id'])
        ]

    # 3. Last resort: any free truck
    if not candidates_today:
        candidates_today = [t for t in fleet if not db.truck_already_dispatched_today(t['id'])]

    if not candidates_today:
        raise HTTPException(status_code=409, detail="No trucks available — all already dispatched today")

    truck = candidates_today[0]

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
