"""
Detailed comparison runner for Trigger A vs. Trigger C under Repeated Demand Shocks.
Runs 50 seeds, 500 ticks, and computes all 13 requested metrics.
Loads interaction and static governance baseline data to calculate deltas.
"""

import os
import sys
import csv
import itertools
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd

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

def run_single_comparison(params):
    trigger_rule, seed, steps = params
    
    # Configure repeated shocks environment
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
        adaptive_governance=False,  # Bypassed to apply trigger manually
        shock_mode=shock_mode
    )
    
    # Initial unconstrained parameters
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    triggered_ticks = []
    
    for _ in range(steps):
        is_stressed = False
        if len(model.history) > 0:
            last_imb = model.history[-1]["system"]["spatial_imbalance"]
            
            def get_unmet_ratio(h):
                eff = h["system"]["total_effective_demand"]
                unmet = h["system"]["total_unmet_demand"]
                return unmet / eff if eff > 0 else 0.0
            
            if trigger_rule == "Trigger_A":
                # spatial_imbalance > 0.14 for 3 consecutive ticks
                if len(model.history) >= 3:
                    is_stressed = all(h["system"]["spatial_imbalance"] > 0.14 for h in model.history[-3:])
            elif trigger_rule == "Trigger_C":
                # spatial_imbalance > 0.14 AND unmet_demand_ratio >= 0.30 for at least 3 of last 5 ticks
                if last_imb > 0.14:
                    recent_ticks = model.history[-5:]
                    overload_count = sum(1 for h in recent_ticks if get_unmet_ratio(h) >= 0.30)
                    is_stressed = (overload_count >= 3)
                    
        if is_stressed:
            model.delta = 2.0
            model.theta = 0.0
            model.R_max = 999
        else:
            model.delta = 999.0
            model.theta = 0.0
            model.R_max = 999
            
        model.step()
        
        current_tick = model.steps - 1
        if model.delta == 2.0:
            triggered_ticks.append(current_tick)
            
    # Calculate aggregate summary metrics
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
    
    # Calculate blocks
    blocks = get_contiguous_blocks(triggered_ticks)
    block_lengths = [len(b) for b in blocks]
    
    summary["trigger_rule"] = trigger_rule
    summary["adaptive_active_ratio"] = len(triggered_ticks) / steps
    summary["triggered_ticks_count"] = len(triggered_ticks)
    summary["triggered_ticks_str"] = ",".join(map(str, triggered_ticks))
    summary["block_lengths_str"] = ",".join(map(str, block_lengths))
    summary["mean_block_length"] = np.mean(block_lengths) if block_lengths else 0.0
    summary["max_block_length"] = np.max(block_lengths) if block_lengths else 0
    summary["first_trigger_tick"] = triggered_ticks[0] if triggered_ticks else -1
    
    return summary

