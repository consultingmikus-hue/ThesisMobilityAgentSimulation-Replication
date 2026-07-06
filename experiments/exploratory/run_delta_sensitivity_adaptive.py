"""
Delta sensitivity sweep for Adaptive Governance Trigger C under Repeated Demand Shocks.
Compares different price damping intensities in the stress state:
- delta = 1.5 (Strong price damping)
- delta = 2.0 (Moderate price damping - baseline)
- delta = 3.0 (Weak price damping)

Uses 50 seeds, 500 ticks, repeated shocks, and Trigger C.
"""

import os
import sys
import csv
import itertools
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import numpy as np

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from src.model import ThesisSimulationModel
from src.metrics import summarize_run

def run_single_delta_simulation(params):
    delta_val, seed, steps = params
    
    # Configure repeated shocks scenario
    shock_mode = "Repeated Demand Shocks"
    pricing_enabled = True
    rebalancing_enabled = True
    forecasting_enabled = True
    governance_enabled = True
    
    # Initialize model
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=pricing_enabled,
        rebalancing_enabled=rebalancing_enabled,
        forecasting_enabled=forecasting_enabled,
        governance_enabled=governance_enabled,
        adaptive_governance=False,  # Custom trigger implemented manually below
        shock_mode=shock_mode
    )
    
    # Default unconstrained limits
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    triggered_ticks = 0
    
    for _ in range(steps):
        is_stressed = False
        if len(model.history) > 0:
            last_imb = model.history[-1]["system"]["spatial_imbalance"]
            
            def get_unmet_ratio(h):
                eff = h["system"]["total_effective_demand"]
                unmet = h["system"]["total_unmet_demand"]
                return unmet / eff if eff > 0 else 0.0
            
            # Trigger C: spatial_imbalance > 0.14 AND overload frequency condition
            # (unmet_demand_ratio >= 0.30 for >= 3 of the last 5 ticks)
            if last_imb > 0.14:
                recent_ticks = model.history[-5:]
                overload_count = sum(1 for h in recent_ticks if get_unmet_ratio(h) >= 0.30)
                is_stressed = (overload_count >= 3)
                
        if is_stressed:
            model.delta = delta_val
            model.theta = 0.0
            model.R_max = 999
            triggered_ticks += 1
        else:
            model.delta = 999.0
            model.theta = 0.0
            model.R_max = 999
            
        model.step()
        
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=f"adaptive_delta_{delta_val}_repeated_shocks",
        governance_setting=f"adaptive_delta_{delta_val}",
        seed=seed,
        imbalance_threshold=0.15,
        delta=None,
        theta=None,
        R_max=None
    )
    
    summary["delta_intervention"] = delta_val
    summary["adaptive_active_ratio"] = triggered_ticks / steps
    
    return summary

def main():
    steps = 500
    runs = 50
    seeds = list(range(1, runs + 1))
    deltas = [1.5, 2.0, 3.0]
    
    tasks = []
    for delta_val, seed in itertools.product(deltas, seeds):
        tasks.append((delta_val, seed, steps))
        
    print("=" * 80)
    print("       RUNNING ADAPTIVE DELTA SENSITIVITY SWEEP (TRIGGER C)")
    print("=" * 80)
    print(f"Total Simulation Runs Scheduled: {len(tasks)}")
    print(f"Seeds/Runs per delta:           {runs}")
    print(f"Ticks/Steps per run:            {steps}")
    print("-" * 80)
    
    num_workers = multiprocessing.cpu_count()
    print(f"Spawning ProcessPoolExecutor with {num_workers} parallel workers...")
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(run_single_delta_simulation, tasks))
        
    # Sort results
    def get_sort_key(res):
        return (res["delta_intervention"], res["seed"])
    results.sort(key=get_sort_key)
    
    # Save results to Outputs
    output_path = "/Users/mikusdev/thesis-simulation/outputs/exploratory/adaptive_delta_sensitivity.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            print(f"Sensitivity sweep results successfully saved to: {output_path}")
            
    # Print results table
    print("\n" + "="*120)
    print("                                   ADAPTIVE PRICE DELTA SENSITIVITY SWEEP TABLE")
    print("="*120)
    print(f"{'Pricing Constraint (Delta)':<28} | {'Active%':<8} | {'Unmet Dmd%':<10} | {'Rev/Veh':<8} | {'Price Vol':<9} | {'Osc Index':<9} | {'Imb Avg':<8} | {'Imb Pers':<8} | {'Overload%':<9} | {'Peak Unmet'}")
    print("-"*120)
    
    grouped = {}
    for res in results:
        key = res["delta_intervention"]
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(res)
        
    for d_val in deltas:
        rows = grouped.get(d_val, [])
        if not rows:
            continue
        avg_active = sum(r["adaptive_active_ratio"] for r in rows) / len(rows)
        avg_unmet = sum(r["unmet_demand_rate"] for r in rows) / len(rows)
        avg_rev = sum(r["revenue_per_vehicle"] for r in rows) / len(rows)
        avg_vol = sum(r["price_volatility"] for r in rows) / len(rows)
        avg_osc = sum(r["oscillation_index"] for r in rows) / len(rows)
        avg_imb = sum(r["spatial_imbalance"] for r in rows) / len(rows)
        avg_pers = sum(r["imbalance_persistence"] for r in rows) / len(rows)
        avg_over = sum(r["overload_frequency"] for r in rows) / len(rows)
        avg_peak = sum(r["peak_unmet_demand"] for r in rows) / len(rows)
        
        label = f"delta = {d_val} " + ("(Strong Damping)" if d_val == 1.5 else ("(Moderate - Base)" if d_val == 2.0 else "(Weak Damping)"))
        print(f"{label:<28} | {avg_active:<8.2%} | {avg_unmet:<10.2%} | {avg_rev:<8.2f} | {avg_vol:<9.3f} | {avg_osc:<9.3f} | {avg_imb:<8.4f} | {avg_pers:<8.3f} | {avg_over:<9.2%} | {avg_peak:<10.1f}")
    print("="*120)

if __name__ == "__main__":
    main()
