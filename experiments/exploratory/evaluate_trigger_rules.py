"""
Trigger rules comparison experiment script.
Evaluates four alternative trigger rules under the repeated demand shock scenario:
- Trigger A: spatial_imbalance > 0.14 for 3 consecutive ticks
- Trigger B: spatial_imbalance > 0.14 AND unmet_demand_ratio > 0.30
- Trigger C: spatial_imbalance > 0.14 AND overload_frequency_condition (>= 3 of last 5 ticks in overload ratio >= 0.30)
- Trigger D: spatial_imbalance > 0.14 (current baseline)

Uses 50 seeds, 500 ticks, and unconstrained rebalancing in the stress state (delta=2, theta=0, R_max=999).
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

def run_trigger_rule_simulation(params):
    trigger_rule, seed, steps = params
    
    # Configure scenario: repeated shocks
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
        adaptive_governance=False,
        shock_mode=shock_mode
    )
    
    # Default unconstrained limits
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    triggered_ticks = []
    
    for _ in range(steps):
        # Apply custom trigger rule at start of step
        is_stressed = False
        if len(model.history) > 0:
            last_imb = model.history[-1]["system"]["spatial_imbalance"]
            
            # Helper: calculate unmet ratio for last step
            def get_unmet_ratio(h):
                eff = h["system"]["total_effective_demand"]
                unmet = h["system"]["total_unmet_demand"]
                return unmet / eff if eff > 0 else 0.0
            
            if trigger_rule == "Trigger_A":
                # spatial_imbalance > 0.14 for 3 consecutive ticks
                if len(model.history) >= 3:
                    is_stressed = all(h["system"]["spatial_imbalance"] > 0.14 for h in model.history[-3:])
            elif trigger_rule == "Trigger_B":
                # spatial_imbalance > 0.14 AND unmet_demand_ratio > 0.30
                last_unmet_ratio = get_unmet_ratio(model.history[-1])
                is_stressed = (last_imb > 0.14) and (last_unmet_ratio > 0.30)
            elif trigger_rule == "Trigger_C":
                # spatial_imbalance > 0.14 AND overload_frequency_condition (>= 3 of last 5 ticks with ratio >= 0.30)
                if last_imb > 0.14:
                    recent_ticks = model.history[-5:]
                    overload_count = sum(1 for h in recent_ticks if get_unmet_ratio(h) >= 0.30)
                    is_stressed = (overload_count >= 3)
            elif trigger_rule == "Trigger_D":
                # spatial_imbalance > 0.14 (current baseline)
                is_stressed = (last_imb > 0.14)
                
        if is_stressed:
            model.delta = 2.0
            model.theta = 0.0
            model.R_max = 999
        else:
            model.delta = 999.0
            model.theta = 0.0
            model.R_max = 999
            
        model.step()
        
        # Check if stress was active during the step that just completed
        current_tick = model.steps - 1
        if model.delta == 2.0:
            triggered_ticks.append(current_tick)
            
    # Calculate summary metrics
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=f"{trigger_rule}_repeated_shocks",
        governance_setting=f"adaptive_{trigger_rule}",
        seed=seed,
        imbalance_threshold=0.15,
        delta=None,
        theta=None,
        R_max=None
    )
    
    # Calculate block lengths
    blocks = get_contiguous_blocks(triggered_ticks)
    block_lengths = [len(b) for b in blocks]
    
    summary["trigger_rule"] = trigger_rule
    summary["adaptive_active_ratio"] = len(triggered_ticks) / steps
    summary["triggered_ticks_str"] = ",".join(map(str, triggered_ticks))
    summary["block_lengths_str"] = ",".join(map(str, block_lengths))
    summary["mean_block_length"] = np.mean(block_lengths) if block_lengths else 0.0
    summary["max_block_length"] = np.max(block_lengths) if block_lengths else 0
    
    # Calculate timing of first trigger
    first_trigger = triggered_ticks[0] if triggered_ticks else -1
    summary["first_trigger_tick"] = first_trigger
    
    # Calculate false alarms (triggers outside the repeating shock periods)
    # Repeating shocks occur at: t >= 20 and (t - 20) % 40 <= 15
    shock_ticks_count = 0
    non_shock_ticks_count = 0
    for t in triggered_ticks:
        if t >= 20 and (t - 20) % 40 <= 15:
            shock_ticks_count += 1
        else:
            non_shock_ticks_count += 1
            
    summary["active_during_shocks"] = shock_ticks_count
    summary["active_outside_shocks"] = non_shock_ticks_count
    
    return summary

def main():
    steps = 500
    runs = 50
    seeds = list(range(1, runs + 1))
    
    trigger_rules = ["Trigger_A", "Trigger_B", "Trigger_C", "Trigger_D"]
    
    tasks = []
    for rule, seed in itertools.product(trigger_rules, seeds):
        tasks.append((rule, seed, steps))
        
    print("=" * 80)
    print("       RUNNING ADAPTIVE GOVERNANCE TRIGGER COMPARISONS")
    print("=" * 80)
    print(f"Total Simulation Runs Scheduled: {len(tasks)}")
    print(f"Seeds/Runs per trigger:         {runs}")
    print(f"Ticks/Steps per run:            {steps}")
    print("-" * 80)
    
    num_workers = multiprocessing.cpu_count()
    print(f"Spawning ProcessPoolExecutor with {num_workers} parallel workers...")
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(run_trigger_rule_simulation, tasks))
        
    # Sort results deterministically
    def get_sort_key(res):
        tr_idx = trigger_rules.index(res["trigger_rule"])
        return (tr_idx, res["seed"])
    results.sort(key=get_sort_key)
    
    # Save results to Outputs
    output_path = "/Users/mikusdev/thesis-simulation/outputs/exploratory/trigger_rules_comparison.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            print(f"Trigger comparison results saved to: {output_path}")
            
    # Calculate group averages
    grouped = {}
    for res in results:
        key = res["trigger_rule"]
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(res)
        
    print("\n" + "="*125)
    print("                                      TRIGGER RULES COMPARATIVE RESULTS TABLE")
    print("="*125)
    print(f"{'Trigger Rule':<25} | {'Active%':<8} | {'Active Tks':<10} | {'Shk Tks':<8} | {'Non-Shk Tks':<11} | {'Avg Block':<9} | {'Max Block':<9} | {'First Trg':<9} | {'Price Vol':<9} | {'Osc Index':<9} | {'Unmet Dmd%':<10} | {'Imb Pers':<8}")
    print("-"*125)
    
    for rule in trigger_rules:
        rows = grouped.get(rule, [])
        if not rows:
            continue
        avg_active = sum(r["adaptive_active_ratio"] for r in rows) / len(rows)
        avg_active_ticks = avg_active * steps
        avg_shock_ticks = sum(r["active_during_shocks"] for r in rows) / len(rows)
        avg_non_shock_ticks = sum(r["active_outside_shocks"] for r in rows) / len(rows)
        
        # Block lengths
        block_lengths = []
        for r in rows:
            if r["block_lengths_str"]:
                block_lengths.extend(map(int, r["block_lengths_str"].split(",")))
        avg_block = np.mean(block_lengths) if block_lengths else 0.0
        max_block = np.max(block_lengths) if block_lengths else 0
        
        avg_first_trigger = sum(r["first_trigger_tick"] for r in rows if r["first_trigger_tick"] != -1) / sum(1 for r in rows if r["first_trigger_tick"] != -1)
        
        avg_vol = sum(r["price_volatility"] for r in rows) / len(rows)
        avg_osc = sum(r["oscillation_index"] for r in rows) / len(rows)
        avg_unmet = sum(r["unmet_demand_rate"] for r in rows) / len(rows)
        avg_pers = sum(r["imbalance_persistence"] for r in rows) / len(rows)
        
        rule_label = "D: imbalance > 0.14 (Base)" if rule == "Trigger_D" else (
            "A: imb > 0.14 (3 consec)" if rule == "Trigger_A" else (
                "B: imb > 0.14 & unmet > 0.3" if rule == "Trigger_B" else "C: imb > 0.14 & ovld_freq"
            )
        )
        
        print(f"{rule_label:<25} | {avg_active:<8.2%} | {avg_active_ticks:<10.1f} | {avg_shock_ticks:<8.1f} | {avg_non_shock_ticks:<11.1f} | {avg_block:<9.2f} | {max_block:<9d} | {avg_first_trigger:<9.1f} | {avg_vol:<9.3f} | {avg_osc:<9.3f} | {avg_unmet:<10.2%} | {avg_pers:<8.3f}")
    print("="*125)
    
    # Print a timeline example of Seed 1
    print("\n" + "="*80)
    print("                     ACTIVATION TIMELINE COMPARISON (SEED 1)")
    print("="*80)
    for rule in trigger_rules:
        res_run = next(r for r in results if r["trigger_rule"] == rule and r["seed"] == 1)
        ticks_list = list(map(int, res_run["triggered_ticks_str"].split(","))) if res_run["triggered_ticks_str"] else []
        rule_label = "Trigger D (Baseline)" if rule == "Trigger_D" else (
            "Trigger A (3 consec)" if rule == "Trigger_A" else (
                "Trigger B (imb & unmet)" if rule == "Trigger_B" else "Trigger C (imb & ovld_freq)"
            )
        )
        print(f"\nRule: {rule_label}")
        print(f"  Triggered Ticks Count: {len(ticks_list)}")
        print(f"  Triggered Ticks:       {ticks_list[:25]}")
        if len(ticks_list) > 25:
            print(f"                         ... ({len(ticks_list) - 25} more ticks)")
    print("="*80)

if __name__ == "__main__":
    main()
