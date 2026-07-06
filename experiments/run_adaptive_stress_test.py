"""
Exploratory stress test and parameter robustness sweep script for Adaptive Governance.
Runs the following experiments under final calibrated settings (N=80, 50% carryover):
1. Stress Test: Repeated shocks at 4.0x, 6.0x, and 8.0x peak multipliers comparing Interaction vs Adaptive Governance.
2. Parameter Robustness Sweep: OFAT checks for price damping delta (1.0, 2.0, 3.0), rebalancing threshold theta (0, 1, 2), and max rebalancing Rmax (999, 15, 10) under the 8.0x repeated shock.
"""

import os
import sys
import csv
import itertools
import multiprocessing as mp
import numpy as np

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.model import ThesisSimulationModel
from src.metrics import summarize_run

OUT_DIR = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "outputs", "final_exploratory_adaptive_governance")
TICKS = 500
SEEDS_COUNT = 50
SEEDS = list(range(1, SEEDS_COUNT + 1))

# Helper: calculate unmet ratio for a history entry
def get_unmet_ratio(h):
    eff = h["system"]["total_effective_demand"]
    unmet = h["system"]["total_unmet_demand"]
    return unmet / eff if eff > 0 else 0.0

# Trigger activation check: imbalance > 0.14 AND >= 3 of last 5 ticks in overload
def check_trigger_c(history, imbalance_threshold=0.14, L=3):
    if not history:
        return False
    last_imb = history[-1]["system"]["spatial_imbalance"]
    if last_imb > imbalance_threshold:
        recent_ticks = history[-5:]
        overload_count = sum(1 for h in recent_ticks if get_unmet_ratio(h) >= 0.30)
        return (overload_count >= L)
    return False

# Multiplier Generator
def make_repeated_multiplier(peak_val=4.0):
    def get_shock_multiplier(self):
        t = self.steps
        if t < 20:
            return 1.0
        t_rel = (t - 20) % 40  # cycle of 40 ticks
        if t_rel <= 2:
            return 1.0 + (peak_val - 1.0) * (t_rel + 1) / 3.0
        elif t_rel <= 13:
            return peak_val
        elif t_rel <= 16:
            return 1.0 + (peak_val - 1.0) * (16 - t_rel) / 3.0
        else:
            return 1.0
    return get_shock_multiplier

# Worker for Component 1: Main Stress Test
def run_stress_test_worker(params):
    regime, peak_multiplier, seed = params
    
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=True,
        rebalancing_enabled=True,
        forecasting_enabled=True,
        governance_enabled=(regime != "interaction"),
        shock_mode="Repeated Demand Shocks"
    )
    
    # Apply multiplier override
    model.get_shock_multiplier = make_repeated_multiplier(peak_multiplier).__get__(model, ThesisSimulationModel)
    
    # Initialize with unconstrained defaults
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    triggered_ticks = 0
    
    for _ in range(TICKS):
        is_stressed = False
        if regime == "adaptive_governance":
            is_stressed = check_trigger_c(model.history, 0.14, 3)
            if is_stressed:
                model.delta = 2.0
                model.theta = 0.0
                model.R_max = 999
            else:
                model.delta = 999.0
                model.theta = 0.0
                model.R_max = 999
                
        model.step()
        if is_stressed and regime == "adaptive_governance":
            triggered_ticks += 1
            
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=f"{regime}_p{peak_multiplier}",
        governance_setting="adaptive" if regime == "adaptive_governance" else "none",
        seed=seed
    )
    
    max_imbalance = max(h["system"]["spatial_imbalance"] for h in model.history)
    
    return {
        "regime": regime,
        "peak_multiplier": peak_multiplier,
        "seed": seed,
        "revenue_per_vehicle": summary["revenue_per_vehicle"],
        "service_rate": summary["service_rate"],
        "overload_frequency": summary["overload_frequency"],
        "avg_spatial_imbalance": summary["spatial_imbalance"],
        "max_spatial_imbalance": max_imbalance,
        "price_volatility": summary["price_volatility"],
        "price_oscillation_index": summary["oscillation_index"],
        "adaptive_active_ratio": triggered_ticks / TICKS if regime == "adaptive_governance" else 0.0
    }

