from fastapi import APIRouter
from collections import defaultdict
import pandas as pd

from ml.route_geometry import routes_dataframe, district_for_route
from ml.predictor import predictor
from ml.demographics import features_for as demographic_features_for

router = APIRouter()

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


@router.get("/weekly")
def weekly_schedule():
    """Return Mon-Fri schedule grid: for each weekday, list districts being collected,
    route counts, truck-type breakdown, and predicted tonnage."""
    df = routes_dataframe()
    if df.empty:
        return {"days": [], "totals": {}}

    df['district'] = df['GARB_RT'].apply(district_for_route)
    df['GARB_DAY'] = df['GARB_DAY'].astype(str).str.strip()

    # Aggregate route count + truck-type per day×district
    grouped = df.groupby(['GARB_DAY', 'district']).agg(
        route_count=('GARB_RT', 'count'),
        auto_count=('OP_TYPE', lambda s: int((s == 'Auto').sum())),
        semi_count=('OP_TYPE', lambda s: int((s == 'Semi').sum())),
    ).reset_index()

    # Predict tonnage per district once (reuse for every day it appears)
    tonnage_by_district = _predict_tonnage_per_district()

    out = []
    totals = defaultdict(lambda: {"routes": 0, "predicted_tons": 0.0})

    for day in DAY_ORDER:
        day_rows = grouped[grouped['GARB_DAY'] == day]
        districts = []
        day_routes = 0
        day_tons = 0.0
        for _, row in day_rows.iterrows():
            d = row['district']
            t = tonnage_by_district.get(d, 0.0)
            districts.append({
                "district": d,
                "routes": int(row['route_count']),
                "auto": int(row['auto_count']),
                "semi": int(row['semi_count']),
                "predicted_tons": round(t, 1),
            })
            day_routes += int(row['route_count'])
            day_tons += t
        districts.sort(key=lambda x: x['predicted_tons'], reverse=True)
        out.append({
            "day": day,
            "routes": day_routes,
            "predicted_tons": round(day_tons, 1),
            "districts": districts,
        })
        totals["all"]["routes"] += day_routes
        totals["all"]["predicted_tons"] += day_tons

    return {
        "days": out,
        "weekTotalRoutes": int(totals["all"]["routes"]),
        "weekTotalTons": round(totals["all"]["predicted_tons"], 1),
    }


def _predict_tonnage_per_district() -> dict:
    """Use the trained model to predict expected daily load per district (lbs → tons)."""
    if not predictor.model or not predictor.feature_order:
        return {}
    districts = [f"District {i}" for i in range(1, 11)]
    today = pd.Timestamp.now()
    rows = []
    for d in districts:
        max_cap_lbs = predictor.get_max_capacity_tons(d) / 0.0005
        rolling = max_cap_lbs * 0.4
        demo = demographic_features_for(d)
        district_encoded = predictor.district_mapping.get(d, 0)
        row = {
            'district_encoded': district_encoded,
            'day_of_week': today.dayofweek,
            'month': today.month,
            'is_weekend': 1 if today.dayofweek in [5, 6] else 0,
            'rolling_7_load_weight': rolling,
            **demo,
        }
        rows.append((d, row))

    X = pd.DataFrame([{k: r.get(k, 0.0) for k in predictor.feature_order} for _, r in rows])
    preds = predictor.model.predict(X)
    return {d: float(p) * 0.0005 for (d, _), p in zip(rows, preds)}
