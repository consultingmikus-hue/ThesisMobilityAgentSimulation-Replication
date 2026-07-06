"""
Batch Monte Carlo experiment runner for the thesis simulation.
Executes batch simulations across scenarios and governance parameters,
and exports results to summary and tick-level files in parallel.
"""

import os
import sys
# Ensure the project root directory is in sys.path to resolve src package imports correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import csv
import json
import argparse
import itertools
import datetime
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from src.model import ThesisSimulationModel
from src.config import TOTAL_VEHICLES
from src.scenarios import SCENARIOS, GOVERNANCE_GRID
from src.metrics import summarize_run


def save_tick_level_history(history, scenario, gov_setting, seed):
    """
    Save tick-level metrics for a single simulation run as a CSV file.
    """
    dir_path = "outputs/tick_history"
    os.makedirs(dir_path, exist_ok=True)
    
    file_name = f"{scenario}_{gov_setting}_{seed}.csv"
    file_path = os.path.join(dir_path, file_name)
    
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "tick", "service_rate", "fleet_utilization", "unmet_demand",
            "spatial_imbalance", "avg_price", "revenue", "idle_vehicles",
            "serving_vehicles", "rebalancing_vehicles", "shock_active"
        ])
        
        for h in history:
            t = h["step"]
            
            # Calculate if shock was active
            mode = h["system"].get("shock_mode", "No Demand Shock")
            if mode == "No Demand Shock":
                shock_active = 0
            elif mode == "Demand Shock":
                shock_active = 1 if (20 <= t <= 35) else 0
            elif mode == "Repeated Demand Shocks":
                shock_active = 1 if (t >= 20 and (t - 20) % 40 <= 15) else 0
            else:
                shock_active = 0
                
            # Calculate avg price of all zones
            zones = h["zones"]
            if zones:
                avg_price = sum(zones[z]["price"] for z in zones) / len(zones)
            else:
                avg_price = 0.0
                
            writer.writerow([
                t,
                h["system"]["service_rate"],
                h["system"]["fleet_utilization"],
                h["system"]["total_unmet_demand"],
                h["system"]["spatial_imbalance"],
                avg_price,
                h["system"]["revenue"],
                h["system"]["idle_vehicles"],
                h["system"]["serving_vehicles"],
                h["system"]["rebalancing_vehicles"],
                shock_active
            ])


def run_single_simulation(params):
    """
    Worker function to run a single simulation iteration.
    This function is self-contained and executed in a separate process.
    """
    (
        scen_name,
        scen_conf,
        delta,
        theta,
        R_max,
        seed,
        steps,
        imbalance_threshold,
        save_tick_history
    ) = params
    
    # Initialize model according to scenario parameters
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=scen_conf["pricing_enabled"],
        rebalancing_enabled=scen_conf["rebalancing_enabled"],
        forecasting_enabled=scen_conf["forecasting_enabled"],
        governance_enabled=scen_conf["governance_enabled"],
        shock_mode=scen_conf["shock_mode"]
    )
    
    # Apply custom governance thresholds if active
    if delta is not None:
        model.delta = delta
        model.theta = theta
        model.R_max = R_max
        
    # Run steps sequentially
    for _ in range(steps):
        model.step()
        
    gov_setting = f"d{delta}_t{theta}_r{R_max}" if delta is not None else "none"
    
    # Calculate run-level statistics
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=scen_name,
        governance_setting=gov_setting,
        seed=seed,
        imbalance_threshold=imbalance_threshold,
        delta=delta,
        theta=theta,
        R_max=R_max
    )
    
    # Save individual tick logs if requested
    if save_tick_history:
        save_tick_level_history(
            history=model.history,
            scenario=scen_name,
            gov_setting=gov_setting,
            seed=seed
        )
        
    return summary


