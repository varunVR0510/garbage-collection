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


@router.get("/truck/{truck_id}")
def get_truck_route(truck_id: str, date: Optional[str] = Query(None)):
    """Per-truck multi-stop tour:
       Depot → Stop 1 → Stop 2 → Stop 3 → Landfill
    Stops are picked from:
      - Already-dispatched zone (mandatory if exists)
      - Truck's home district
      - Up to 2 nearest high/medium priority zones (capacity-aware)
    Stops are visited in nearest-neighbor order from depot.
    """
    from routes.fleet import _build_fleet
    from datetime import datetime as _dt
    when = _dt.fromisoformat(date) if date else _dt.now()

    fleet = _build_fleet(when)
    truck = next((t for t in fleet if t['id'] == truck_id), None)
    if not truck:
        return {"timeline": [], "summary": None, "error": "Truck not found"}

    import hashlib
    home_district = truck.get('district') or 'District 1'
    capacity = float(truck.get('capacity') or 12.0)
    coords = _coords()
    zones = {z['name']: z for z in get_zones_predictions(date=date)}
    home_centroid = coords.get(home_district, DEPOT_COORD)

    def _make_stop(zone_name: str, demand_t: float, reason_override: Optional[str] = None) -> dict:
        z = zones.get(zone_name, {})
        return {
            "name": zone_name,
            "level": z.get('level', 0),
            "status": z.get('status', 'low'),
            "reason": reason_override or z.get('reason', 'Routine pickup'),
            "demand": demand_t,
        }

    # Per-truck deterministic seed so each truck picks DIFFERENT neighbors
    truck_seed = int(hashlib.md5(truck_id.encode()).hexdigest()[:8], 16)

    candidates: list[dict] = []

    # 1. Already-dispatched zone (mandatory)
    for d in db.list_dispatches_today():
        if d['truck_id'] == truck_id:
            candidates.append(_make_stop(d['zone_name'], min(capacity * 0.55, 7.0), "Manually dispatched"))
            break

    # 2. Home district (always include)
    if not any(c['name'] == home_district for c in candidates):
        candidates.append(_make_stop(home_district, min(capacity * 0.50, 6.5)))

    # 3. Up to 2 high/medium priority zones (nearest first, capacity-permitting)
    priority_zones = [
        z for z in zones.values()
        if z['status'] in ('high', 'medium') and not any(c['name'] == z['name'] for c in candidates)
    ]
    priority_zones.sort(key=lambda z: haversine(home_centroid, coords.get(z['name'], DEPOT_COORD)))
    used_capacity = sum(c['demand'] for c in candidates)
    for z in priority_zones[:2]:
        extra = min(capacity * 0.25, 3.5)
        if used_capacity + extra > capacity * 0.95:
            break
        candidates.append(_make_stop(z['name'], extra))
        used_capacity += extra

    # 4. Fill the tour with neighbor districts the truck hasn't been routed through yet.
    #    Use a per-truck PRNG so different trucks of the same home pick DIFFERENT neighbors.
    import random as _random
    if len(candidates) < 3:
        existing_names = {c['name'] for c in candidates}
        neighbors = [
            (haversine(home_centroid, coords.get(n, DEPOT_COORD)), n)
            for n in [f"District {i}" for i in range(1, 11)]
            if n not in existing_names
        ]
        neighbors.sort()
        # Pool: 6 nearest. Shuffle it deterministically per truck and take 2.
        nearest_pool = [n for _, n in neighbors[:6]]
        rng = _random.Random(truck_seed)
        rng.shuffle(nearest_pool)

        pick_count = min(2, 3 - len(candidates))
        for chosen in nearest_pool[:pick_count]:
            extra = min(capacity * 0.22, 3.0)
            if used_capacity + extra > capacity * 0.95:
                break
            candidates.append(_make_stop(chosen, extra, "Adjacent district sweep"))
            used_capacity += extra

    # Order stops via nearest-neighbor starting at depot
    ordered: list[dict] = []
    remaining = list(candidates)
    cursor = DEPOT_COORD
    while remaining:
        remaining.sort(key=lambda c: haversine(cursor, coords.get(c['name'], DEPOT_COORD)))
        nxt = remaining.pop(0)
        ordered.append(nxt)
        cursor = coords.get(nxt['name'], DEPOT_COORD)

    # Build timeline
    timeline = [{
        "step": 1, "location": "Austin Central Depot (Start)",
        "type": "start", "note": f"Departure · truck {truck_id} · capacity {capacity:.0f} T",
        "priority": None,
    }]
    cursor = DEPOT_COORD
    total_km = 0.0
    cumulative_load = 0.0
    leg_kms: list[float] = []
    for i, c in enumerate(ordered):
        nxt = coords.get(c['name'], DEPOT_COORD)
        leg = haversine(cursor, nxt)
        total_km += leg
        leg_kms.append(round(leg, 1))
        cumulative_load += c['demand']
        level_part = f"Predicted Fill: {c['level']}% · " if c['level'] is not None else ""
        note = f"{level_part}Pickup ~{c['demand']:.1f} T → load {cumulative_load:.1f}/{capacity:.0f} T · {leg:.1f} km from prev"
        timeline.append({
            "step": i + 2,
            "location": c['name'],
            "type": c['status'],
            "note": note,
            "priority": (i + 1) if c['status'] in ('high', 'medium', 'dispatched') else None,
        })
        cursor = nxt

    return_km = haversine(cursor, DEPOT_COORD)
    total_km += return_km
    timeline.append({
        "step": len(timeline) + 1,
        "location": "TDS Landfill (End)",
        "type": "end",
        "note": f"Return · {return_km:.1f} km · final load {cumulative_load:.1f}/{capacity:.0f} T",
        "priority": None,
    })

    fuel_l = total_km * FUEL_LITRES_PER_KM
    stops = len(ordered)
    hours = total_km / 25.0 + stops * 0.5  # 25 km/h + 30 min/stop
    h = int(hours)
    m = int((hours - h) * 60)

    return {
        "timeline": timeline,
        "summary": {
            "distance": f"{total_km:.1f} km",
            "fuel": f"{fuel_l:.1f} L",
            "time": f"{h}h {m}m",
            "stops": stops,
            "legKms": leg_kms,
            "returnKm": round(return_km, 1),
            "targetDistricts": [c['name'] for c in ordered],
            "truckHomeDistrict": home_district,
            "scheduledToday": bool(truck.get('scheduledToday')),
            "currentLoad": truck.get('load'),
            "capacity": capacity,
            "tourLoad": round(cumulative_load, 1),
            "loadFraction": round(cumulative_load / capacity, 2) if capacity else 0,
        },
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
