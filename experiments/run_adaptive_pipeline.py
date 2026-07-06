"""
Master pipeline runner for the exploratory adaptive governance extension.
Executes the following components under final calibrated settings (N=80, 50% carryover):
1. 27-configuration static governance grid sweep and selection.
2. Main adaptive governance comparison under repeated shocks (Interaction, Static Gov, Trigger A, Trigger C).
3. Parameter sensitivity analysis for Trigger C (Delta, Threshold, Persistence).
4. Robustness checks comparing 1-tick abrupt shock with 3-tick ramp shock.
5. Recovery-phase tick-level diagnostic averaging and matplotlib visualization.
"""

import os
import sys
import csv
import json
import itertools
import multiprocessing as mp
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.model import ThesisSimulationModel
from src.metrics import summarize_run

OUT_DIR = "outputs/final_exploratory_adaptive_governance"
TICKS = 500
SEEDS_COUNT = 50
SEEDS = list(range(1, SEEDS_COUNT + 1))

# Helper: calculate unmet ratio for a history entry
def get_unmet_ratio(h):
    eff = h["system"]["total_effective_demand"]
    unmet = h["system"]["total_unmet_demand"]
    return unmet / eff if eff > 0 else 0.0

# Trigger A Check: imbalance > threshold for L consecutive ticks
def check_trigger_a(history, imbalance_threshold=0.14, L=3):
    if len(history) < L:
        return False
    return all(h["system"]["spatial_imbalance"] > imbalance_threshold for h in history[-L:])

# Trigger C Check: imbalance > threshold AND >= L of last 5 ticks in overload
def check_trigger_c(history, imbalance_threshold=0.14, L=3):
    if not history:
        return False
    last_imb = history[-1]["system"]["spatial_imbalance"]
    if last_imb > imbalance_threshold:
        recent_ticks = history[-5:]
        overload_count = sum(1 for h in recent_ticks if get_unmet_ratio(h) >= 0.30)
        return (overload_count >= L)
    return False

# Component 1 Worker: Static Governance Grid Sweep
def run_static_grid_worker(params):
    delta, theta, R_max, seed = params
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=True,
        rebalancing_enabled=True,
        forecasting_enabled=True,
        governance_enabled=True,
        shock_mode="No Demand Shock"
    )
    model.delta = delta
    model.theta = theta
    model.R_max = R_max
    
    for _ in range(TICKS):
        model.step()
        
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario="governance",
        governance_setting=f"d{delta}_t{theta}_r{R_max}",
        seed=seed,
        delta=delta,
        theta=theta,
        R_max=R_max
    )
    return summary

# Component 2 & 3 Worker: Adaptive/Interaction Simulation
def run_simulation_worker(params):
    regime, env_name, seed, trigger_type, threshold, persistence, delta_stress = params
    
    # Environment Setup
    if env_name == "no_shock":
        shock_mode = "No Demand Shock"
    elif env_name == "baseline_shock":
        shock_mode = "Demand Shock"
    else:
        shock_mode = "Repeated Demand Shocks"
        
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=True,
        rebalancing_enabled=True,
        forecasting_enabled=True,
        governance_enabled=(regime != "interaction"),
        shock_mode=shock_mode
    )
    
    # Initialize with unconstrained defaults
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    triggered_ticks = 0
    
    for _ in range(TICKS):
        is_stressed = False
        if regime == "static_governance":
            is_stressed = True
            model.delta = delta_stress # For static, apply static delta
            model.theta = threshold    # For static, use threshold as theta
            model.R_max = persistence  # For static, use persistence as R_max
        elif regime == "adaptive":
            if trigger_type == "Trigger_A":
                is_stressed = check_trigger_a(model.history, threshold, persistence)
            elif trigger_type == "Trigger_C":
                is_stressed = check_trigger_c(model.history, threshold, persistence)
                
            if is_stressed:
                model.delta = delta_stress
                model.theta = 0.0
                model.R_max = 999
            else:
                model.delta = 999.0
                model.theta = 0.0
                model.R_max = 999
                
        model.step()
        if is_stressed and regime == "adaptive":
            triggered_ticks += 1
            
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=f"{regime}_{trigger_type}_{env_name}" if regime == "adaptive" else f"{regime}_{env_name}",
        governance_setting=f"adaptive_{trigger_type}" if regime == "adaptive" else ("static" if regime == "static_governance" else "none"),
        seed=seed,
        delta=model.delta if regime == "static_governance" else None,
        theta=model.theta if regime == "static_governance" else None,
        R_max=model.R_max if regime == "static_governance" else None
    )
    summary["regime"] = regime
    summary["trigger_type"] = trigger_type
    summary["adaptive_active_ratio"] = triggered_ticks / TICKS if regime == "adaptive" else (1.0 if regime == "static_governance" else 0.0)
    summary["threshold_param"] = threshold
    summary["persistence_param"] = persistence
    summary["delta_stress"] = delta_stress
    summary["environment"] = env_name
    
    return summary

