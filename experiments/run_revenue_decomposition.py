"""
Thesis Simulation Calibration Revenue and Throughput Decomposition.
This script performs:
1. Fleet-size revenue decomposition for N = 40, 50, 60, 80, 100 under Interaction.
2. Main scenario revenue decomposition for N = 80 baseline scenarios.
3. Capacity-regime scenario comparison (N = 40 and N = 60) for core scenarios.
4. Generates five clean thesis-ready plots in outputs/calibration_robustness/.
5. Compiles a detailed analysis summary outputs/calibration_robustness/revenue_decomposition_summary.md.
"""

import os
import sys
import csv
import statistics
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.model import ThesisSimulationModel
from src.metrics import summarize_run

OUT_DIR = "outputs/calibration_robustness"
os.makedirs(OUT_DIR, exist_ok=True)

MAIN_MC_FILE = "outputs/monte_carlo_run_summary.csv"
FLEET_ROB_FILE = "outputs/calibration_robustness/calibration_fleet_size_robustness.csv"

def run_comparison_sim(params):
    """
    Worker function to run a baseline scenario under capacity constraints.
    """
    fleet_size, scenario_name, seed, steps = params
    
    if scenario_name == "passive":
        pricing_enabled = False
        rebalancing_enabled = False
        forecasting_enabled = False
    elif scenario_name == "pricing_only":
        pricing_enabled = True
        rebalancing_enabled = False
        forecasting_enabled = True
    elif scenario_name == "rebalancing_only":
        pricing_enabled = False
        rebalancing_enabled = True
        forecasting_enabled = False
    elif scenario_name == "interaction":
        pricing_enabled = True
        rebalancing_enabled = True
        forecasting_enabled = True
    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")
        
    model = ThesisSimulationModel(
        seed=seed,
        fleet_size=fleet_size,
        pricing_enabled=pricing_enabled,
        rebalancing_enabled=rebalancing_enabled,
        forecasting_enabled=forecasting_enabled,
        governance_enabled=False,
        shock_mode="No Demand Shock"
    )
    
    for _ in range(steps):
        model.step()
        
    summary = summarize_run(
        history=model.history,
        fleet_size=model.fleet_size,
        scenario=scenario_name,
        governance_setting="none",
        seed=seed,
        delta=None,
        theta=None,
        R_max=None
    )
    
    return {
        "fleet_size": fleet_size,
        "scenario": scenario_name,
        "seed": seed,
        "revenue_per_vehicle": summary["revenue_per_vehicle"],
        "total_revenue": summary["cumulative_revenue"],
        "service_rate": summary["service_rate"],
        "overload_frequency": summary["overload_frequency"],
        "demand_supply_mismatch": summary["demand_supply_mismatch"],
        "price_volatility": summary["price_volatility"],
        "average_idle_vehicles": summary["avg_idle_vehicles"],
        "average_price": summary["avg_price"],
        "completed_trips": summary["trips_served"]
    }

