from fastapi import APIRouter, Query
from datetime import datetime
from typing import Optional
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import math
from routes.predictions import get_zones_predictions
from routes.fleet import get_real_fleet
from ml.route_geometry import all_district_centroids
import db


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if date_str:
        try:
            return datetime.fromisoformat(date_str)
        except Exception:
            pass
    return None

router = APIRouter()

FUEL_LITRES_PER_KM = 0.35  # ~35L/100km for a garbage truck
COST_PER_LITRE = 95.0      # demo cost — easy to swap

DEPOT_COORD = (30.2672, -97.7431)  # Austin Resource Recovery, downtown

def _coords():
    """Live district centroids from austin_routes_2015.xlsx (computed via KMeans on
    polygon centroids). Falls back to Depot if a district is missing."""
    centroids = all_district_centroids()
    coords = {'Depot': DEPOT_COORD}
    coords.update(centroids)
    return coords

def haversine(coord1, coord2):
    R = 6371  # km
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def create_data_model(date_str: Optional[str] = None):
    """Stores the data for the routing problem."""
    data = {}
    coords = _coords()

    all_zones = get_zones_predictions(date=date_str)
    priority = [z for z in all_zones if z['status'] in ['high', 'medium']]
    if priority:
        priority.sort(key=lambda x: x['level'], reverse=True)
        zones = priority[:8]
    else:
        all_zones.sort(key=lambda x: x['level'], reverse=True)
        zones = all_zones[:8]
    
    # Nodes: 0 is Depot, 1..N are zones
    locations = ['Depot'] + [z['name'] for z in zones]
    data['locations'] = locations
    data['zones_data'] = [{'name': 'Depot', 'level': 0, 'status': 'start'}] + zones
    
    num_locations = len(locations)
    
    # Distance matrix (in meters to avoid floats in OR-Tools)
    distance_matrix = []
    for i in range(num_locations):
        row = []
        for j in range(num_locations):
            dist_km = haversine(coords.get(locations[i], coords['Depot']), coords.get(locations[j], coords['Depot']))
            row.append(int(dist_km * 1000))
        distance_matrix.append(row)
    data['distance_matrix'] = distance_matrix
    
    # Demands (approximate tons)
    demands = [0]
    for z in zones:
        # A simple estimation: level * 0.1 tons (10 tons if 100%)
        demands.append(int(z['level'] * 0.1))
    data['demands'] = demands
    
    # Vehicles from Fleet API
    when = _parse_date(date_str)
    fleet = get_real_fleet(when=when)
    active_trucks = [t for t in fleet if t['status'] != 'idle']
    if not active_trucks:
        # Fallback to 2 generic trucks if none active
        active_trucks = [{'id': 'TRK-A', 'capacity': 12}, {'id': 'TRK-B', 'capacity': 12}]
    else:
        active_trucks = active_trucks[:3] # Limit to 3 for VRP
        
    data['vehicle_capacities'] = [int(t['capacity']) for t in active_trucks]
    data['num_vehicles'] = len(data['vehicle_capacities'])
    data['depot'] = 0
    
    return data

def solve_vrp(date_str: Optional[str] = None):
    data = create_data_model(date_str)
    
    if data['num_vehicles'] == 0 or len(data['locations']) <= 1:
        return None
        
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    
    # Solve
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        return data, manager, routing, solution
    return None

@router.get("/optimized")
def get_optimized_route(date: Optional[str] = Query(None)):
    result = solve_vrp(date)
    if not result:
        return []
        
    data, manager, routing, solution = result
    
    # Get the best route (longest one) to show in the UI timeline
    best_route_dist = -1
    best_route_idx = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        route_distance = 0
        while not routing.IsEnd(index):
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        if route_distance > best_route_dist:
            best_route_dist = route_distance
            best_route_idx = vehicle_id
            
    # Reconstruct timeline for best route
    timeline = []
    index = routing.Start(best_route_idx)
    step_num = 1
    
    while not routing.IsEnd(index):
        node_index = manager.IndexToNode(index)
        zone_data = data['zones_data'][node_index]
        
        if node_index == 0:
            timeline.append({
                "step": step_num, "location": "Austin Central Depot (Start)", 
                "type": "start", "note": "Departure", "priority": None
            })
        else:
            timeline.append({
                "step": step_num, 
                "location": zone_data['name'], 
                "type": zone_data['status'], 
                "note": f"Predicted Fill: {zone_data['level']}% · Priority Pickup", 
                "priority": step_num - 1
            })
            
        step_num += 1
        index = solution.Value(routing.NextVar(index))
        
    timeline.append({
        "step": step_num, "location": "TDS Landfill (End)", "type": "end", "note": "ETA Arrival", "priority": None
    })
    
    return timeline

