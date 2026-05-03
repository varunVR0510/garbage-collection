from fastapi import APIRouter
import pandas as pd
import os

router = APIRouter()

def get_real_fleet():
    csv_path = r"..\cleaned_waste_data.csv"
    if not os.path.exists(csv_path):
        return []
    
    df = pd.read_csv(csv_path, usecols=['Route Number', 'Route Type', 'Load Weight'])
    df = df.dropna(subset=['Route Number', 'Route Type', 'Load Weight'])
    
    top_routes = df['Route Number'].value_counts().head(6).index.tolist()
    
    fleet = []
    for i, route in enumerate(top_routes):
        route_type = df[df['Route Number'] == route]['Route Type'].iloc[0]
        max_load = df[df['Route Number'] == route]['Load Weight'].max() * 0.0005
        current_load = df[df['Route Number'] == route]['Load Weight'].mean() * 0.0005
        
        status = "idle" if current_load < 1 else ("returning" if current_load > max_load * 0.8 else "on-route")
        
        fleet.append({
            "id": f"RT-{route}",
            "type": str(route_type),
            "capacity": round(max_load, 1) if pd.notnull(max_load) else 10.0,
            "load": round(current_load, 1) if pd.notnull(current_load) else 0.0,
            "status": status,
            "route": f"Austin Route {route}"
        })
    return fleet

@router.get("/status")
def get_fleet_status():
    fleet = get_real_fleet()
    if not fleet:
        return []
    return fleet

@router.get("/assignments")
def get_fleet_assignments():
    fleet = get_real_fleet()
    assignments = []
    for f in fleet:
        assignments.append({
            "vehicleId": f['id'],
            "assignedZone": f['route'] if f['status'] != 'idle' else "Unassigned",
            "status": f['status']
        })
    return assignments

@router.get("/utilization")
def get_fleet_utilization():
    fleet = get_real_fleet()
    if not fleet:
        return {"utilization": 0}
        
    total_cap = sum(f['capacity'] for f in fleet)
    total_load = sum(f['load'] for f in fleet)
    
    pct = 0
    if total_cap > 0:
        pct = (total_load / total_cap) * 100
        
    return {
        "utilizationPercentage": round(pct, 1),
        "activeVehicles": sum(1 for f in fleet if f['status'] != 'idle'),
        "totalVehicles": len(fleet)
    }