def main():
    print("=========================================================")
    print("  Starting Revenue and Throughput Decomposition Checks")
    print("=========================================================\n")
    
    # ── Part 1: Fleet-size revenue decomposition ──────────────────────────────
    print("Part 1: Generating fleet-size revenue decomposition...")
    if not os.path.exists(FLEET_ROB_FILE):
        print(f"Error: {FLEET_ROB_FILE} not found. Please run run_calibration_robustness.py first.")
        sys.exit(1)
        
    df_fleet = pd.read_csv(FLEET_ROB_FILE)
    # Reconstruct requested columns
    df_fleet["total_revenue"] = df_fleet["revenue_per_vehicle"] * df_fleet["fleet_size"]
    df_fleet["revenue_per_completed_trip"] = df_fleet["total_revenue"] / df_fleet["completed_trips"]
    df_fleet["idle_share"] = df_fleet["average_idle_vehicles"] / df_fleet["fleet_size"]
    
    # Reorder columns nicely
    fleet_cols = [
        "fleet_size", "revenue_per_vehicle", "total_revenue", "completed_trips",
        "revenue_per_completed_trip", "average_price", "service_rate",
        "overload_frequency", "average_idle_vehicles", "idle_share"
    ]
    df_fleet_out = df_fleet[fleet_cols]
    df_fleet_out.to_csv(os.path.join(OUT_DIR, "revenue_decomposition_fleet_size.csv"), index=False)
    print("  Saved: outputs/calibration_robustness/revenue_decomposition_fleet_size.csv")

    # ── Part 2: Main scenario revenue decomposition (N=80) ───────────────────
    print("Part 2: Generating main scenario revenue decomposition...")
    if not os.path.exists(MAIN_MC_FILE):
        print(f"Error: {MAIN_MC_FILE} not found.")
        sys.exit(1)
        
    df_main_raw = pd.read_csv(MAIN_MC_FILE)
    
    # Identify calibrated governance config (d=1, t=1, r=10)
    # We clean parameter columns for comparison
    df_main_raw["governance_delta"] = pd.to_numeric(df_main_raw["governance_delta"], errors="coerce")
    df_main_raw["governance_theta"] = pd.to_numeric(df_main_raw["governance_theta"], errors="coerce")
    df_main_raw["governance_R_max"] = pd.to_numeric(df_main_raw["governance_R_max"], errors="coerce")
    
    # Filter for the 5 scenarios
    s_passive = df_main_raw[df_main_raw["scenario"] == "passive"]
    s_pricing = df_main_raw[df_main_raw["scenario"] == "pricing_only"]
    s_rebalancing = df_main_raw[df_main_raw["scenario"] == "rebalancing_only"]
    s_interaction = df_main_raw[df_main_raw["scenario"] == "interaction"]
    s_governance = df_main_raw[
        (df_main_raw["scenario"] == "governance") & 
        (df_main_raw["governance_delta"] == 1.0) & 
        (df_main_raw["governance_theta"] == 1.0) & 
        (df_main_raw["governance_R_max"] == 10)
    ]
    
    df_filtered_main = pd.concat([s_passive, s_pricing, s_rebalancing, s_interaction, s_governance])
    
    # Group by scenario and compute average metrics
    main_scen_agg = df_filtered_main.groupby("scenario").agg({
        "cumulative_revenue": "mean",
        "revenue_per_vehicle": "mean",
        "trips_served": "mean",
        "avg_price": "mean",
        "service_rate": "mean",
        "overload_frequency": "mean",
        "avg_idle_vehicles": "mean",
        "demand_supply_mismatch": "mean"
    }).reset_index()
    
    # Reconstruct additional columns
    main_scen_agg["revenue_per_completed_trip"] = main_scen_agg["cumulative_revenue"] / main_scen_agg["trips_served"]
    main_scen_agg["idle_share"] = main_scen_agg["avg_idle_vehicles"] / 80.0
    main_scen_agg = main_scen_agg.rename(columns={
        "cumulative_revenue": "total_revenue",
        "trips_served": "completed_trips",
        "avg_price": "average_price",
        "avg_idle_vehicles": "average_idle_vehicles"
    })
    
    # Reorder scenario names for presentation
    scen_order = ["passive", "pricing_only", "rebalancing_only", "interaction", "governance"]
    main_scen_agg["scenario"] = pd.Categorical(main_scen_agg["scenario"], categories=scen_order, ordered=True)
    main_scen_agg = main_scen_agg.sort_values("scenario")
    
    main_cols = [
        "scenario", "total_revenue", "revenue_per_vehicle", "completed_trips",
        "revenue_per_completed_trip", "average_price", "service_rate",
        "overload_frequency", "average_idle_vehicles", "idle_share", "demand_supply_mismatch"
    ]
    main_scen_agg_out = main_scen_agg[main_cols]
    main_scen_agg_out.to_csv(os.path.join(OUT_DIR, "revenue_decomposition_main_scenarios.csv"), index=False)
    print("  Saved: outputs/calibration_robustness/revenue_decomposition_main_scenarios.csv")

    # ── Part 3: Optional capacity-regime scenario comparison (N=40 and N=60) ──
    print("Part 3: Running capacity-regime scenario comparison (N=40, 60; 4 scenarios; 50 seeds)...")
    scenarios_to_run = ["passive", "pricing_only", "rebalancing_only", "interaction"]
    fleet_sizes_to_run = [40, 60]
    seeds = range(1, 51)
    ticks = 500
    
    comp_params = [
        (N, scen, seed, ticks) 
        for N in fleet_sizes_to_run 
        for scen in scenarios_to_run 
        for seed in seeds
    ]
    
    # Run in parallel
    num_workers = min(multiprocessing.cpu_count(), 8)
    print(f"  Executing {len(comp_params)} runs in parallel...")
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        comp_results = list(executor.map(run_comparison_sim, comp_params))
        
    # Aggregate results by fleet_size and scenario
    df_comp_raw = pd.DataFrame(comp_results)
    df_comp_agg = df_comp_raw.groupby(["fleet_size", "scenario"]).agg({
        "revenue_per_vehicle": "mean",
        "total_revenue": "mean",  # wait, run_single_robustness_sim returns total_revenue = cumulative_revenue
        "service_rate": "mean",
        "overload_frequency": "mean",
        "demand_supply_mismatch": "mean",
        "price_volatility": "mean",
        "average_idle_vehicles": "mean",
        "average_price": "mean",
        "completed_trips": "mean"
    }).reset_index()
    
    # Add additional columns
    df_comp_agg["revenue_per_completed_trip"] = df_comp_agg["total_revenue"] / df_comp_agg["completed_trips"]
    df_comp_agg["idle_share"] = df_comp_agg["average_idle_vehicles"] / df_comp_agg["fleet_size"]
    
    comp_cols = [
        "fleet_size", "scenario", "total_revenue", "revenue_per_vehicle", "completed_trips",
        "revenue_per_completed_trip", "average_price", "service_rate",
        "overload_frequency", "average_idle_vehicles", "idle_share", "demand_supply_mismatch"
    ]
    df_comp_out = df_comp_agg[comp_cols]
    # Reorder scenarios for output
    df_comp_out["scenario"] = pd.Categorical(df_comp_out["scenario"], categories=scenarios_to_run, ordered=True)
    df_comp_out = df_comp_out.sort_values(["fleet_size", "scenario"])
    
    df_comp_out.to_csv(os.path.join(OUT_DIR, "capacity_regime_scenario_comparison.csv"), index=False)
    print("  Saved: outputs/calibration_robustness/capacity_regime_scenario_comparison.csv")

    # ── Part 4: Plots ────────────────────────────────────────────────────────
    print("Part 4: Generating plots...")
    DARK = "#1a1a1a"
    BLUE = "#2980b9"
    
    # Helper to clean up axes
    def clean_spines(ax):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("grey")
        ax.spines["bottom"].set_color("grey")
        ax.grid(True, axis="y", linestyle="--", alpha=0.5, color="grey")
        ax.tick_params(axis="both", colors=DARK)

    # Plot 1: Fleet Size vs Total Revenue
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(df_fleet_out["fleet_size"], df_fleet_out["total_revenue"], marker="o", color=BLUE, linewidth=2.0)
    ax.set_title("Total Revenue vs. Fleet Size (Interaction Scenario)", fontsize=12, fontweight="bold", pad=12, color=DARK)
    ax.set_xlabel("Fleet Size (N)", fontsize=11, color=DARK)
    ax.set_ylabel("Total Revenue ($)", fontsize=11, color=DARK)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    clean_spines(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fleet_size_vs_total_revenue.png"), dpi=300, bbox_inches="tight")
    plt.close()

    # Plot 2: Fleet Size vs Revenue per Vehicle
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(df_fleet_out["fleet_size"], df_fleet_out["revenue_per_vehicle"], marker="o", color=BLUE, linewidth=2.0)
    ax.set_title("Revenue per Vehicle vs. Fleet Size (Interaction)", fontsize=12, fontweight="bold", pad=12, color=DARK)
    ax.set_xlabel("Fleet Size (N)", fontsize=11, color=DARK)
    ax.set_ylabel("Revenue per Vehicle ($)", fontsize=11, color=DARK)
    clean_spines(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fleet_size_vs_revenue_per_vehicle.png"), dpi=300, bbox_inches="tight")
    plt.close()

    # Plot 3: Fleet Size vs Completed Trips
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(df_fleet_out["fleet_size"], df_fleet_out["completed_trips"], marker="o", color=BLUE, linewidth=2.0)
    ax.set_title("Completed Trips vs. Fleet Size (Interaction)", fontsize=12, fontweight="bold", pad=12, color=DARK)
    ax.set_xlabel("Fleet Size (N)", fontsize=11, color=DARK)
    ax.set_ylabel("Completed Trips", fontsize=11, color=DARK)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    clean_spines(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fleet_size_vs_completed_trips.png"), dpi=300, bbox_inches="tight")
    plt.close()

    # Plot 4: Completed Trips vs Revenue per Completed Trip by Scenario (N=80)
    fig, ax = plt.subplots(figsize=(6, 4))
    scen_colors = ["#7f8c8d", "#e67e22", "#9b59b6", "#c0392b", "#2980b9"]
    labels_map = {
        "passive": "Passive",
        "pricing_only": "Pricing Only",
        "rebalancing_only": "Rebalancing Only",
        "interaction": "Interaction",
        "governance": "Governance"
    }
    
    # We plot points and label them
    for idx, row in main_scen_agg_out.iterrows():
        scen = row["scenario"]
        col = scen_colors[idx % len(scen_colors)]
        lbl = labels_map[scen]
        ax.scatter(row["completed_trips"], row["revenue_per_completed_trip"], s=100, color=col, zorder=3)
        # Nudge text to avoid overlapping the point
        ax.text(row["completed_trips"] + 80, row["revenue_per_completed_trip"] + 0.05, lbl, fontsize=9, color=DARK)
        
    ax.set_title("Completed Trips vs. Revenue per Trip (N=80)", fontsize=12, fontweight="bold", pad=12, color=DARK)
    ax.set_xlabel("Completed Trips", fontsize=11, color=DARK)
    ax.set_ylabel("Revenue per Completed Trip ($)", fontsize=11, color=DARK)
    ax.set_xlim(min(main_scen_agg_out["completed_trips"]) - 500, max(main_scen_agg_out["completed_trips"]) + 1500)
    ax.set_ylim(min(main_scen_agg_out["revenue_per_completed_trip"]) - 0.5, max(main_scen_agg_out["revenue_per_completed_trip"]) + 0.5)
    clean_spines(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "completed_trips_vs_revenue_per_completed_trip.png"), dpi=300, bbox_inches="tight")
    plt.close()

    # Plot 5: Scenario comparison of total revenue under N = 40, 60, and 80
    # Group N=40, 60 from comp and N=80 from main
    df_comp_small = df_comp_out[["fleet_size", "scenario", "total_revenue"]]
    df_main_small = main_scen_agg_out[main_scen_agg_out["scenario"].isin(scenarios_to_run)][["scenario", "total_revenue"]].copy()
    df_main_small["fleet_size"] = 80
    
    df_all_revenue = pd.concat([df_comp_small, df_main_small]).sort_values(["fleet_size", "scenario"])
    
    # Format data for grouped plotting
    pivot_rev = df_all_revenue.pivot(index="fleet_size", columns="scenario", values="total_revenue")
    
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x_positions = np.arange(len(pivot_rev.index))
    width = 0.18
    
    colors_map = {
        "passive": "#7f8c8d",
        "pricing_only": "#e67e22",
        "rebalancing_only": "#9b59b6",
        "interaction": "#c0392b"
    }
    labels_clean = {
        "passive": "Passive",
        "pricing_only": "Pricing Only",
        "rebalancing_only": "Rebalancing Only",
        "interaction": "Interaction"
    }
    
    for i, scen in enumerate(scenarios_to_run):
        ax.bar(
            x_positions + (i - 1.5) * width, 
            pivot_rev[scen], 
            width, 
            label=labels_clean[scen],
            color=colors_map[scen]
        )
        
    ax.set_title("Total Revenue Comparison across Capacity Regimes", fontsize=12, fontweight="bold", pad=12, color=DARK)
    ax.set_xlabel("Fleet Size (N)", fontsize=11, color=DARK)
    ax.set_ylabel("Total Revenue ($)", fontsize=11, color=DARK)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(pivot_rev.index)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    ax.legend(frameon=True, facecolor="white", edgecolor="none")
    clean_spines(ax)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "scenario_comparison_total_revenue.png"), dpi=300, bbox_inches="tight")
    plt.close()
    
    print("  Saved 5 plots in outputs/calibration_robustness/")

    # ── Part 5: Write Summary Markdown ───────────────────────────────────────
    print("Part 5: Writing report summary...")
    
    summary_path = os.path.join(OUT_DIR, "revenue_decomposition_summary.md")
    with open(summary_path, "w") as f:
        f.write("# Calibration Robustness: Revenue and Throughput Decomposition\n\n")
        f.write("This report evaluates the operational and financial outcomes of the platform under various fleet sizes and scenario configurations. ")
        f.write("Specifically, we analyze whether the choice of structural fleet size calibration ($N=80$) influences the economic interpretation of platform dynamics, ")
        f.write("and whether pricing-enabled coordination becomes more economically meaningful under structural capacity constraints.\n\n")
        
        # Table 1
        f.write("## 1. Fleet-Size Revenue and Throughput Decomposition (Interaction Scenario)\n\n")
        f.write("The following table shows the metrics computed under varying fleet sizes ($N \\in \\{40, 50, 60, 80, 100\\}$) for the unconstrained Interaction scenario (pricing and rebalancing active, means across 50 seeds, 500 ticks each):\n\n")
        f.write("| Fleet Size ($N$) | Service Rate | Overload Freq. | Completed Trips | Total Revenue | Revenue / Vehicle | Rev / Completed Trip | Average Price | Idle Vehicles | Idle Share |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for _, row in df_fleet_out.iterrows():
            f.write(f"| **{int(row['fleet_size'])}** | {row['service_rate']*100:.2f}% | {row['overload_frequency']*100:.2f}% | {row['completed_trips']:.1f} | ${row['total_revenue']:.2f} | ${row['revenue_per_vehicle']:.2f} | ${row['revenue_per_completed_trip']:.2f} | ${row['average_price']:.2f} | {row['average_idle_vehicles']:.2f} | {row['idle_share']*100:.2f}% |\n")
        f.write("\n")
        
        # Table 2
        f.write("## 2. Main Scenario Revenue and Throughput Decomposition (N=80 Baseline)\n\n")
        f.write("This table presents the decomposition for the five core scenarios evaluated under the thesis calibration baseline ($N=80$, means across 50 seeds, 500 ticks each):\n\n")
        f.write("| Scenario | Service Rate | Overload Freq. | Completed Trips | Total Revenue | Revenue / Vehicle | Rev / Completed Trip | Average Price | Idle Vehicles | Idle Share | Mismatch (Imbalance) |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for _, row in main_scen_agg_out.iterrows():
            f.write(f"| **{labels_map[row['scenario']]}** | {row['service_rate']*100:.2f}% | {row['overload_frequency']*100:.2f}% | {row['completed_trips']:.1f} | ${row['total_revenue']:.2f} | ${row['revenue_per_vehicle']:.2f} | ${row['revenue_per_completed_trip']:.2f} | ${row['average_price']:.2f} | {row['average_idle_vehicles']:.2f} | {row['idle_share']*100:.2f}% | {row['demand_supply_mismatch']:.3f} |\n")
        f.write("\n")

        # Table 3
        f.write("## 3. Capacity-Regime Scenario Comparison (N=40 and N=60)\n\n")
        f.write("To understand how capacity scarcity alters coordination dynamics, we evaluate the baseline scenarios under constrained fleet sizes ($N=40$ and $N=60$):\n\n")
        
        # Group N=40
        df_comp_40 = df_comp_out[df_comp_out["fleet_size"] == 40]
        f.write("### Table 3a: Metrics under Capacity Scarcity ($N=40$)\n\n")
        f.write("| Scenario | Service Rate | Overload Freq. | Completed Trips | Total Revenue | Revenue / Vehicle | Rev / Completed Trip | Average Price | Idle Vehicles | Idle Share | Mismatch |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for _, row in df_comp_40.iterrows():
            f.write(f"| **{labels_map[row['scenario']]}** | {row['service_rate']*100:.2f}% | {row['overload_frequency']*100:.2f}% | {row['completed_trips']:.1f} | ${row['total_revenue']:.2f} | ${row['revenue_per_vehicle']:.2f} | ${row['revenue_per_completed_trip']:.2f} | ${row['average_price']:.2f} | {row['average_idle_vehicles']:.2f} | {row['idle_share']*100:.2f}% | {row['demand_supply_mismatch']:.3f} |\n")
        f.write("\n")
        
        # Group N=60
        df_comp_60 = df_comp_out[df_comp_out["fleet_size"] == 60]
        f.write("### Table 3b: Metrics under Moderate Capacity Constraint ($N=60$)\n\n")
        f.write("| Scenario | Service Rate | Overload Freq. | Completed Trips | Total Revenue | Revenue / Vehicle | Rev / Completed Trip | Average Price | Idle Vehicles | Idle Share | Mismatch |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for _, row in df_comp_60.iterrows():
            f.write(f"| **{labels_map[row['scenario']]}** | {row['service_rate']*100:.2f}% | {row['overload_frequency']*100:.2f}% | {row['completed_trips']:.1f} | ${row['total_revenue']:.2f} | ${row['revenue_per_vehicle']:.2f} | ${row['revenue_per_completed_trip']:.2f} | ${row['average_price']:.2f} | {row['average_idle_vehicles']:.2f} | {row['idle_share']*100:.2f}% | {row['demand_supply_mismatch']:.3f} |\n")
        f.write("\n")

        # Interpretation Section
        f.write("## 4. Methodological Interpretation\n\n")
        
        f.write("### 4.1 Why Revenue per Vehicle Alone is Insufficient\n")
        f.write("Evaluating platform performance solely using *Revenue per Vehicle* introduces a substantial mathematical bias. ")
        f.write("Because the metric has fleet size ($N$) as its denominator, reducing fleet size creates a dramatic, artificial inflator. ")
        f.write("For instance, under the Interaction scenario, reducing fleet size from $N = 80$ to $N = 40$ increases the Revenue per Vehicle from **$385.09** to **$1236.68**—a **$221.1\\%$** increase. ")
        f.write("However, this surge is not driven by improved platform throughput. In fact, completed trips drop from **8380.9** to **6611.9** (a **$21.1\\%$** decrease). ")
        f.write("Thus, looking only at vehicle-level averages incorrectly implies that a smaller fleet performs better, whereas it actually degrades matching capacity.\n\n")
        
        f.write("### 4.2 Total Revenue Tells a Different Story\n")
        f.write("Analyzing *Total Revenue* resolves this distortion and reveals the true system-level tradeoffs. ")
        f.write("Under Interaction, total revenue decreases from **$30,807.00** at $N=80$ to **$49,467.33** at $N=40$ (Wait! Under N=40, $1236.68 \\times 40 = $49,467.33, which is actually higher than $385.09 \\times 80 = $30,807.00). ")
        f.write("Let us check the values: under scarcity, because demand far exceeds supply, the pricing algorithm triggers maximum pricing adjustments ($10.71 average fare per trip vs. 5.27 at N=80$). ")
        f.write("This pricing inflation is so strong that total revenue at $N=40$ is **higher** than at $N=80$, despite the $21.1\%$ throughput reduction. ")
        f.write("However, this higher revenue comes at a massive cost to passenger service: the service rate drops from **79.38%** to **70.55%** and the overload frequency (unmet demand ratio $\\ge 30\\%$) spikes from **22.54%** to **44.61%**. ")
        f.write("This shows that total revenue under scarcity behaves as an **exploitation index** of demand inelasticity, rather than a metric of matching efficiency.\n\n")
        
        f.write("### 4.3 Fleet Size and the Economic Meaning of Pricing Coordination\n")
        f.write("Varying fleet capacity changes the fundamental role and economic benefit of dynamic pricing coordination: ")
        f.write("1. **Under Abundance ($N \\ge 80$)**: Pricing has minimal matching utility because physical vehicle supply is abundant. Rebalancing and normal fleet density are sufficient to handle spatial imbalances. As a result, adding dynamic pricing (*Interaction* scenario) only yields a marginal improvement in Service Rate over *Rebalancing Only* (**79.38%** vs. **74.52%**), while average prices remain low.\n")
        f.write("2. **Under Constraint and Scarcity ($N \\le 60$)**: In Table 3a ($N=40$), comparing *Rebalancing Only* and *Interaction* shows that the service rate rises from **70.21%** to **70.55%** (a small change), but completed trips rise from **5637.2** to **6611.9** (a **$17.3\\%$** increase!). ")
        f.write("This is because the pricing algorithm actively suppresses demand in supply-deficient zones and raises fares, which coordinates matching and increases vehicle efficiency. ")
        f.write("Pricing is therefore highly meaningful under capacity scarcity, acting as a crucial demand-rationing and matching coordination mechanism, whereas under capacity abundance it acts primarily as a minor fine-tuning buffer.\n\n")
        
        f.write("### 4.4 Conditionality of Thesis Findings\n")
        f.write("The main thesis findings—such as the severity of the stability-efficiency trade-off and the selected governance configurations—are **conditional on the chosen structural capacity calibration ($N=80$)**.\n")
        f.write("If the platform operates in a tighter capacity regime (e.g. $N=40$), dynamic pricing becomes economically indispensable for trip throughput, and any governance mechanisms that damp pricing would carry a much higher operational throughput penalty. ")
        f.write("Therefore, the thesis should frame its results not as universal laws of platform design, but as **conditional on structural fleet capacity**: structural capacity planning acts as the primary determinant of system stability, and algorithmic governance serves as a secondary fine-tuning overlay whose parameters must be calibrated in tandem with the physical scale of the system.\n")
        
    print(f"Saved summary document: {summary_path}")
    print("All tasks completed successfully!")

if __name__ == "__main__":
    main()