# Worker for Component 2: OFAT Robustness Checks
def run_robustness_worker(params):
    delta_stress, theta_stress, rmax_stress, param_group, seed = params
    
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=True,
        rebalancing_enabled=True,
        forecasting_enabled=True,
        governance_enabled=True,
        shock_mode="Repeated Demand Shocks"
    )
    
    # 8.0x shock intensity
    model.get_shock_multiplier = make_repeated_multiplier(8.0).__get__(model, ThesisSimulationModel)
    
    # Default unconstrained limits
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    triggered_ticks = 0
    
    for _ in range(TICKS):
        # Activation check
        is_stressed = check_trigger_c(model.history, 0.14, 3)
        if is_stressed:
            model.delta = delta_stress
            model.theta = theta_stress
            model.R_max = rmax_stress
            triggered_ticks += 1
        else:
            model.delta = 999.0
            model.theta = 0.0
            model.R_max = 999
            
        model.step()
        
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=f"robustness_{param_group}_d{delta_stress}_t{theta_stress}_r{rmax_stress}",
        governance_setting=f"d{delta_stress}_t{theta_stress}_r{rmax_stress}",
        seed=seed
    )
    
    return {
        "param_group": param_group,
        "delta": delta_stress,
        "theta": theta_stress,
        "Rmax": rmax_stress,
        "seed": seed,
        "revenue_per_vehicle": summary["revenue_per_vehicle"],
        "service_rate": summary["service_rate"],
        "overload_frequency": summary["overload_frequency"],
        "spatial_imbalance": summary["spatial_imbalance"],
        "price_volatility": summary["price_volatility"],
        "price_oscillation_index": summary["oscillation_index"],
        "activation_frequency": triggered_ticks / TICKS
    }

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    num_workers = mp.cpu_count()
    print(f"Refocused pipeline starting. Using {num_workers} parallel workers.")
    
    # =========================================================================
    # COMPONENT 1: Main Stress Test (Interaction vs Adaptive Governance)
    # =========================================================================
    print("\n--- Running Component 1: Stress Test (4x, 6x, 8x) ---")
    stress_tasks = []
    regimes = ["interaction", "adaptive_governance"]
    multipliers = [4.0, 6.0, 8.0]
    
    for reg, mult in itertools.product(regimes, multipliers):
        for seed in SEEDS:
            stress_tasks.append((reg, mult, seed))
            
    with mp.Pool(processes=num_workers) as pool:
        stress_raw = pool.map(run_stress_test_worker, stress_tasks)
        
    # Aggregate stress test results
    grouped_stress = {}
    for r in stress_raw:
        key = (r["regime"], r["peak_multiplier"])
        if key not in grouped_stress:
            grouped_stress[key] = []
        grouped_stress[key].append(r)
        
    stress_summary = []
    for key, runs in grouped_stress.items():
        reg, mult = key
        stress_summary.append({
            "regime": reg,
            "peak_multiplier": mult,
            "revenue_per_vehicle": np.mean([x["revenue_per_vehicle"] for x in runs]),
            "service_rate": np.mean([x["service_rate"] for x in runs]),
            "overload_frequency": np.mean([x["overload_frequency"] for x in runs]),
            "avg_spatial_imbalance": np.mean([x["avg_spatial_imbalance"] for x in runs]),
            "max_spatial_imbalance": np.mean([x["max_spatial_imbalance"] for x in runs]),
            "price_volatility": np.mean([x["price_volatility"] for x in runs]),
            "price_oscillation_index": np.mean([x["price_oscillation_index"] for x in runs]),
            "activation_frequency": np.mean([x["adaptive_active_ratio"] for x in runs])
        })
        
    # Sort deterministically
    reg_order = ["interaction", "adaptive_governance"]
    stress_summary.sort(key=lambda x: (x["peak_multiplier"], reg_order.index(x["regime"])))
    
    # Save Stress Test CSV
    stress_csv_path = os.path.join(OUT_DIR, "adaptive_stress_test_results.csv")
    with open(stress_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=stress_summary[0].keys())
        writer.writeheader()
        writer.writerows(stress_summary)
    print(f"Stress test summary saved to: {stress_csv_path}")

    # =========================================================================
    # COMPONENT 2: One-Factor-At-A-Time Robustness Sweep
    # =========================================================================
    print("\n--- Running Component 2: OFAT Robustness Sweeps (8.0x) ---")
    
    # Base adaptive setting: delta = 2.0, theta = 0, R_max = 999
    # We define robustness runs:
    # 1. Delta sweep: delta in [1.0, 2.0, 3.0] with theta=0, Rmax=999
    # 2. Theta sweep: theta in [0, 1, 2] with delta=2.0, Rmax=999
    # 3. Rmax sweep: Rmax in [999, 15, 10] with delta=2.0, theta=0
    
    # We define configurations as (delta, theta, R_max, param_group)
    configs = []
    
    # delta check
    configs.append((1.0, 0, 999, "delta"))
    configs.append((2.0, 0, 999, "delta")) # shared baseline
    configs.append((3.0, 0, 999, "delta"))
    
    # theta check
    configs.append((2.0, 0, 999, "theta")) # shared baseline
    configs.append((2.0, 1, 999, "theta"))
    configs.append((2.0, 2, 999, "theta"))
    
    # Rmax check
    configs.append((2.0, 0, 999, "Rmax")) # shared baseline
    configs.append((2.0, 0, 15, "Rmax"))
    configs.append((2.0, 0, 10, "Rmax"))
    
    # Filter duplicates in the task generation to avoid redundant simulations
    seen_configs = set()
    rob_tasks = []
    
    for d, t, r, group in configs:
        config_key = (d, t, r, group)
        if config_key not in seen_configs:
            seen_configs.add(config_key)
            for seed in SEEDS:
                rob_tasks.append((d, t, r, group, seed))
                
    with mp.Pool(processes=num_workers) as pool:
        rob_raw = pool.map(run_robustness_worker, rob_tasks)
        
    # Group results
    grouped_rob = {}
    for r in rob_raw:
        key = (r["param_group"], r["delta"], r["theta"], r["Rmax"])
        if key not in grouped_rob:
            grouped_rob[key] = []
        grouped_rob[key].append(r)
        
    rob_summary = []
    for key, runs in grouped_rob.items():
        group, d_val, t_val, r_val = key
        rob_summary.append({
            "parameter_group": group,
            "delta": d_val,
            "theta": t_val,
            "Rmax": r_val,
            "service_rate": np.mean([x["service_rate"] for x in runs]),
            "overload_frequency": np.mean([x["overload_frequency"] for x in runs]),
            "revenue_per_vehicle": np.mean([x["revenue_per_vehicle"] for x in runs]),
            "price_volatility": np.mean([x["price_volatility"] for x in runs]),
            "spatial_imbalance": np.mean([x["spatial_imbalance"] for x in runs]),
            "activation_frequency": np.mean([x["activation_frequency"] for x in runs])
        })
        
    # Sort: group order, then parameter value
    def get_rob_sort_key(row):
        g_idx = ["delta", "theta", "Rmax"].index(row["parameter_group"])
        if row["parameter_group"] == "delta":
            val = row["delta"]
        elif row["parameter_group"] == "theta":
            val = row["theta"]
        else:
            val = -row["Rmax"] # reverse to put 999 first, then 15, then 10
        return (g_idx, val)
        
    rob_summary.sort(key=get_rob_sort_key)
    
    # Save Robustness CSV
    rob_csv_path = os.path.join(OUT_DIR, "adaptive_governance_parameter_robustness.csv")
    with open(rob_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rob_summary[0].keys())
        writer.writeheader()
        writer.writerows(rob_summary)
    print(f"Robustness sweep summary saved to: {rob_csv_path}")
    
    print("\n=========================================================================")
    print("               PIPELINE COMPLETION SUMMARY")
    print("=========================================================================")
    print(f"Output Directory:      {OUT_DIR}")
    print(f"1. Stress Test CSV:    {stress_csv_path}")
    print(f"2. Robustness CSV:     {rob_csv_path}")
    print("=========================================================================")

if __name__ == "__main__":
    main()