def main():
    steps = 500
    runs = 50
    seeds = list(range(1, runs + 1))
    
    tasks = []
    for rule in ["Trigger_A", "Trigger_C"]:
        for seed in seeds:
            tasks.append((rule, seed, steps))
            
    print("=" * 80)
    print("       RUNNING FINAL COMPARISON: TRIGGER A vs. TRIGGER C")
    print("=" * 80)
    print(f"Total Simulation Runs Scheduled: {len(tasks)}")
    print(f"Seeds/Runs per config:          {runs}")
    print(f"Ticks/Steps per run:            {steps}")
    print("-" * 80)
    
    num_workers = multiprocessing.cpu_count()
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(run_single_comparison, tasks))
        
    # Load baselines from Outputs
    baseline_path = "/Users/mikusdev/thesis-simulation/outputs/adaptive_comparison_summary.csv"
    if not os.path.exists(baseline_path):
        print(f"Error: Baseline results file {baseline_path} not found.")
        sys.exit(1)
        
    df_base = pd.read_csv(baseline_path)
    
    # Extract Interaction and Static Gov averages for repeated shocks
    df_int = df_base[(df_base["regime"] == "interaction") & (df_base["environment"] == "repeated_shocks")]
    df_static = df_base[(df_base["regime"] == "static_governance") & (df_base["environment"] == "repeated_shocks")]
    
    baselines_avg = {
        "interaction": {
            "unmet_demand_rate": df_int["unmet_demand_rate"].mean(),
            "revenue_per_vehicle": df_int["revenue_per_vehicle"].mean(),
            "price_volatility": df_int["price_volatility"].mean(),
            "oscillation_index": df_int["oscillation_index"].mean(),
            "spatial_imbalance": df_int["spatial_imbalance"].mean(),
            "imbalance_persistence": df_int["imbalance_persistence"].mean(),
            "overload_frequency": df_int["overload_frequency"].mean(),
            "peak_unmet_demand": df_int["peak_unmet_demand"].mean()
        },
        "static_governance": {
            "unmet_demand_rate": df_static["unmet_demand_rate"].mean(),
            "revenue_per_vehicle": df_static["revenue_per_vehicle"].mean(),
            "price_volatility": df_static["price_volatility"].mean(),
            "oscillation_index": df_static["oscillation_index"].mean(),
            "spatial_imbalance": df_static["spatial_imbalance"].mean(),
            "imbalance_persistence": df_static["imbalance_persistence"].mean(),
            "overload_frequency": df_static["overload_frequency"].mean(),
            "peak_unmet_demand": df_static["peak_unmet_demand"].mean()
        }
    }
    
    # Calculate Trigger averages
    df_res = pd.DataFrame(results)
    grouped = df_res.groupby("trigger_rule")
    
    trigger_stats = {}
    for rule in ["Trigger_A", "Trigger_C"]:
        sub = df_res[df_res["trigger_rule"] == rule]
        
        # Calculate block stats properly by flattening lists
        block_lengths = []
        for bl_str in sub["block_lengths_str"]:
            if bl_str:
                block_lengths.extend(map(int, bl_str.split(",")))
                
        # First trigger tick averaging (excluding -1)
        valid_firsts = sub[sub["first_trigger_tick"] != -1]["first_trigger_tick"]
        
        trigger_stats[rule] = {
            "active_pct": sub["adaptive_active_ratio"].mean(),
            "active_ticks": sub["triggered_ticks_count"].mean(),
            "avg_block": np.mean(block_lengths) if block_lengths else 0.0,
            "max_block": np.max(block_lengths) if block_lengths else 0,
            "first_trigger": valid_firsts.mean() if not valid_firsts.empty else -1,
            "revenue_per_vehicle": sub["revenue_per_vehicle"].mean(),
            "unmet_demand_rate": sub["unmet_demand_rate"].mean(),
            "price_volatility": sub["price_volatility"].mean(),
            "oscillation_index": sub["oscillation_index"].mean(),
            "spatial_imbalance": sub["spatial_imbalance"].mean(),
            "imbalance_persistence": sub["imbalance_persistence"].mean(),
            "overload_frequency": sub["overload_frequency"].mean(),
            "peak_unmet_demand": sub["peak_unmet_demand"].mean()
        }
        
    # Save comparison to CSV
    output_path = "/Users/mikusdev/thesis-simulation/outputs/exploratory/final_trigger_a_c_comparison.csv"
    df_res.to_csv(output_path, index=False)
    print(f"Detailed run results exported to: {output_path}")
    
    # Print the report
    print("\n" + "="*90)
    print("                      DETAILED COMPARISON: TRIGGER A vs. TRIGGER C")
    print("="*90)
    
    metrics_list = [
        ("Gov Active %", "active_pct", "{:.2%}"),
        ("Avg Active Ticks", "active_ticks", "{:.1f}"),
        ("Avg Block Length", "avg_block", "{:.2f}"),
        ("Max Block Length", "max_block", "{:d}"),
        ("First Trigger Tick", "first_trigger", "{:.1f}"),
        ("Revenue per Vehicle", "revenue_per_vehicle", "${:.2f}"),
        ("Unmet Demand Rate", "unmet_demand_rate", "{:.2%}"),
        ("Price Volatility", "price_volatility", "{:.3f}"),
        ("Oscillation Index", "oscillation_index", "{:.3f}"),
        ("Spatial Imbalance (Avg)", "spatial_imbalance", "{:.4f}"),
        ("Imbalance Persistence", "imbalance_persistence", "{:.3f}"),
        ("Overload Frequency", "overload_frequency", "{:.2%}"),
        ("Peak Unmet Demand", "peak_unmet_demand", "{:.1f}")
    ]
    
    print(f"{'Metric':<26} | {'Trigger A (0.15)':<17} | {'Trigger C (0.14+ovld)':<21}")
    print("-"*90)
    
    for label, key, fmt in metrics_list:
        val_a = trigger_stats["Trigger_A"][key]
        val_c = trigger_stats["Trigger_C"][key]
        
        str_a = fmt.format(val_a)
        str_c = fmt.format(val_c)
        
        print(f"{label:<26} | {str_a:<17} | {str_c:<21}")
        
    print("\n" + "="*90)
    print("                             DELTAS RELATIVE TO BASELINES")
    print("="*90)
    print(f"{'Metric':<25} | {'Trigger A vs. Int':<18} | {'Trigger A vs. Stat':<18} | {'Trigger C vs. Int':<18} | {'Trigger C vs. Stat':<18}")
    print("-"*105)
    
    delta_metrics = [
        ("Revenue/Vehicle", "revenue_per_vehicle", "${:+.2f}"),
        ("Unmet Demand Rate", "unmet_demand_rate", "{:+.2%}"),
        ("Price Volatility", "price_volatility", "{:+.3f}"),
        ("Oscillation Index", "oscillation_index", "{:+.3f}"),
        ("Spatial Imbalance", "spatial_imbalance", "{:+.4f}"),
        ("Imbalance Persistence", "imbalance_persistence", "{:+.3f}"),
        ("Overload Frequency", "overload_frequency", "{:+.2%}"),
        ("Peak Unmet Demand", "peak_unmet_demand", "{:+.1f}")
    ]
    
    for label, key, fmt in delta_metrics:
        # Baselines
        int_val = baselines_avg["interaction"][key]
        stat_val = baselines_avg["static_governance"][key]
        
        # Trigger A
        a_val = trigger_stats["Trigger_A"][key]
        da_int = a_val - int_val
        da_stat = a_val - stat_val
        
        # Trigger C
        c_val = trigger_stats["Trigger_C"][key]
        dc_int = c_val - int_val
        dc_stat = c_val - stat_val
        
        print(f"{label:<25} | {fmt.format(da_int):<18} | {fmt.format(da_stat):<18} | {fmt.format(dc_int):<18} | {fmt.format(dc_stat):<18}")
    print("="*105)

if __name__ == "__main__":
    main()
