"""
Robustness experiment script comparing different demand shock profiles.
Runs batch simulations under abrupt shock (5.0x, no ramp) and strong ramp shock (6.0x, short ramp)
and compares them against baseline (4.0x, standard ramp) and no-shock controls.
"""

import os
import sys
import csv
import itertools
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from src.model import ThesisSimulationModel
from src.metrics import summarize_run

def make_abrupt_multiplier():
    def get_shock_multiplier(self):
        t = self.steps
        if 20 <= t <= 35:
            return 5.0
        return 1.0
    return get_shock_multiplier

def make_strong_ramp_multiplier():
    def get_shock_multiplier(self):
        t = self.steps
        if t <= 19:
            return 1.0
        elif t == 20:
            return 3.5  # midpoint between 1.0 and 6.0
        elif t <= 34:
            return 6.0  # peak
        elif t == 35:
            return 3.5  # midpoint between 6.0 and 1.0
        else:
            return 1.0
    return get_shock_multiplier

def run_single_robustness_run(params):
    shock_profile, scenario_type, seed, steps = params
    
    # Pricing, rebalancing, and forecasting are active for all interaction/governance runs
    pricing_enabled = True
    rebalancing_enabled = True
    forecasting_enabled = True
    
    if scenario_type == "interaction":
        governance_enabled = False
        delta, theta, R_max = None, None, None
        gov_setting = "none"
        scenario_name = "interaction" if shock_profile == "no_shock" else "interaction_demand_shock"
    else:
        governance_enabled = True
        delta, theta, R_max = 2.0, 2.0, 25
        gov_setting = "d2.0_t2.0_r25"
        scenario_name = "governance" if shock_profile == "no_shock" else "governance_demand_shock"
        
    shock_mode = "No Demand Shock" if shock_profile == "no_shock" else "Demand Shock"
    
    # Initialize model
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=pricing_enabled,
        rebalancing_enabled=rebalancing_enabled,
        forecasting_enabled=forecasting_enabled,
        governance_enabled=governance_enabled,
        shock_mode=shock_mode
    )
    
    # Apply moderate governance limits if active
    if governance_enabled:
        model.delta = delta
        model.theta = theta
        model.R_max = R_max
        
    # Monkey patch custom shock multipliers if applicable
    if shock_profile == "abrupt":
        model.get_shock_multiplier = make_abrupt_multiplier().__get__(model, ThesisSimulationModel)
    elif shock_profile == "strong_ramp":
        model.get_shock_multiplier = make_strong_ramp_multiplier().__get__(model, ThesisSimulationModel)
        
    # Run simulation
    for _ in range(steps):
        model.step()
        
    # Summarize run metrics
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=scenario_name,
        governance_setting=gov_setting,
        seed=seed,
        imbalance_threshold=0.15,
        delta=delta,
        theta=theta,
        R_max=R_max
    )
    
    # Add metadata fields
    summary["shock_profile"] = shock_profile
    summary["shock_multiplier"] = 1.0 if shock_profile == "no_shock" else (4.0 if shock_profile == "baseline" else (5.0 if shock_profile == "abrupt" else 6.0))
    summary["shock_type"] = "none" if shock_profile == "no_shock" else ("ramp" if shock_profile in ["baseline", "strong_ramp"] else "abrupt")
    
    return summary

def main():
    steps = 500
    runs = 10
    seeds = list(range(1, runs + 1))
    
    shock_profiles = ["no_shock", "baseline", "abrupt", "strong_ramp"]
    scenario_types = ["interaction", "governance"]
    
    tasks = []
    for shock_profile, scenario_type, seed in itertools.product(shock_profiles, scenario_types, seeds):
        tasks.append((shock_profile, scenario_type, seed, steps))
        
    print(f"Total robustness simulations to run: {len(tasks)}")
    
    num_workers = multiprocessing.cpu_count()
    print(f"Spawning ProcessPoolExecutor with {num_workers} parallel workers...")
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(run_single_robustness_run, tasks))
        
    # Sort results for deterministic output
    # Sort by shock_profile order, scenario_type order, seed
    profile_order = ["no_shock", "baseline", "abrupt", "strong_ramp"]
    scen_order = ["interaction", "governance"]
    
    def get_sort_key(res):
        p_idx = profile_order.index(res["shock_profile"])
        # Extract base scenario type: 'interaction' vs 'governance'
        s_type = "governance" if "governance" in res["scenario"] else "interaction"
        s_idx = scen_order.index(s_type)
        return (p_idx, s_idx, res["seed"])
        
    results.sort(key=get_sort_key)
    
    # Write to outputs/diagnostic_robustness_results.csv
    output_path = "/Users/mikusdev/thesis-simulation/outputs/exploratory/diagnostic_robustness_results.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            print(f"Robustness results successfully written to: {output_path}")

    # Print a summary report table
    print("\n" + "="*80)
    print("                    DIAGNOSTIC ROBUSTNESS REPORT SUMMARY")
    print("="*80)
    
    # Group results to compute averages
    grouped = {}
    for res in results:
        key = (res["shock_profile"], "governance" if "governance" in res["scenario"] else "interaction")
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(res)
        
    print(f"{'Shock Profile':<15} | {'Scenario':<11} | {'Unmet Dmd%':<10} | {'Rev/Veh':<8} | {'Price Vol':<9} | {'Osc Index':<9} | {'Imb Pers':<8} | {'Overload%':<9}")
    print("-"*80)
    for profile in profile_order:
        for scen in scen_order:
            rows = grouped.get((profile, scen), [])
            if not rows:
                continue
            avg_unmet = sum(r["unmet_demand_rate"] for r in rows) / len(rows)
            avg_rev = sum(r["revenue_per_vehicle"] for r in rows) / len(rows)
            avg_vol = sum(r["price_volatility"] for r in rows) / len(rows)
            avg_osc = sum(r["oscillation_index"] for r in rows) / len(rows)
            avg_pers = sum(r["imbalance_persistence"] for r in rows) / len(rows)
            avg_over = sum(r["overload_frequency"] for r in rows) / len(rows)
            
            print(f"{profile:<15} | {scen:<11} | {avg_unmet:<10.2%} | {avg_rev:<8.2f} | {avg_vol:<9.3f} | {avg_osc:<9.3f} | {avg_pers:<8.3f} | {avg_over:<9.2%}")
            
    print("="*80)

if __name__ == "__main__":
    main()
