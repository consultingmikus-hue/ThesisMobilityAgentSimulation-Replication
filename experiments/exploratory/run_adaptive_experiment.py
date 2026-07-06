"""
Adaptive Governance Comparison Experiment Runner.
Compares four regimes across three shock environments over 50 seeds (500 ticks each):
1. Interaction (Unconstrained pricing & rebalancing)
2. Static Governance (delta=2.0, theta=2.0, R_max=25)
3. Adaptive Governance A (Trigger spatial_imbalance > 0.15)
4. Adaptive Governance B (Trigger spatial_imbalance > 0.14)
"""

import os
import sys
import csv
import itertools
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from src.model import ThesisSimulationModel
from src.metrics import summarize_run

def run_single_adaptive_simulation(params):
    regime, env_name, seed, steps = params
    
    # Configure baseline scenario settings
    pricing_enabled = True
    rebalancing_enabled = True
    forecasting_enabled = True
    
    # Configure shock mode
    if env_name == "no_shock":
        shock_mode = "No Demand Shock"
    elif env_name == "baseline_shock":
        shock_mode = "Demand Shock"
    else:
        shock_mode = "Repeated Demand Shocks"
        
    # Configure governance options
    if regime == "interaction":
        governance_enabled = False
        adaptive_governance = False
        adaptive_threshold = 0.15
        delta, theta, R_max = None, None, None
        gov_setting = "none"
    elif regime == "static_governance":
        governance_enabled = True
        adaptive_governance = False
        adaptive_threshold = 0.15
        delta, theta, R_max = 2.0, 2.0, 25
        gov_setting = "static_d2.0_t2.0_r25"
    elif regime == "adaptive_A":
        governance_enabled = True
        adaptive_governance = True
        adaptive_threshold = 0.15
        delta, theta, R_max = 999.0, 0.0, 999  # Normal state defaults, dynamically overridden
        gov_setting = "adaptive_A_t0.15"
    elif regime == "adaptive_B":
        governance_enabled = True
        adaptive_governance = True
        adaptive_threshold = 0.14
        delta, theta, R_max = 999.0, 0.0, 999  # Normal state defaults, dynamically overridden
        gov_setting = "adaptive_B_t0.14"
    else:
        raise ValueError(f"Unknown regime: {regime}")
        
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
    
    # Apply static parameters initially
    if governance_enabled:
        model.delta = delta
        model.theta = theta
        model.R_max = R_max
        
    # Run simulation
    for _ in range(steps):
        model.step()
        
    # Calculate summary metrics
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=f"{regime}_{env_name}",
        governance_setting=gov_setting,
        seed=seed,
        imbalance_threshold=0.15,
        delta=delta if not adaptive_governance else None,
        theta=theta if not adaptive_governance else None,
        R_max=R_max if not adaptive_governance else None
    )
    
    # Track how often the adaptive governance stress state was active
    stress_ticks = 0
    if adaptive_governance and len(model.history) > 1:
        # Ticks where spatial imbalance > threshold (since the state transitions at start of next step,
        # we check the imbalance of step t-1 which triggers state at step t. Tick t-1 has imbalance stored in model.history[t-1])
        # The stress intervention is active at ticks 1 to steps-1.
        for h in model.history[:-1]:
            if h["system"]["spatial_imbalance"] > adaptive_threshold:
                stress_ticks += 1
                
    summary["regime"] = regime
    summary["environment"] = env_name
    summary["adaptive_active_ratio"] = stress_ticks / steps if adaptive_governance else (1.0 if regime == "static_governance" else 0.0)
    
    return summary

def main():
    steps = 500
    runs = 50
    seeds = list(range(1, runs + 1))
    
    regimes = ["interaction", "static_governance", "adaptive_A", "adaptive_B"]
    environments = ["no_shock", "baseline_shock", "repeated_shocks"]
    
    tasks = []
    for regime, env_name, seed in itertools.product(regimes, environments, seeds):
        tasks.append((regime, env_name, seed, steps))
        
    print("=" * 70)
    print("       RUNNING ADAPTIVE GOVERNANCE COMPARISON EXPERIMENTS")
    print("=" * 70)
    print(f"Total Simulation Runs Scheduled: {len(tasks)}")
    print(f"Seeds/Runs per config:          {runs}")
    print(f"Ticks/Steps per run:            {steps}")
    print("-" * 70)
    
    num_workers = multiprocessing.cpu_count()
    print(f"Spawning ProcessPoolExecutor with {num_workers} parallel workers...")
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(run_single_adaptive_simulation, tasks))
        
    # Sort results deterministically
    regime_order = ["interaction", "static_governance", "adaptive_A", "adaptive_B"]
    env_order = ["no_shock", "baseline_shock", "repeated_shocks"]
    
    def get_sort_key(res):
        r_idx = regime_order.index(res["regime"])
        e_idx = env_order.index(res["environment"])
        return (e_idx, r_idx, res["seed"])
        
    results.sort(key=get_sort_key)
    
    # Save results to Outputs
    output_path = "/Users/mikusdev/thesis-simulation/outputs/adaptive_comparison_summary.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            print(f"Aggregated summary results saved to: {output_path}")
            
    # Print the aggregate summary table
    print("\n" + "="*120)
    print("                                      ADAPTIVE GOVERNANCE EXPERIMENTAL RESULTS SUMMARY")
    print("="*120)
    print(f"{'Environment':<15} | {'Regime':<17} | {'Unmet Dmd%':<10} | {'Rev/Veh':<8} | {'Price Vol':<9} | {'Osc Index':<9} | {'Imb Avg':<8} | {'Imb Pers':<8} | {'Overload%':<9} | {'Gov Active%':<11}")
    print("-"*120)
    
    grouped = {}
    for res in results:
        key = (res["environment"], res["regime"])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(res)
        
    for env in env_order:
        for regime in regime_order:
            rows = grouped.get((env, regime), [])
            if not rows:
                continue
            avg_unmet = sum(r["unmet_demand_rate"] for r in rows) / len(rows)
            avg_rev = sum(r["revenue_per_vehicle"] for r in rows) / len(rows)
            avg_vol = sum(r["price_volatility"] for r in rows) / len(rows)
            avg_osc = sum(r["oscillation_index"] for r in rows) / len(rows)
            avg_imb = sum(r["spatial_imbalance"] for r in rows) / len(rows)
            avg_pers = sum(r["imbalance_persistence"] for r in rows) / len(rows)
            avg_over = sum(r["overload_frequency"] for r in rows) / len(rows)
            avg_active = sum(r["adaptive_active_ratio"] for r in rows) / len(rows)
            
            env_label = "No Shock" if env == "no_shock" else ("Single Shock" if env == "baseline_shock" else "Repeated Shocks")
            reg_label = "Interaction" if regime == "interaction" else ("Static Gov" if regime == "static_governance" else ("Adaptive A (0.15)" if regime == "adaptive_A" else "Adaptive B (0.14)"))
            
            print(f"{env_label:<15} | {reg_label:<17} | {avg_unmet:<10.2%} | {avg_rev:<8.2f} | {avg_vol:<9.3f} | {avg_osc:<9.3f} | {avg_imb:<8.4f} | {avg_pers:<8.3f} | {avg_over:<9.2%} | {avg_active:<11.2%}")
            
    print("="*120)

if __name__ == "__main__":
    main()
