from fastapi import APIRouter
from datetime import datetime
from ml.predictor import predictor
import json
import os

router = APIRouter()

@router.get("/zones")
def get_zones_predictions():
    date_now = datetime.now()
    
    # Generate response for the 10 real districts we trained on
    response = []
    
    districts = [f"District {i}" for i in range(1, 11)]
    
    for i, district in enumerate(districts):
        # We need a rolling weight. In a real production system, this comes from DB.
        # Here we will just use half the max capacity as the current rolling baseline 
        # to ensure it varies based on the real max capacity of that district.
        max_cap = predictor.get_max_capacity_tons(district) / 0.0005
        # We take a historically reasonable rolling average
        rolling_weight = max_cap * 0.4 
        
        predicted_tons = predictor.predict_district_waste(district, date_now, rolling_weight)
        max_capacity_tons = predictor.get_max_capacity_tons(district)
        
        level = 0
        if max_capacity_tons > 0:
            level = min(int((predicted_tons / max_capacity_tons) * 100), 100)
            
        status = "critical" if level >= 85 else ("medium" if level >= 50 else "low")
        
        # Real insight based solely on data
        reason = f"Predicted load is {predicted_tons:.1f}T vs Historical Max {max_capacity_tons:.1f}T"
        
        response.append({
            "id": f"D{i+1}",
            "name": district,
            "zoneNo": i+1,
            "level": level,
            "status": status,
            "reason": reason
        })
        
    return response