# Component 4 Worker: Shock profile robustness comparison
def run_robustness_worker(params):
    regime, env_name, seed, shock_design, trigger_type = params
    
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=True,
        rebalancing_enabled=True,
        forecasting_enabled=True,
        governance_enabled=(regime == "adaptive"),
        shock_mode="Demand Shock" if env_name == "baseline_shock" else "Repeated Demand Shocks"
    )
    
    # Custom multiplier overrides for 1-tick abrupt shock
    if shock_design == "abrupt_1tick":
        def abrupt_single_multiplier(self):
            t = self.steps
            if t <= 19: return 1.0
            elif t == 20: return 2.5
            elif t <= 34: return 4.0
            elif t == 35: return 2.5
            else: return 1.0
            
        def abrupt_repeated_multiplier(self):
            t = self.steps
            if t < 20: return 1.0
            t_rel = (t - 20) % 40
            if t_rel == 0: return 2.5
            elif t_rel <= 14: return 4.0
            elif t_rel == 15: return 2.5
            else: return 1.0
            
        if env_name == "baseline_shock":
            model.get_shock_multiplier = abrupt_single_multiplier.__get__(model, ThesisSimulationModel)
        else:
            model.get_shock_multiplier = abrupt_repeated_multiplier.__get__(model, ThesisSimulationModel)
            
    # Unconstrained defaults
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    triggered_ticks = []
    
    for _ in range(TICKS):
        is_stressed = False
        if regime == "adaptive":
            if trigger_type == "Trigger_A":
                is_stressed = check_trigger_a(model.history, 0.14, 3)
            elif trigger_type == "Trigger_C":
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
        current_tick = model.steps - 1
        if is_stressed and regime == "adaptive":
            triggered_ticks.append(current_tick)
            
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=f"{regime}_{shock_design}_{env_name}",
        governance_setting=f"adaptive_{trigger_type}",
        seed=seed
    )
    
    # Calculate triggers in shock phase (20-35) vs recovery (36-100) vs steady state (101-500)
    during_shock = sum(1 for t in triggered_ticks if 20 <= t <= 35)
    post_shock = sum(1 for t in triggered_ticks if 36 <= t <= 100)
    
    summary["regime"] = regime
    summary["shock_design"] = shock_design
    summary["environment"] = env_name
    summary["adaptive_active_ratio"] = len(triggered_ticks) / TICKS
    summary["shock_phase_active_ticks"] = during_shock
    summary["recovery_phase_active_ticks"] = post_shock
    summary["trigger_type"] = trigger_type
    
    return summary

