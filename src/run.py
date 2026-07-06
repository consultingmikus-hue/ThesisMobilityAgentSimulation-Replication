"""
Runner script for the thesis simulation.
Runs a simulation and prints summary statistics.
Saves detailed log history to the outputs/ directory.
"""

import os
import json
import argparse
from src.model import ThesisSimulationModel
from src.config import TOTAL_VEHICLES


def run_simulation(steps=50, fleet_size=TOTAL_VEHICLES, seed=42, output_file=None):
    """
    Run the simulation for a given number of steps and save/print results.
    """
    print(f"Initializing Thesis Simulation Model...")
    print(f"Parameters: Steps={steps}, Fleet Size={fleet_size}, Seed={seed}")
    
    # Initialize model
    model = ThesisSimulationModel(fleet_size=fleet_size, seed=seed)
    
    # Run steps
    for step_num in range(1, steps + 1):
        model.step()
        
    print(f"Simulation completed successfully.")
    
    # Extract final metrics
    history = model.history
    
    # Calculate overall aggregate metrics
    tot_new = sum(h["system"]["total_new_demand"] for h in history)
    tot_realized = sum(h["system"]["total_realized_demand"] for h in history)
    tot_served = sum(h["system"]["total_served_demand"] for h in history)
    avg_idle = sum(h["system"]["idle_vehicles"] for h in history) / len(history)
    avg_serving = sum(h["system"]["serving_vehicles"] for h in history) / len(history)
    avg_service_rate = sum(h["system"]["service_rate"] for h in history) / len(history)
    
    print("\n" + "="*50)
    print("              SIMULATION SUMMARY")
    print("="*50)
    print(f"Total Ticks/Steps Run:      {len(history)}")
    print(f"Total Raw Arrivals:         {tot_new}")
    print(f"Total Realized Demand:      {tot_realized}")
    print(f"Total Served Trips:         {tot_served}")
    print(f"Unmet Demand (End State):   {history[-1]['system']['total_unmet_demand']}")
    print(f"Average Service Rate:       {avg_service_rate:.2%}")
    print(f"Average Idle Fleet:         {avg_idle:.1f} vehicles")
    print(f"Average Serving Fleet:      {avg_serving:.1f} vehicles")
    print("="*50)
    
    # Print zone-level summaries
    print("\nZone-Level Average Performance:")
    print(f"{'Zone':<6} | {'New Dem':<8} | {'Served':<8} | {'Service %':<9} | {'Idle Fleet':<11}")
    print("-" * 52)
    for zone in model.baseline_prices.keys():
        z_new = sum(h["zones"][zone]["new_demand"] for h in history) / len(history)
        z_served = sum(h["zones"][zone]["served_demand"] for h in history) / len(history)
        z_idle = sum(h["zones"][zone]["idle_vehicles"] for h in history) / len(history)
        z_eff = sum(h["zones"][zone]["effective_demand"] for h in history)
        z_serv_tot = sum(h["zones"][zone]["served_demand"] for h in history)
        z_rate = z_serv_tot / z_eff if z_eff > 0 else 1.0
        print(f"{zone:<6} | {z_new:<8.2f} | {z_served:<8.2f} | {z_rate:<9.1%} | {z_idle:<11.1f}")
    print("="*50)

    # Save to file if output file specified
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"\nDetailed simulation logs saved to: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Thesis Simulation (Phase 1)")
    parser.add_argument("--steps", type=int, default=50, help="Number of ticks/steps to simulate")
    parser.add_argument("--fleet", type=int, default=TOTAL_VEHICLES, help="Total vehicles in simulation")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="outputs/simulation_history.json", help="Path to save output JSON log")
    
    args = parser.parse_args()
    
    run_simulation(
        steps=args.steps,
        fleet_size=args.fleet,
        seed=args.seed,
        output_file=args.output
    )