def run_experiments(runs=50, steps=500, output_path="outputs/monte_carlo_run_summary.csv", save_tick_history=False, imbalance_threshold=None):
    """
    Orchestrate batch execution across scenarios and seeds in parallel.
    """
    print("=" * 60)
    print("       STARTING PARALLEL BATCH MONTE CARLO SIMULATIONS")
    print("=" * 60)
    print(f"Runs/Seeds per config: {runs}")
    print(f"Steps/Ticks per run:   {steps}")
    print(f"Output File:           {output_path}")
    print(f"Save Tick History:     {save_tick_history}")
    print("-" * 60)
    
    # Ensure imbalance threshold is set, defaulting to 0.15 if None
    if imbalance_threshold is None:
        thresholds_file = "outputs/final_thresholds.json"
        if os.path.exists(thresholds_file):
            print(f"Checking existing imbalance threshold file: {thresholds_file}")
            try:
                with open(thresholds_file, 'r') as f:
                    data = json.load(f)
                imbalance_threshold = data.get("imbalance_threshold", 0.15)
                print(f"Loaded imbalance threshold: {imbalance_threshold:.6f}")
            except Exception as e:
                print(f"Error loading threshold file: {e}. Falling back to 0.15...")
                imbalance_threshold = 0.15
        else:
            imbalance_threshold = 0.15
            # Save T = 0.15 to outputs/final_thresholds.json
            try:
                metadata_threshold = {
                    "imbalance_threshold": 0.15,
                    "percentile_rule": "Fixed thesis authoritative threshold (T = 0.15)",
                    "normalization": "spatial_imbalance divided by fleet_size",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                os.makedirs(os.path.dirname(thresholds_file), exist_ok=True)
                with open(thresholds_file, 'w') as f:
                    json.dump(metadata_threshold, f, indent=2)
            except Exception:
                pass
    else:
        print(f"Using provided imbalance-threshold: {imbalance_threshold}")
        
    # Generate list of tasks for parallel workers
    tasks = []
    for scen_name, scen_conf in SCENARIOS.items():
        # Determine governance configuration branches
        if scen_conf["governance_enabled"]:
            gov_combinations = list(itertools.product(
                GOVERNANCE_GRID["deltas"],
                GOVERNANCE_GRID["thetas"],
                GOVERNANCE_GRID["R_maxs"]
            ))
        else:
            gov_combinations = [(None, None, None)]
            
        for delta, theta, R_max in gov_combinations:
            for seed in range(1, runs + 1):
                tasks.append((
                    scen_name,
                    scen_conf,
                    delta,
                    theta,
                    R_max,
                    seed,
                    steps,
                    imbalance_threshold,
                    save_tick_history
                ))
                
    total_runs_executed = len(tasks)
    print(f"Total Simulation Runs Scheduled: {total_runs_executed}")
    
    num_workers = multiprocessing.cpu_count()
    print(f"Spawning ProcessPoolExecutor with {num_workers} parallel workers...")
    print("-" * 60)
    
    # Run tasks in parallel using process pool
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(run_single_simulation, tasks))
        
    # Sort results to guarantee 100% reproducible and deterministic CSV sorting
    # Sorted by: Scenario Index (in SCENARIOS), Governance delta, theta, R_max, and Seed
    scenarios_order = list(SCENARIOS.keys())
    
    def get_sort_key(res):
        scen = res["scenario"]
        scen_idx = scenarios_order.index(scen)
        g_delta = res["governance_delta"]
        g_theta = res["governance_theta"]
        g_rmax = res["governance_R_max"]
        seed = res["seed"]
        
        # Convert "none" strings to -1.0 for sorting baseline configurations
        d_val = float(g_delta) if g_delta != "none" else -1.0
        t_val = float(g_theta) if g_theta != "none" else -1.0
        r_val = float(g_rmax) if g_rmax != "none" else -1.0
        
        return (scen_idx, d_val, t_val, r_val, seed)
        
    results.sort(key=get_sort_key)
    
    # Export batch results to CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            
    # Export metadata config to JSON
    metadata = {
        "run_length": steps,
        "n_runs": runs,
        "seed_range": f"1 to {runs}",
        "scenario_definitions": SCENARIOS,
        "governance_grid": GOVERNANCE_GRID,
        "imbalance_threshold": imbalance_threshold
    }
    metadata_path = os.path.join(os.path.dirname(output_path), "monte_carlo_scenario_config.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    print("-" * 60)
    print("                      RUN SUMMARY")
    print("-" * 60)
    print(f"Total Simulation Runs Completed: {total_runs_executed}")
    print(f"Aggregated summary CSV saved to: {output_path}")
    print(f"Scenario configuration saved to: {metadata_path}")
    if save_tick_history:
        print(f"Tick histories saved under:      outputs/tick_history/")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Parallel Batch Monte Carlo Experiments")
    parser.add_argument("--runs", type=int, default=50, help="Number of runs/seeds per configuration (default: 50)")
    parser.add_argument("--steps", type=int, default=500, help="Length of each simulation run in ticks (default: 500)")
    parser.add_argument("--output", type=str, default="outputs/monte_carlo_run_summary.csv", help="Output path for summary CSV")
    parser.add_argument("--save-tick-history", action="store_true", help="Save tick-level CSV log for each individual run")
    parser.add_argument("--imbalance-threshold", type=float, default=0.15, help="Imbalance threshold for persistence (default: 0.15)")
    
    args = parser.parse_args()
    
    run_experiments(
        runs=args.runs,
        steps=args.steps,
        output_path=args.output,
        save_tick_history=args.save_tick_history,
        imbalance_threshold=args.imbalance_threshold
    )