# Component 5 Worker: Tick-by-tick recovery diagnostics (No averaging inside, returns raw history metrics)
def run_recovery_worker(params):
    regime, seed, trigger_type = params
    steps = 150 # Focus on first 150 steps to cover single shock (ticks 20-36) and its recovery
    
    model = ThesisSimulationModel(
        seed=seed,
        pricing_enabled=True,
        rebalancing_enabled=True,
        forecasting_enabled=True,
        governance_enabled=(regime == "adaptive"),
        shock_mode="Demand Shock"
    )
    
    # Unconstrained defaults
    model.delta = 999.0
    model.theta = 0.0
    model.R_max = 999
    
    history_records = []
    
    for _ in range(steps):
        is_stressed = False
        if regime == "adaptive":
            if trigger_type == "Trigger_A":
                is_stressed = check_trigger_a(model.history, 0.14, 3)
            elif trigger_type == "Trigger_C":
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
        
        # Log tick metrics
        t = model.steps - 1
        h = model.history[-1]
        
        # Calculate unmet ratio
        unmet_ratio = get_unmet_ratio(h)
        
        # Calculate price standard deviation (dispersion) across zones
        prices = [h["zones"][z]["price"] for z in h["zones"]]
        price_disp = np.std(prices) if prices else 0.0
        
        history_records.append({
            "tick": t,
            "spatial_imbalance": h["system"]["spatial_imbalance"],
            "unmet_demand_ratio": unmet_ratio,
            "price_dispersion": price_disp,
            "governance_active": 1.0 if is_stressed else 0.0
        })
        
    return history_records

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    num_workers = mp.cpu_count()
    print(f"Master pipeline starting. Using {num_workers} parallel workers.")
    
    # =========================================================================
    # COMPONENT 1: Static Governance Grid Sweep and Selection
    # =========================================================================
    print("\n--- Running Component 1: Static Governance Grid Sweep ---")
    deltas = [1.0, 2.0, 4.0]
    thetas = [1.0, 2.0, 4.0]
    r_maxs = [10, 25, 40]
    
    static_tasks = []
    for d, t, r in itertools.product(deltas, thetas, r_maxs):
        for seed in SEEDS:
            static_tasks.append((d, t, r, seed))
            
    with mp.Pool(processes=num_workers) as pool:
        static_results = pool.map(run_static_grid_worker, static_tasks)
        
    # Run baseline interaction for static selection comparison
    baseline_tasks = [("interaction", "no_shock", seed, "none", 0.0, 0, 999.0) for seed in SEEDS]
    with mp.Pool(processes=num_workers) as pool:
        baseline_results = pool.map(run_simulation_worker, baseline_tasks)
        
    # Aggregate baseline means
    df_int_base = pd_df = [r for r in baseline_results]
    int_means = {
        "revenue_per_vehicle": np.mean([r["revenue_per_vehicle"] for r in df_int_base]),
        "service_rate": np.mean([r["service_rate"] for r in df_int_base]),
        "price_volatility": np.mean([r["price_volatility"] for r in df_int_base]),
        "oscillation_index": np.mean([r["oscillation_index"] for r in df_int_base]),
        "overload_frequency": np.mean([r["overload_frequency"] for r in df_int_base]),
        "demand_supply_mismatch": np.mean([r["demand_supply_mismatch"] for r in df_int_base])
    }
    
    # Group static results
    grouped_static = {}
    for r in static_results:
        key = (r["governance_delta"], r["governance_theta"], r["governance_R_max"])
        if key not in grouped_static:
            grouped_static[key] = []
        grouped_static[key].append(r)
        
    sweep_rows = []
    for key, runs in grouped_static.items():
        d_val, t_val, r_val = key
        mean_rev = np.mean([x["revenue_per_vehicle"] for x in runs])
        mean_srv = np.mean([x["service_rate"] for x in runs])
        mean_vol = np.mean([x["price_volatility"] for x in runs])
        mean_osc = np.mean([x["oscillation_index"] for x in runs])
        mean_ovl = np.mean([x["overload_frequency"] for x in runs])
        mean_mis = np.mean([x["demand_supply_mismatch"] for x in runs])
        mean_vc = np.mean([x["vehicle_concentration"] for x in runs])
        
        # Metrics changes relative to baseline
        rev_change = (mean_rev - int_means["revenue_per_vehicle"]) / abs(int_means["revenue_per_vehicle"])
        srv_change = (mean_srv - int_means["service_rate"]) / abs(int_means["service_rate"])
        vol_imp = (int_means["price_volatility"] - mean_vol) / abs(int_means["price_volatility"])
        osc_imp = (int_means["oscillation_index"] - mean_osc) / abs(int_means["oscillation_index"])
        ovl_imp = (int_means["overload_frequency"] - mean_ovl) / abs(int_means["overload_frequency"])
        mis_imp = (int_means["demand_supply_mismatch"] - mean_mis) / abs(int_means["demand_supply_mismatch"])
        
        # Exclusions and scoring
        excluded = (srv_change < -0.10) or (rev_change < -0.10) or (ovl_imp < -0.10)
        score = 0.35 * vol_imp + 0.25 * osc_imp + 0.15 * ovl_imp + 0.10 * mis_imp + 0.10 * srv_change + 0.05 * rev_change
        
        sweep_rows.append({
            "delta": d_val, "theta": t_val, "Rmax": r_val,
            "revenue_per_vehicle": mean_rev, "service_rate": mean_srv,
            "overload_frequency": mean_ovl, "spatial_demand_supply_mismatch": mean_mis,
            "price_volatility": mean_vol, "price_oscillation_index": mean_osc,
            "vehicle_concentration": mean_vc,
            "service_rate_change": srv_change, "revenue_per_vehicle_change": rev_change,
            "overload_frequency_improvement": ovl_imp, "balanced_score": score,
            "excluded": int(excluded)
        })
        
    # Write Sweep Summary CSV
    sweep_csv_path = os.path.join(OUT_DIR, "adaptive_static_sweep_summary.csv")
    with open(sweep_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sweep_rows[0].keys())
        writer.writeheader()
        writer.writerows(sweep_rows)
        
    # Apply selection
    non_excluded = [row for row in sweep_rows if not row["excluded"]]
    fallback_used = False
    if non_excluded:
        selected_row = sorted(non_excluded, key=lambda x: x["balanced_score"], reverse=True)[0]
    else:
        # Fallback
        selected_row = sorted(sweep_rows, key=lambda x: (x["service_rate_change"], -x["price_volatility"]), reverse=True)[0]
        fallback_used = True
        
    sel_delta = selected_row["delta"]
    sel_theta = selected_row["theta"]
    sel_Rmax = selected_row["Rmax"]
    print(f"Selected Static Governance: delta={sel_delta}, theta={sel_theta}, R_max={sel_Rmax} (Fallback={fallback_used})")

    # =========================================================================
    # COMPONENT 2: Main Adaptive Governance Comparison
    # =========================================================================
    print("\n--- Running Component 2: Main Adaptive Governance Comparison ---")
    comp_tasks = []
    # 1. Interaction baseline
    for seed in SEEDS:
        comp_tasks.append(("interaction", "repeated_shocks", seed, "none", 0.0, 0, 999.0))
    # 2. Selected Static Governance
    for seed in SEEDS:
        comp_tasks.append(("static_governance", "repeated_shocks", seed, "none", sel_theta, sel_Rmax, sel_delta))
    # 3. Adaptive Trigger A (threshold 0.14, consecutive length 3, delta 2.0)
    for seed in SEEDS:
        comp_tasks.append(("adaptive", "repeated_shocks", seed, "Trigger_A", 0.14, 3, 2.0))
    # 4. Adaptive Trigger C (threshold 0.14, persistence 3 of 5, delta 2.0)
    for seed in SEEDS:
        comp_tasks.append(("adaptive", "repeated_shocks", seed, "Trigger_C", 0.14, 3, 2.0))
        
    with mp.Pool(processes=num_workers) as pool:
        comp_results = pool.map(run_simulation_worker, comp_tasks)
        
    # Calculate means
    comp_grouped = {}
    for r in comp_results:
        key = (r["regime"], r["trigger_type"])
        if key not in comp_grouped:
            comp_grouped[key] = []
        comp_grouped[key].append(r)
        
    comp_summary = []
    for key, runs in comp_grouped.items():
        reg, trig = key
        label = "interaction" if reg == "interaction" else ("static_governance" if reg == "static_governance" else f"adaptive_{trig}")
        
        comp_summary.append({
            "regime": label,
            "revenue_per_vehicle": np.mean([x["revenue_per_vehicle"] for x in runs]),
            "service_rate": np.mean([x["service_rate"] for x in runs]),
            "overload_frequency": np.mean([x["overload_frequency"] for x in runs]),
            "spatial_demand_supply_mismatch": np.mean([x["spatial_imbalance"] for x in runs]),
            "price_volatility": np.mean([x["price_volatility"] for x in runs]),
            "price_oscillation_index": np.mean([x["oscillation_index"] for x in runs]),
            "vehicle_concentration": np.mean([x["vehicle_concentration"] for x in runs]),
            "intervention_frequency": np.mean([x["adaptive_active_ratio"] for x in runs])
        })
        
    comp_csv_path = os.path.join(OUT_DIR, "adaptive_comparison_summary.csv")
    with open(comp_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=comp_summary[0].keys())
        writer.writeheader()
        writer.writerows(comp_summary)
        
    # =========================================================================
    # COMPONENT 3: Parameter Sensitivity Analysis
    # =========================================================================
    print("\n--- Running Component 3: Parameter Sensitivity ---")
    
    # 3.1 Delta Sensitivity Sweep (delta = 1.0, 1.5, 2.0, 3.0)
    delta_tasks = []
    for d in [1.0, 1.5, 2.0, 3.0]:
        for seed in SEEDS:
            delta_tasks.append(("adaptive", "repeated_shocks", seed, "Trigger_C", 0.14, 3, d))
            
    with mp.Pool(processes=num_workers) as pool:
        delta_results = pool.map(run_simulation_worker, delta_tasks)
        
    delta_grouped = {}
    for r in delta_results:
        key = r["delta_stress"]
        if key not in delta_grouped:
            delta_grouped[key] = []
        delta_grouped[key].append(r)
        
    delta_summary = []
    for d_val, runs in delta_grouped.items():
        delta_summary.append({
            "delta": d_val,
            "revenue_per_vehicle": np.mean([x["revenue_per_vehicle"] for x in runs]),
            "service_rate": np.mean([x["service_rate"] for x in runs]),
            "overload_frequency": np.mean([x["overload_frequency"] for x in runs]),
            "spatial_demand_supply_mismatch": np.mean([x["spatial_imbalance"] for x in runs]),
            "price_volatility": np.mean([x["price_volatility"] for x in runs]),
            "price_oscillation_index": np.mean([x["oscillation_index"] for x in runs]),
            "vehicle_concentration": np.mean([x["vehicle_concentration"] for x in runs]),
            "intervention_frequency": np.mean([x["adaptive_active_ratio"] for x in runs])
        })
        
    delta_csv_path = os.path.join(OUT_DIR, "adaptive_delta_sensitivity.csv")
    with open(delta_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=delta_summary[0].keys())
        writer.writeheader()
        writer.writerows(delta_summary)
        
    # 3.2 Threshold Sensitivity Sweep (imbalance threshold = 0.12, 0.14, 0.16)
    thresh_tasks = []
    for t in [0.12, 0.14, 0.16]:
        for seed in SEEDS:
            thresh_tasks.append(("adaptive", "repeated_shocks", seed, "Trigger_C", t, 3, 2.0))
            
    with mp.Pool(processes=num_workers) as pool:
        thresh_results = pool.map(run_simulation_worker, thresh_tasks)
        
    thresh_grouped = {}
    for r in thresh_results:
        key = r["threshold_param"]
        if key not in thresh_grouped:
            thresh_grouped[key] = []
        thresh_grouped[key].append(r)
        
    thresh_summary = []
    for t_val, runs in thresh_grouped.items():
        thresh_summary.append({
            "threshold": t_val,
            "revenue_per_vehicle": np.mean([x["revenue_per_vehicle"] for x in runs]),
            "service_rate": np.mean([x["service_rate"] for x in runs]),
            "overload_frequency": np.mean([x["overload_frequency"] for x in runs]),
            "spatial_demand_supply_mismatch": np.mean([x["spatial_imbalance"] for x in runs]),
            "price_volatility": np.mean([x["price_volatility"] for x in runs]),
            "price_oscillation_index": np.mean([x["oscillation_index"] for x in runs]),
            "vehicle_concentration": np.mean([x["vehicle_concentration"] for x in runs]),
            "intervention_frequency": np.mean([x["adaptive_active_ratio"] for x in runs])
        })
        
    thresh_csv_path = os.path.join(OUT_DIR, "adaptive_threshold_sensitivity.csv")
    with open(thresh_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=thresh_summary[0].keys())
        writer.writeheader()
        writer.writerows(thresh_summary)
        
    # 3.3 Persistence Sensitivity Sweep (persistence length = 2, 3, 4 ticks)
    pers_tasks = []
    for p in [2, 3, 4]:
        for seed in SEEDS:
            pers_tasks.append(("adaptive", "repeated_shocks", seed, "Trigger_C", 0.14, p, 2.0))
            
    with mp.Pool(processes=num_workers) as pool:
        pers_results = pool.map(run_simulation_worker, pers_tasks)
        
    pers_grouped = {}
    for r in pers_results:
        key = r["persistence_param"]
        if key not in pers_grouped:
            pers_grouped[key] = []
        pers_grouped[key].append(r)
        
    pers_summary = []
    for p_val, runs in pers_grouped.items():
        pers_summary.append({
            "persistence": p_val,
            "revenue_per_vehicle": np.mean([x["revenue_per_vehicle"] for x in runs]),
            "service_rate": np.mean([x["service_rate"] for x in runs]),
            "overload_frequency": np.mean([x["overload_frequency"] for x in runs]),
            "spatial_demand_supply_mismatch": np.mean([x["spatial_imbalance"] for x in runs]),
            "price_volatility": np.mean([x["price_volatility"] for x in runs]),
            "price_oscillation_index": np.mean([x["oscillation_index"] for x in runs]),
            "vehicle_concentration": np.mean([x["vehicle_concentration"] for x in runs]),
            "intervention_frequency": np.mean([x["adaptive_active_ratio"] for x in runs])
        })
        
    pers_csv_path = os.path.join(OUT_DIR, "adaptive_persistence_sensitivity.csv")
    with open(pers_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=pers_summary[0].keys())
        writer.writeheader()
        writer.writerows(pers_summary)

    # =========================================================================
    # COMPONENT 4: Abrupt Shock Robustness Check
    # =========================================================================
    print("\n--- Running Component 4: Abrupt Shock Robustness ---")
    rob_tasks = []
    for design in ["baseline_3tick", "abrupt_1tick"]:
        for seed in SEEDS:
            # We run adaptive Trigger C for robustness checks
            rob_tasks.append(("adaptive", "baseline_shock", seed, design, "Trigger_C"))
            rob_tasks.append(("interaction", "baseline_shock", seed, design, "Trigger_C"))
            
    with mp.Pool(processes=num_workers) as pool:
        rob_results = pool.map(run_robustness_worker, rob_tasks)
        
    rob_grouped = {}
    for r in rob_results:
        key = (r["shock_design"], r["regime"])
        if key not in rob_grouped:
            rob_grouped[key] = []
        rob_grouped[key].append(r)
        
    rob_summary = []
    for key, runs in rob_grouped.items():
        dsgn, reg = key
        label = "adaptive_Trigger_C" if reg == "adaptive" else "interaction"
        rob_summary.append({
            "shock_profile": dsgn,
            "regime": label,
            "revenue_per_vehicle": np.mean([x["revenue_per_vehicle"] for x in runs]),
            "service_rate": np.mean([x["service_rate"] for x in runs]),
            "overload_frequency": np.mean([x["overload_frequency"] for x in runs]),
            "spatial_demand_supply_mismatch": np.mean([x["spatial_imbalance"] for x in runs]),
            "price_volatility": np.mean([x["price_volatility"] for x in runs]),
            "price_oscillation_index": np.mean([x["oscillation_index"] for x in runs]),
            "vehicle_concentration": np.mean([x["vehicle_concentration"] for x in runs]),
            "intervention_frequency": np.mean([x["adaptive_active_ratio"] for x in runs]),
            "shock_phase_active_ticks": np.mean([x["shock_phase_active_ticks"] for x in runs]),
            "recovery_phase_active_ticks": np.mean([x["recovery_phase_active_ticks"] for x in runs])
        })
        
    rob_csv_path = os.path.join(OUT_DIR, "adaptive_abrupt_shock_results.csv")
    with open(rob_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rob_summary[0].keys())
        writer.writeheader()
        writer.writerows(rob_summary)

    # =========================================================================
    # COMPONENT 5 & 6: Recovery-Phase Diagnostics and Plotting
    # =========================================================================
    print("\n--- Running Component 5 & 6: Recovery Diagnostics and Plotting ---")
    rec_tasks = []
    for seed in SEEDS:
        rec_tasks.append(("adaptive", seed, "Trigger_C"))
        
    with mp.Pool(processes=num_workers) as pool:
        rec_results = pool.map(run_recovery_worker, rec_tasks)
        
    # Aggregate tick-by-tick averages across 50 seeds
    tick_stats = {}
    for run in rec_results:
        for record in run:
            t = record["tick"]
            if t not in tick_stats:
                tick_stats[t] = {
                    "spatial_imbalance": [],
                    "unmet_demand_ratio": [],
                    "price_dispersion": [],
                    "governance_active": []
                }
            tick_stats[t]["spatial_imbalance"].append(record["spatial_imbalance"])
            tick_stats[t]["unmet_demand_ratio"].append(record["unmet_demand_ratio"])
            tick_stats[t]["price_dispersion"].append(record["price_dispersion"])
            tick_stats[t]["governance_active"].append(record["governance_active"])
            
    averaged_history = []
    for t in sorted(tick_stats.keys()):
        averaged_history.append({
            "tick": t,
            "spatial_imbalance": np.mean(tick_stats[t]["spatial_imbalance"]),
            "unmet_demand_ratio": np.mean(tick_stats[t]["unmet_demand_ratio"]),
            "price_dispersion": np.mean(tick_stats[t]["price_dispersion"]),
            "governance_active": np.mean(tick_stats[t]["governance_active"])
        })
        
    rec_csv_path = os.path.join(OUT_DIR, "adaptive_recovery_diagnostic.csv")
    with open(rec_csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=averaged_history[0].keys())
        writer.writeheader()
        writer.writerows(averaged_history)
        
    # Component 6: Matplotlib Plot Generation
    print("Generating timeline plot...")
    ticks_plot = [x["tick"] for x in averaged_history]
    imb_plot = [x["spatial_imbalance"] for x in averaged_history]
    unmet_plot = [x["unmet_demand_ratio"] for x in averaged_history]
    gov_plot = [x["governance_active"] for x in averaged_history]
    
    fig, ax1 = plt.subplots(figsize=(10, 5))
    
    # Left Y-axis for Spatial Imbalance and Overload Ratio
    color_imb = "#e06666"
    color_unmet = "#ffd966"
    ax1.set_xlabel("Simulation Ticks", fontsize=11, fontweight="bold", labelpad=8)
    ax1.set_ylabel("Metric Ratio", fontsize=11, fontweight="bold")
    
    line1 = ax1.plot(ticks_plot, imb_plot, color=color_imb, label="Spatial Imbalance Index", linewidth=2)
    line2 = ax1.plot(ticks_plot, unmet_plot, color=color_unmet, label="Overload Ratio (Unmet / Effective)", linewidth=2)
    ax1.tick_params(axis='y')
    ax1.set_ylim(-0.02, 1.02)
    
    # Right Y-axis for Governance Active State
    ax2 = ax1.twinx()
    color_gov = "#6fa8dc"
    ax2.set_ylabel("Governance Activation Probability", color=color_gov, fontsize=11, fontweight="bold")
    line3 = ax2.plot(ticks_plot, gov_plot, color=color_gov, label="Governance Active State", linestyle="--", linewidth=2)
    ax2.tick_params(axis='y', labelcolor=color_gov)
    ax2.set_ylim(-0.05, 1.05)
    
    # Shading the shock period: Ticks 20 to 36
    ax1.axvspan(20, 36, color="grey", alpha=0.15, label="Demand Shock Window")
    
    # Adding titles and legends
    plt.title("Adaptive Governance Timeline (Trigger C): Shock and Recovery Dynamics (N=80)", fontsize=13, fontweight="bold", pad=12)
    
    # Combine legends from both axes
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines] + ["Demand Shock Window (Ticks 20-36)"]
    ax1.legend(lines, labels, loc="upper right", framealpha=0.9, fontsize=9)
    
    plt.tight_layout()
    plot_path = os.path.join(OUT_DIR, "adaptive_recovery_timeline.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"Time-series plot successfully saved to: {plot_path}")
    
    print("\n=========================================================================")
    print("               PIPELINE COMPLETION SUMMARY")
    print("=========================================================================")
    print(f"Output Directory:      {OUT_DIR}")
    print(f"1. Static Sweep CSV:   {sweep_csv_path}")
    print(f"2. Main Comparison:    {comp_csv_path}")
    print(f"3. Delta Sensitivity:  {delta_csv_path}")
    print(f"4. Threshold Sens:     {thresh_csv_path}")
    print(f"5. Persistence Sens:   {pers_csv_path}")
    print(f"6. Abrupt Shock CSV:   {rob_csv_path}")
    print(f"7. Recovery Diag CSV:  {rec_csv_path}")
    print(f"8. Timeline Plot PNG:  {plot_path}")
    print("=========================================================================")

if __name__ == "__main__":
    main()
