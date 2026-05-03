from fastapi import APIRouter, Query
from datetime import datetime
from typing import Optional
from ml.predictor import predictor
from ml.demographics import area_sqkm, population
import db

router = APIRouter()


@router.get("/zones")
def get_zones_predictions(date: Optional[str] = Query(None, description="YYYY-MM-DD; defaults to today")):
    if date:
        try:
            date_now = datetime.fromisoformat(date)
        except Exception:
            date_now = datetime.now()
    else:
        date_now = datetime.now()

    response = []
    districts = [f"District {i}" for i in range(1, 11)]

    for i, district in enumerate(districts):
        max_cap = predictor.get_max_capacity_tons(district) / 0.0005
        rolling_weight = max_cap * 0.4

        predicted_tons = predictor.predict_district_waste(district, date_now, rolling_weight)
        max_capacity_tons = predictor.get_max_capacity_tons(district)

        level = 0
        if max_capacity_tons > 0:
            level = min(int((predicted_tons / max_capacity_tons) * 100), 100)

        status = "high" if level >= 85 else ("medium" if level >= 50 else "low")

        reason = f"Predicted load is {predicted_tons:.1f}T vs Historical Max {max_capacity_tons:.1f}T"

        sqkm = area_sqkm(district)
        pop = population(district)
        density_tons_per_sqkm = (predicted_tons / sqkm) if sqkm else 0.0
        per_capita_kg = (predicted_tons * 1000.0 / pop) if pop else 0.0

        response.append({
            "id": f"D{i+1}",
            "name": district,
            "zoneNo": i + 1,
            "level": level,
            "status": status,
            "reason": reason,
            "predictedTons": round(predicted_tons, 2),
            "areaSqkm": sqkm,
            "population": pop,
            "densityTonsPerSqkm": round(density_tons_per_sqkm, 3),
            "perCapitaKg": round(per_capita_kg, 3),
        })

        try:
            db.log_prediction(district, float(predicted_tons), int(level), status)
        except Exception:
            pass

    return response
