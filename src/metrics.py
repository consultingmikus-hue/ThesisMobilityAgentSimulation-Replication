"""
Metrics utility module for the thesis simulation.
Calculates run-level summary statistics from raw step-by-step histories.
"""

import statistics

def summarize_run(history, fleet_size, scenario=None, governance_setting=None, seed=None, imbalance_threshold=None, delta=None, theta=None, R_max=None):
    """
    Summarize a simulation run history into a single flat dictionary of aggregate metrics.
    
    Args:
        history: List of step-level metrics dictionaries from the simulation model.
        fleet_size: Total number of vehicles in the simulation.
        scenario: Name of the active scenario.
        governance_setting: Name of the active governance configuration.
        seed: Random seed used for the run.
        imbalance_threshold: Spatial imbalance threshold for persistence.
        
    Returns:
        dict: flat dictionary of run-level summary metrics.
    """
    if not history:
        return {}
        
    run_length = len(history)
    
    # Calculate step-level average zone prices
    avg_prices = []
    for h in history:
        zones = h["zones"]
        if zones:
            avg_price_t = sum(zones[z]["price"] for z in zones) / len(zones)
        else:
            avg_price_t = 0.0
        avg_prices.append(avg_price_t)
        
    # Calculate target aggregates
    cumulative_revenue = sum(h["system"]["revenue"] for h in history)
    revenue_per_vehicle = cumulative_revenue / fleet_size if fleet_size > 0 else 0.0
    
    fleet_utilization = statistics.mean(h["system"]["fleet_utilization"] for h in history)
    
    total_unmet = sum(h["system"]["total_unmet_demand"] for h in history)
    total_eff = sum(h["system"]["total_effective_demand"] for h in history)
    unmet_demand_rate = total_unmet / total_eff if total_eff > 0 else 0.0
    
    avg_unmet_demand = statistics.mean(h["system"]["total_unmet_demand"] for h in history)
    peak_unmet_demand = max(h["system"]["total_unmet_demand"] for h in history)
    spatial_imbalance = statistics.mean(h["system"]["spatial_imbalance"] for h in history)
    
    # Use the authoritative fixed thesis threshold (T = 0.15) if not provided
    if imbalance_threshold is None:
        imbalance_threshold = 0.15
            
    imbalance_persistence = sum(1 for h in history if h["system"]["spatial_imbalance"] > imbalance_threshold) / run_length
    
    price_volatility = statistics.pstdev(avg_prices) if len(avg_prices) > 1 else 0.0
    
    # Calculate overload frequency using unmet_ratio
    overload_ticks = 0
    for h in history:
        eff = h["system"]["total_effective_demand"]
        unmet = h["system"]["total_unmet_demand"]
        ratio = unmet / eff if eff > 0 else 0.0
        if ratio >= 0.30:
            overload_ticks += 1
            
    overload_frequency = overload_ticks / run_length
    
    low_idle_ticks = sum(1 for h in history if h["system"]["idle_vehicles"] < 0.10 * fleet_size)
    low_idle_frequency = low_idle_ticks / run_length
    
    # Calculate oscillation index based on directional reversals of average prices
    diffs = [avg_prices[i] - avg_prices[i-1] for i in range(1, len(avg_prices))]
    # Filter out zero differences (ignoring flat periods)
    nonzero_diffs = [d for d in diffs if abs(d) > 1e-9]
    
    if len(nonzero_diffs) >= 2:
        reversals = 0
        for i in range(1, len(nonzero_diffs)):
            if nonzero_diffs[i] * nonzero_diffs[i-1] < 0:
                reversals += 1
        oscillation_index = reversals / (len(nonzero_diffs) - 1)
    else:
        oscillation_index = 0.0
        
    # Calculate vehicle concentration (average standard deviation of idle vehicles across zones)
    zones = []
    if history and "zones" in history[0] and history[0]["zones"]:
        zones = list(history[0]["zones"].keys())
        
    vc_list = []
    if zones:
        for h in history:
            if "zones" in h and h["zones"]:
                # Check if all zones have idle_vehicles
                if all(z in h["zones"] and "idle_vehicles" in h["zones"][z] for z in zones):
                    vc_list.append(statistics.pstdev(h["zones"][z]["idle_vehicles"] for z in zones))
    vehicle_concentration = statistics.mean(vc_list) if vc_list else 0.0
    # Additional diagnostic metrics for Monte Carlo calibration
    trips_served = sum(h["system"].get("total_served_demand", 0) for h in history)
    avg_price = statistics.mean(avg_prices) if avg_prices else 0.0
    avg_idle_vehicles = statistics.mean(h["system"].get("idle_vehicles", 0) for h in history)
    avg_price_C = statistics.mean(h["zones"]["C"].get("price", 0) for h in history) if history and "zones" in history[0] and "C" in history[0]["zones"] else 0.0
    avg_price_A = statistics.mean(h["zones"]["A"].get("price", 0) for h in history) if history and "zones" in history[0] and "A" in history[0]["zones"] else 0.0
    avg_price_R1 = statistics.mean(h["zones"]["R1"].get("price", 0) for h in history) if history and "zones" in history[0] and "R1" in history[0]["zones"] else 0.0

    return {
        "scenario": scenario if scenario else "unknown",
        "governance_setting": governance_setting if governance_setting else "none",
        "governance_delta": delta if delta is not None else "none",
        "governance_theta": theta if theta is not None else "none",
        "governance_R_max": R_max if R_max is not None else "none",
        "seed": seed if seed is not None else -1,
        "run_length": run_length,
        "cumulative_revenue": cumulative_revenue,
        "revenue_per_vehicle": revenue_per_vehicle,
        "fleet_utilization": fleet_utilization,
        "unmet_demand_rate": unmet_demand_rate,
        "service_rate": 1.0 - unmet_demand_rate,
        "avg_unmet_demand": avg_unmet_demand,
        "price_volatility": price_volatility,
        "spatial_imbalance": spatial_imbalance,
        "demand_supply_mismatch": spatial_imbalance,
        "imbalance_persistence": imbalance_persistence,
        "persistence_demand_supply_mismatch": imbalance_persistence,
        "vehicle_concentration": vehicle_concentration,
        "oscillation_index": oscillation_index,
        "overload_frequency": overload_frequency,
        "low_idle_frequency": low_idle_frequency,
        "peak_unmet_demand": peak_unmet_demand,
        "trips_served": trips_served,
        "avg_price": avg_price,
        "avg_idle_vehicles": avg_idle_vehicles,
        "avg_price_C": avg_price_C,
        "avg_price_A": avg_price_A,
        "avg_price_R1": avg_price_R1
    }
