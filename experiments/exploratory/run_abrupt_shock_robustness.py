"""
Robustness experiment runner comparing the abrupt 1-tick ramp demand shock
against the baseline 3-tick ramp demand shock design (4.0x peak multiplier).
Evaluates whether adaptive governance B (trigger 0.14) starts triggering during
the shock itself or remains active primarily during post-shock recovery.
"""

import os
import sys
import csv
import itertools
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import numpy as np

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from src.model import ThesisSimulationModel
from src.metrics import summarize_run

def make_abrupt_single_multiplier(peak_val=4.0):
    def get_shock_multiplier(self):
        t = self.steps
        if t <= 19:
            return 1.0
        elif t == 20:
            return 1.0 + (peak_val - 1.0) * 0.5  # 2.5
        elif t <= 34:
            return peak_val  # 4.0
        elif t == 35:
            return 1.0 + (peak_val - 1.0) * 0.5  # 2.5
        else:
            return 1.0
    return get_shock_multiplier

def make_abrupt_repeated_multiplier(peak_val=4.0):
    def get_shock_multiplier(self):
        t = self.steps
        if t < 20:
            return 1.0
        t_rel = (t - 20) % 40
        if t_rel == 0:
            return 1.0 + (peak_val - 1.0) * 0.5  # 2.5
        elif t_rel <= 14:
            return peak_val  # 4.0
        elif t_rel == 15:
            return 1.0 + (peak_val - 1.0) * 0.5  # 2.5
        else:
            return 1.0
    return get_shock_multiplier

def get_contiguous_blocks(ticks_list):
    if not ticks_list:
        return []
    sorted_ticks = sorted(ticks_list)
    blocks = []
    current_block = [sorted_ticks[0]]
    for t in sorted_ticks[1:]:
        if t == current_block[-1] + 1:
            current_block.append(t)
        else:
            blocks.append(current_block)
            current_block = [t]
    blocks.append(current_block)
    return blocks

def run_single_robustness_simulation(params):
    regime, env_name, seed, steps, shock_design = params
    
    # Configure baseline scenario settings
    pricing_enabled = True
    rebalancing_enabled = True
    forecasting_enabled = True
    
    if env_name == "baseline_shock":
        shock_mode = "Demand Shock"
    else:
        shock_mode = "Repeated Demand Shocks"
        
    if regime == "interaction":
        governance_enabled = False
        adaptive_governance = False
        adaptive_threshold = 0.14
        delta, theta, R_max = None, None, None
        gov_setting = "none"
    else:
        governance_enabled = True
        adaptive_governance = True
        adaptive_threshold = 0.14
        delta, theta, R_max = 999.0, 0.0, 999
        gov_setting = "adaptive_B_t0.14"
        
    # Initialize model
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=pricing_enabled,
        rebalancing_enabled=rebalancing_enabled,
        forecasting_enabled=forecasting_enabled,
        governance_enabled=governance_enabled,
        adaptive_governance=adaptive_governance,
        adaptive_governance_threshold=adaptive_threshold,
        shock_mode=shock_mode
    )
    
    if governance_enabled:
        model.delta = delta
        model.theta = theta
        model.R_max = R_max
        
    # Override shock multiplier if using the abrupt (1-tick ramp) design
    if shock_design == "abrupt_1tick":
        if env_name == "baseline_shock":
            model.get_shock_multiplier = make_abrupt_single_multiplier(4.0).__get__(model, ThesisSimulationModel)
        else:
            model.get_shock_multiplier = make_abrupt_repeated_multiplier(4.0).__get__(model, ThesisSimulationModel)
            
    # Run simulation
    triggered_ticks = []
    for _ in range(steps):
        model.step()
        current_tick = model.steps - 1
        # Check if stress state was active during the step that just completed
        if adaptive_governance and model.delta == 2.0:
            triggered_ticks.append(current_tick)
            
    # Calculate summary metrics
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=f"{regime}_{env_name}_{shock_design}",
        governance_setting=gov_setting,
        seed=seed,
        imbalance_threshold=0.15,
        delta=delta if not adaptive_governance else None,
        theta=theta if not adaptive_governance else None,
        R_max=R_max if not adaptive_governance else None
    )
    
    # Calculate block lengths
    blocks = get_contiguous_blocks(triggered_ticks)
    block_lengths = [len(b) for b in blocks]
    
    summary["regime"] = regime
    summary["environment"] = env_name
    summary["shock_design"] = shock_design
    summary["adaptive_active_ratio"] = len(triggered_ticks) / steps if adaptive_governance else 0.0
    summary["triggered_ticks_str"] = ",".join(map(str, triggered_ticks))
    summary["block_lengths_str"] = ",".join(map(str, block_lengths))
    summary["mean_block_length"] = np.mean(block_lengths) if block_lengths else 0.0
    summary["max_block_length"] = np.max(block_lengths) if block_lengths else 0
    
    return summary

