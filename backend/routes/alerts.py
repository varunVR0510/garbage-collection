from fastapi import APIRouter, Query
from typing import Optional
from routes.predictions import get_zones_predictions

router = APIRouter()

@router.get("/alerts")
def get_alerts(date: Optional[str] = Query(None)):
    zones = get_zones_predictions(date=date)
    
    alerts = []
    alert_id = 1
    
    for z in zones:
        if z['status'] == 'high':
            alerts.append({
                "id": alert_id,
                "icon": "🚨",
                "severity": "high",
                "title": f"Overflow Risk: {z['name']}",
                "message": f"Fill level is at {z['level']}%. Immediate collection recommended based on XGBoost prediction.",
                "time": "Just now",
            })
            alert_id += 1
        elif z['status'] == 'medium':
            alerts.append({
                "id": alert_id,
                "icon": "⚠️",
                "severity": "warning",
                "title": f"Monitoring: {z['name']}",
                "message": f"Fill level reaching {z['level']}%. Schedule upcoming pickup.",
                "time": "Just now",
            })
            alert_id += 1
            
    # Add a system alert
    alerts.append({
        "id": alert_id,
        "icon": "✅",
        "severity": "success",
        "title": "Data Pipeline Active",
        "message": "Dashboard powered 100% by Austin Open Data and XGBoost engine.",
        "time": "System",
    })
    
    return alerts
