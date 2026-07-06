"""
Script to analyze activation details of Adaptive A (0.15) and Adaptive B (0.14).
For a representative seed (e.g., Seed 1) and across 10 seeds, it tracks:
1. Exact ticks triggered.
2. False alarms (triggers outside shock periods).
3. Contiguous block lengths of activation.
"""

import os
import sys
import numpy as np

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from src.model import ThesisSimulationModel

def get_shock_ticks(steps, mode):
    if mode == "No Demand Shock":
        return set()
    elif mode == "Demand Shock":
        return set(range(20, 36))
    elif mode == "Repeated Demand Shocks":
        shock_ticks = set()
        for t in range(steps):
            if t >= 20 and (t - 20) % 40 <= 15:
                shock_ticks.add(t)
        return shock_ticks
    return set()

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

def analyze_regime(regime, env_name, seed, steps=500):
    if env_name == "baseline_shock":
        shock_mode = "Demand Shock"
    else:
        shock_mode = "Repeated Demand Shocks"
        
    adaptive_threshold = 0.15 if regime == "Adaptive A" else 0.14
    
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=True,
        rebalancing_enabled=True,
        forecasting_enabled=True,
        governance_enabled=True,
        adaptive_governance=True,
        adaptive_governance_threshold=adaptive_threshold,
        shock_mode=shock_mode
    )
    
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    triggered_ticks = []
    for t in range(steps):
        # We check the trigger status which is set at the start of step()
        # The trigger condition uses history[-1] (previous tick's spatial imbalance).
        # We can simulate the step, then check if it was in the stress state in this step.
        model.step()
        
        # In the model: self.history[-1] represents the state that was logged.
        # Since state transition checks last_imb > threshold at start of step t,
        # we can see whether the limits were applied during step t.
        # Let's check: if model.delta == 2.0, then stress state was active during this step.
        # Step index is model.steps - 1 (since it was incremented during step).
        current_tick = model.steps - 1
        if model.delta == 2.0:
            triggered_ticks.append(current_tick)
            
    shock_ticks = get_shock_ticks(steps, shock_mode)
    triggered_set = set(triggered_ticks)
    
    # False alarms: triggered ticks outside shock periods
    false_alarms = triggered_set - shock_ticks
    # Missed ticks: shock ticks that did not trigger
    missed_shocks = shock_ticks - triggered_set
    
    blocks = get_contiguous_blocks(triggered_ticks)
    block_lengths = [len(b) for b in blocks]
    
    return {
        "triggered_ticks": triggered_ticks,
        "false_alarms": sorted(list(false_alarms)),
        "missed_shocks": sorted(list(missed_shocks)),
        "blocks": blocks,
        "block_lengths": block_lengths
    }

def main():
    steps = 500
    seeds_count = 10
    
    for env in ["baseline_shock", "repeated_shocks"]:
        print("\n" + "="*80)
        print(f" ENVIRONMENT: {env.upper()}")
        print("="*80)
        
        for regime in ["Adaptive A", "Adaptive B"]:
            print(f"\n>>> REGIME: {regime} <<<")
            
            # 1. Detail on Seed 1
            res1 = analyze_regime(regime, env, seed=1, steps=steps)
            print(f"Seed 1 Details:")
            print(f"  Triggered ticks count: {len(res1['triggered_ticks'])}")
            print(f"  Triggered ticks:       {res1['triggered_ticks'][:25]}")
            if len(res1['triggered_ticks']) > 25:
                print(f"                         ... ({len(res1['triggered_ticks']) - 25} more ticks)")
            print(f"  Contiguous blocks:     {[f'{b[0]}-{b[-1]} (len={len(b)})' for b in res1['blocks']]}")
            print(f"  False alarms (ticks):  {res1['false_alarms']}")
            print(f"  Missed shock ticks:    {res1['missed_shocks'][:15]}")
            if len(res1['missed_shocks']) > 15:
                print(f"                         ... ({len(res1['missed_shocks']) - 15} more)")
                
            # 2. Aggregated over 10 seeds
            all_false_alarms = []
            all_block_lengths = []
            all_triggered_counts = []
            
            for s in range(1, seeds_count + 1):
                res = analyze_regime(regime, env, seed=s, steps=steps)
                all_false_alarms.append(len(res["false_alarms"]))
                all_block_lengths.extend(res["block_lengths"])
                all_triggered_counts.append(len(res["triggered_ticks"]))
                
            mean_triggered = np.mean(all_triggered_counts)
            mean_false = np.mean(all_false_alarms)
            mean_block = np.mean(all_block_lengths) if all_block_lengths else 0.0
            max_block = np.max(all_block_lengths) if all_block_lengths else 0
            
            print(f"\n  Average across {seeds_count} seeds:")
            print(f"    Mean triggered ticks:        {mean_triggered:.2f} ticks ({mean_triggered/steps:.2%})")
            print(f"    Mean false alarm ticks:      {mean_false:.2f} ticks")
            print(f"    Mean contiguous block length: {mean_block:.2f} ticks")
            print(f"    Max contiguous block length:  {max_block} ticks")
            print("-"*80)

if __name__ == "__main__":
    main()