def main():
    steps = 500
    runs = 50
    seeds = list(range(1, runs + 1))
    
    regimes = ["interaction", "adaptive_B"]
    environments = ["baseline_shock", "repeated_shocks"]
    shock_designs = ["baseline_3tick", "abrupt_1tick"]
    
    tasks = []
    # Build task matrix
    for regime, env_name, seed, shock_design in itertools.product(regimes, environments, seeds, shock_designs):
        tasks.append((regime, env_name, seed, steps, shock_design))
        
    print("=" * 80)
    print("       RUNNING SHOCK PROFILE ROBUSTNESS EXPERIMENTS")
    print("=" * 80)
    print(f"Total Simulation Runs Scheduled: {len(tasks)} (200 runs for 1-tick, 200 runs for 3-tick)")
    print(f"Seeds/Runs per config:          {runs}")
    print(f"Ticks/Steps per run:            {steps}")
    print("-" * 80)
    
    num_workers = multiprocessing.cpu_count()
    print(f"Spawning ProcessPoolExecutor with {num_workers} parallel workers...")
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(run_single_robustness_simulation, tasks))
        
    # Sort results
    def get_sort_key(res):
        sd_idx = shock_designs.index(res["shock_design"])
        e_idx = environments.index(res["environment"])
        r_idx = regimes.index(res["regime"])
        return (sd_idx, e_idx, r_idx, res["seed"])
    results.sort(key=get_sort_key)
    
    # Save to outputs/diagnostic_abrupt_shock_results.csv
    output_path = "/Users/mikusdev/thesis-simulation/outputs/exploratory/diagnostic_abrupt_shock_results.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            print(f"Robustness sweep results saved to: {output_path}")
            
    # Calculate group averages
    grouped = {}
    for res in results:
        key = (res["shock_design"], res["environment"], res["regime"])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(res)
        
    print("\n" + "="*125)
    print("                                     ROBUSTNESS COMPARISON SUMMARY TABLE")
    print("="*125)
    print(f"{'Shock Profile':<14} | {'Environment':<15} | {'Regime':<13} | {'Unmet Dmd%':<10} | {'Price Vol':<9} | {'Osc Index':<9} | {'Imb Avg':<8} | {'Imb Pers':<8} | {'Gov Active%':<11} | {'Avg Block':<9} | {'Max Block':<9}")
    print("-"*125)
    
    for design in shock_designs:
        for env in environments:
            for regime in regimes:
                rows = grouped.get((design, env, regime), [])
                if not rows:
                    continue
                avg_unmet = sum(r["unmet_demand_rate"] for r in rows) / len(rows)
                avg_vol = sum(r["price_volatility"] for r in rows) / len(rows)
                avg_osc = sum(r["oscillation_index"] for r in rows) / len(rows)
                avg_imb = sum(r["spatial_imbalance"] for r in rows) / len(rows)
                avg_pers = sum(r["imbalance_persistence"] for r in rows) / len(rows)
                avg_active = sum(r["adaptive_active_ratio"] for r in rows) / len(rows)
                
                # Extract block metrics (only for active adaptive runs)
                block_lengths = []
                for r in rows:
                    if r["block_lengths_str"]:
                        block_lengths.extend(map(int, r["block_lengths_str"].split(",")))
                avg_block = np.mean(block_lengths) if block_lengths else 0.0
                max_block = np.max(block_lengths) if block_lengths else 0
                
                design_label = "3-tick Ramp" if design == "baseline_3tick" else "1-tick Ramp"
                env_label = "Single Shock" if env == "baseline_shock" else "Repeated Shocks"
                reg_label = "Interaction" if regime == "interaction" else "Adaptive B"
                
                print(f"{design_label:<14} | {env_label:<15} | {reg_label:<13} | {avg_unmet:<10.2%} | {avg_vol:<9.3f} | {avg_osc:<9.3f} | {avg_imb:<8.4f} | {avg_pers:<8.3f} | {avg_active:<11.2%} | {avg_block:<9.2f} | {max_block:<9d}")
    print("="*125)
    
    # Timeline details for Seed 1 (Single Shock)
    print("\n" + "="*80)
    print("                     ACTIVATION TIMELINE EXAMPLE (SEED 1)")
    print("="*80)
    
    for design in ["baseline_3tick", "abrupt_1tick"]:
        res_run = next(r for r in results if r["shock_design"] == design and r["environment"] == "baseline_shock" and r["regime"] == "adaptive_B" and r["seed"] == 1)
        ticks_list = list(map(int, res_run["triggered_ticks_str"].split(","))) if res_run["triggered_ticks_str"] else []
        design_label = "3-tick Ramp (Baseline)" if design == "baseline_3tick" else "1-tick Ramp (Abrupt)"
        print(f"\nProfile: {design_label}")
        print(f"  Triggered Ticks Count: {len(ticks_list)}")
        print(f"  Triggered Ticks List:  {ticks_list[:25]}")
        if len(ticks_list) > 25:
            print(f"                         ... ({len(ticks_list) - 25} more ticks)")
        
        # Check triggers during shock (20-35) vs post-shock (36-100) vs steady-state (101-500)
        during_shock = [t for t in ticks_list if 20 <= t <= 35]
        post_shock = [t for t in ticks_list if 36 <= t <= 100]
        steady_state = [t for t in ticks_list if t < 20 or t > 100]
        
        print(f"  Timeline Breakdown:")
        print(f"    - During Shock (Ticks 20-35):   {len(during_shock)} ticks triggered (e.g. {during_shock})")
        print(f"    - Post-Shock Recovery (36-100): {len(post_shock)} ticks triggered (e.g. {post_shock[:10]})")
        print(f"    - Steady-State / Transients:    {len(steady_state)} ticks triggered (e.g. {steady_state[:10]})")
    print("="*80)

if __name__ == "__main__":
    main()
