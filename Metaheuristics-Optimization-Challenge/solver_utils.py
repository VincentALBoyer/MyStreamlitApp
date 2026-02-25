import math

def calculate_knapsack_stats(selected_ids, items, capacity):
    """
    selected_ids: set of item ids
    items: list of {"id": i, "w": weight, "v": value}
    capacity: total capacity
    """
    total_weight = 0
    total_value = 0
    for item in items:
        if item["id"] in selected_ids:
            total_weight += item["w"]
            total_value += item["v"]
    
    is_feasible = total_weight <= capacity
    remaining = capacity - total_weight
    return {
        "weight": total_weight,
        "value": total_value,
        "is_feasible": is_feasible,
        "remaining": remaining
    }

def euclidean_distance(c1, c2):
    return math.sqrt((c1["x"] - c2["x"])**2 + (c1["y"] - c2["y"])**2)

def calculate_p_median_stats(facility_ids, cities):
    """
    facility_ids: set of city ids selected as facilities
    cities: list of {"id": i, "x": x, "y": y}
    """
    if not facility_ids:
        return {
            "total_distance": float('inf'),
            "assignments": {},
            "nearest_distances": {c["id"]: float('inf') for c in cities}
        }
    
    facilities = [c for c in cities if c["id"] in facility_ids]
    total_distance = 0
    assignments = {}
    nearest_distances = {}
    
    for city in cities:
        min_dist = float('inf')
        assigned_facility = None
        for fac in facilities:
            d = euclidean_distance(city, fac)
            if d < min_dist:
                min_dist = d
                assigned_facility = fac["id"]
        
        total_distance += min_dist
        assignments[city["id"]] = assigned_facility
        nearest_distances[city["id"]] = min_dist
        
    return {
        "total_distance": total_distance,
        "assignments": assignments,
        "nearest_distances": nearest_distances
    }