def _naive_distance_km(data) -> float:
    """Sequential depot -> all stops -> depot, with no optimization."""
    matrix = data['distance_matrix']
    if len(matrix) <= 1:
        return 0.0
    total_m = 0
    prev = 0  # depot
    for i in range(1, len(matrix)):
        total_m += matrix[prev][i]
        prev = i
    total_m += matrix[prev][0]  # back to depot
    return total_m / 1000.0


def compute_route_summary(date_str: Optional[str] = None):
    """Compute optimized + naive baseline. Returns numeric dict (or None)."""
    all_zones_now = get_zones_predictions(date=date_str)
    total_zones = len(all_zones_now)
    must_collect = sum(1 for z in all_zones_now if z['status'] in ['high', 'medium'])
    trips_avoided = max(total_zones - must_collect, 0)

    result = solve_vrp(date_str)
    if not result:
        return {
            "total_km": 0.0, "naive_km": 0.0,
            "fuel_l": 0.0, "naive_fuel_l": 0.0,
            "hours": 0.0,
            "saved_km": 0.0, "saved_fuel_l": 0.0, "saved_pct": 0.0,
            "stops": 0,
            "total_zones": total_zones,
            "must_collect": must_collect,
            "trips_avoided": trips_avoided,
            "_no_solution": True,
        }

    data, manager, routing, solution = result
    total_distance_m = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        route_distance = 0
        while not routing.IsEnd(index):
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        total_distance_m += route_distance

    total_km = total_distance_m / 1000.0
    naive_km = _naive_distance_km(data)
    fuel_l = total_km * FUEL_LITRES_PER_KM
    naive_fuel_l = naive_km * FUEL_LITRES_PER_KM
    stops = max(len(data['locations']) - 1, 0)
    hours = (total_km / 25.0) + stops * 0.5  # 25 km/h + 30 min/stop

    saved_km = max(naive_km - total_km, 0.0)
    saved_fuel_l = max(naive_fuel_l - fuel_l, 0.0)
    saved_pct = (saved_km / naive_km * 100.0) if naive_km > 0 else 0.0

    return {
        "total_km": total_km,
        "naive_km": naive_km,
        "fuel_l": fuel_l,
        "naive_fuel_l": naive_fuel_l,
        "hours": hours,
        "saved_km": saved_km,
        "saved_fuel_l": saved_fuel_l,
        "saved_pct": saved_pct,
        "stops": stops,
        "total_zones": total_zones,
        "must_collect": must_collect,
        "trips_avoided": trips_avoided,
    }


@router.get("/summary")
def get_route_summary(date: Optional[str] = Query(None)):
    s = compute_route_summary(date)
    h = int(s["hours"])
    m = int((s["hours"] - h) * 60)

    if not s.get("_no_solution"):
        try:
            db.log_route_run(s["total_km"], s["naive_km"], s["fuel_l"], s["naive_fuel_l"])
        except Exception:
            pass

    return {
        "distance": f"{s['total_km']:.1f} km",
        "fuel": f"{s['fuel_l']:.1f} L",
        "time": f"{h}h {m}m",
        "savedKm": round(s["saved_km"], 1),
        "savedFuelL": round(s["saved_fuel_l"], 1),
        "savedPct": round(s["saved_pct"], 1),
        "tripsAvoided": s["trips_avoided"],
        "totalZones": s["total_zones"],
        "mustCollect": s["must_collect"],
    }
