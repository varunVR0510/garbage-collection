from fastapi import APIRouter
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import math
from routes.predictions import get_zones_predictions
from routes.fleet import get_real_fleet

router = APIRouter()

# Pseudo-coordinates for Austin 10 Districts & Depot
COORDS = {
    'Depot': (30.2672, -97.7431),
    'District 1': (30.2800, -97.7300),
    'District 2': (30.2200, -97.6000),
    'District 3': (30.2500, -97.5500),
    'District 4': (30.1000, -97.7500),
    'District 5': (30.1100, -97.7600),
    'District 6': (30.3400, -97.7000),
    'District 7': (30.2700, -97.7500),
    'District 8': (30.3500, -97.8500),
    'District 9': (30.3000, -97.7700),
    'District 10': (30.2600, -97.7700)
}

def haversine(coord1, coord2):
    R = 6371  # km
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def create_data_model():
    """Stores the data for the routing problem."""
    data = {}
    
    # Get active zones (Critical or Medium) from prediction API
    all_zones = get_zones_predictions()
    zones = [z for z in all_zones if z['status'] in ['critical', 'medium']]
    # Limit to top 8 to ensure VRP solves quickly
    zones.sort(key=lambda x: x['level'], reverse=True)
    zones = zones[:8]
    
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
            dist_km = haversine(COORDS.get(locations[i], COORDS['Depot']), COORDS.get(locations[j], COORDS['Depot']))
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
    fleet = get_real_fleet()
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

def solve_vrp():
    data = create_data_model()
    
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
def get_optimized_route():
    result = solve_vrp()
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

@router.get("/summary")
def get_route_summary():
    result = solve_vrp()
    if not result:
        return {"distance": "0 km", "fuel": "0.0 L", "time": "0h 0m"}
        
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
    fuel_l = total_km * 0.35 # Approx 35L / 100km for garbage truck
    hours = total_km / 25.0 + (len(data['locations']) - 1) * 0.5 # 25km/h avg speed + 30 min per stop
    
    h = int(hours)
    m = int((hours - h) * 60)
    
    return {
        "distance": f"{total_km:.1f} km",
        "fuel": f"{fuel_l:.1f} L",
        "time": f"{h}h {m}m"
    }
