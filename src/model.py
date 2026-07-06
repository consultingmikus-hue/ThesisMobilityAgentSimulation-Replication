"""
Model module for the thesis simulation.
Implements the main Mesa Model class: ThesisSimulationModel.
Orchestrates spatial zones, demand generation, matching logic, and metrics.
Supports dynamic pricing, heuristic rebalancing, forecasting, governance, and demand shocks.
"""

import math
from mesa import Model
from src.config import ZONES, TRAVEL_TIMES, DESTINATION_PROBS, DEMAND_LAMBDAS, BASELINE_PRICES, BETA, TOTAL_VEHICLES
from src.agents import VehicleAgent, VehicleState


class ThesisSimulationModel(Model):
    """
    ThesisSimulationModel orchestrates the simulation.
    It manages the spatial zones, demand generation, vehicle agents, 
    matching process, and metrics tracking.
    
    One simulation tick represents approximately five minutes of platform operations. 
    This interval reflects short matching cycles and stylized urban travel times 
    between zones within the platform environment.
    """
    
    # Rate of unmet demand carried over to the next tick (50% patience assumption)
    BACKLOG_CARRYOVER_RATE = 0.5

    def __init__(self, 
                 fleet_size=TOTAL_VEHICLES, 
                 beta=BETA, 
                 lambdas=DEMAND_LAMBDAS, 
                 baseline_prices=BASELINE_PRICES, 
                 travel_times=TRAVEL_TIMES, 
                 destination_probs=DESTINATION_PROBS,
                 seed=None,
                 pricing_enabled=False,
                 rebalancing_enabled=False,
                 forecasting_enabled=False,  # NOTE: Only controls pricing forecast contribution (alpha_f term)
                 governance_enabled=False,
                 shock_enabled=False,
                 shock_mode=None,
                 alpha=0.3,
                 alpha_f=0.1,
                 omega=0.3,
                 theta=1.0,
                 delta=2.0,
                 R_max=10,
                 rebalancing_horizon=1,
                 adaptive_governance=False,
                 adaptive_governance_threshold=0.15,
                 shock_intensity=4.0):
        """
        Initialize the simulation model.
        
        Args:
            fleet_size: Total number of vehicles in the system.
            beta: Price elasticity coefficient for demand.
            lambdas: Dictionary of Poisson demand rates per zone.
            baseline_prices: Dictionary of baseline prices per zone.
            travel_times: Dictionary representing the travel times between zones.
            destination_probs: Dictionary representing transition probabilities between zones.
            seed: Seed for reproducibility.
            pricing_enabled: Dynamic pricing toggle.
            rebalancing_enabled: Vehicle rebalancing toggle.
            forecasting_enabled: Pricing forecast toggle (forecast demand and rebalancing use are always enabled).
            governance_enabled: Governance constraints toggle.
            shock_enabled: Demand shock scenario toggle (ticks 20-35).
            shock_mode: Demand shock mode ("No Demand Shock", "Demand Shock", "Repeated Demand Shocks").
            alpha: Dynamic pricing sensitivity parameter.
            omega: Exponential smoothing factor for forecasting.
            theta: Rebalancing activation threshold under governance.
            delta: Max price adjustment per step under governance.
            R_max: Max rebalancing dispatches per step under governance.
        """
        super().__init__(seed=seed)
        
        self.fleet_size = fleet_size
        self.beta = beta
        self.lambdas = lambdas.copy()
        self.baseline_prices = baseline_prices.copy()
        self.travel_times = travel_times
        self.destination_probs = destination_probs
        
        # Scenarios and control parameters
        self.pricing_enabled = pricing_enabled
        self.rebalancing_enabled = rebalancing_enabled
        self.forecasting_enabled = forecasting_enabled  # NOTE: Only controls forecast term contribution to pricing updates
        self.governance_enabled = governance_enabled
        
        if shock_mode is not None:
            self.shock_mode = shock_mode
        else:
            self.shock_mode = "Demand Shock" if shock_enabled else "No Demand Shock"
            
        self.alpha = alpha
        self.alpha_f = alpha_f
        self.omega = omega
        self.theta = theta
        self.delta = delta
        self.R_max = R_max
        self.rebalancing_horizon = rebalancing_horizon
        self.adaptive_governance = adaptive_governance
        self.adaptive_governance_threshold = adaptive_governance_threshold
        self.shock_intensity = shock_intensity
        
        # State variables
        self.unmet_demand = {zone: 0 for zone in ZONES}
        self.prices = {zone: baseline_prices[zone] for zone in ZONES}
        self.forecast_demand = {zone: self.lambdas[zone] for zone in ZONES}
        
        # Seeded forecast history or historical demand for the first step
        self.last_demand = {zone: self.lambdas[zone] for zone in ZONES}
        self.last_effective_demand = {zone: self.lambdas[zone] for zone in ZONES}
        
        # Initialize fleet and distribute vehicles across zones as evenly as possible
        zones_list = list(ZONES)
        for i in range(self.fleet_size):
            zone = zones_list[i % len(zones_list)]
            VehicleAgent(model=self, initial_zone=zone)
            
        # Log of step-by-step metrics
        self.history = []

    @property
    def shock_enabled(self):
        """Getter for shock_enabled (backward compatibility)."""
        return self.shock_mode != "No Demand Shock"
        
    @shock_enabled.setter
    def shock_enabled(self, value):
        """Setter for shock_enabled (backward compatibility)."""
        if not value:
            self.shock_mode = "No Demand Shock"
        elif self.shock_mode == "No Demand Shock":
            self.shock_mode = "Demand Shock"

    @property
    def is_shock_active(self):
        """Check if a demand shock is active at the current step."""
        if self.shock_mode == "No Demand Shock":
            return False
        elif self.shock_mode == "Demand Shock":
            return 20 <= self.steps <= 35
        elif self.shock_mode == "Repeated Demand Shocks":
            return self.steps >= 20 and (self.steps - 20) % 40 <= 15
        return False

    def get_shock_multiplier(self):
        """
        Calculate the dynamic demand shock multiplier for the current step.
        Supports:
        - "No Demand Shock": returns 1.0
        - "Demand Shock": active ticks 20-36
        - "Repeated Demand Shocks": active ticks 20-36, 60-76, 100-116, ... repeating every 40 ticks
        """
        if self.shock_mode == "No Demand Shock":
            return 1.0
            
        t = self.steps
        peak_mult = self.shock_intensity
        if self.shock_mode == "Demand Shock":
            if t <= 19:
                return 1.0
            elif t <= 22:
                # Linear ramp-up from 1.0 at t=19 to peak_mult at t=22
                return 1.0 + (peak_mult - 1.0) * (t - 19) / 3.0
            elif t <= 33:
                # Peak phase
                return peak_mult
            elif t <= 36:
                # Linear ramp-down from peak_mult at t=33 to 1.0 at t=36
                return 1.0 + (peak_mult - 1.0) * (36 - t) / 3.0
            else:
                return 1.0
                
        elif self.shock_mode == "Repeated Demand Shocks":
            if t < 20:
                return 1.0
            t_rel = (t - 20) % 40
            if t_rel <= 2:
                # Linear ramp-up
                return 1.0 + (peak_mult - 1.0) * (t_rel + 1) / 3.0
            elif t_rel <= 13:
                # Peak phase
                return peak_mult
            elif t_rel <= 16:
                # Linear ramp-down
                return 1.0 + (peak_mult - 1.0) * (16 - t_rel) / 3.0
            else:
                return 1.0
        
        return 1.0

    def _poisson_draw(self, lam):
        """
        Generate a Poisson random variable using Knuth's method.
        Uses self.random to ensure reproducibility across runs.
        """
        if lam <= 0:
            return 0
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= self.random.random()
        return k - 1

    def step(self):
        """
        Execute a single simulation tick.
        Follows the operational sequence:
        0. Adaptive Governance (update constraints based on trigger state)
        1. Transit update (decrement time_left, handle arrivals)
        2. Forecast update (exponential smoothing)
        3. Dynamic Pricing (feedback loop using previous imbalance)
        4. Demand generation (Poisson + Price response + Unmet carryover)
        5. Trip assignment (Matching idle vehicles to demand)
        6. Vehicle rebalancing (Reposition surplus to deficit zones)
        7. Metrics logging
        """
        # --- 0. Adaptive Governance Update ---
        if self.governance_enabled and self.adaptive_governance:
            is_stressed = False
            if len(self.history) > 0:
                last_imb = self.history[-1]["system"]["spatial_imbalance"]
                is_stressed = (last_imb > self.adaptive_governance_threshold)
                
            if is_stressed:
                # Stress State: Dampen pricing changes but leave rebalancing fully open
                self.delta = 2.0
                self.theta = 0.0
                self.R_max = 999
            else:
                # Normal State: Unconstrained pricing and rebalancing (interaction behavior)
                self.delta = 999.0
                self.theta = 0.0
                self.R_max = 999

        # --- 1. Transit Update ---
        for agent in self.agents:
            agent.step()
            
        # Determine current drivers physically in each zone (idle)
        zone_idle_drivers = {
            zone: sum(1 for v in self.agents if v.state == VehicleState.IDLE and v.current_zone == zone)
            for zone in ZONES
        }
        zone_total_drivers = {
            zone: sum(1 for v in self.agents if v.current_zone == zone)
            for zone in ZONES
        }

        # --- 2. Forecast Update ---
        # NOTE: Forecast demand is always calculated internally as part of core architecture.
        for zone in ZONES:
            self.forecast_demand[zone] = (
                self.omega * self.last_demand[zone] + 
                (1.0 - self.omega) * self.forecast_demand[zone]
            )

        # --- 3. Dynamic Pricing ---
        if self.pricing_enabled:
            active_delta = self.delta
            
            for zone in ZONES:
                # Imbalance from previous step: last_effective - last_total
                imbalance = self.last_effective_demand[zone] - zone_total_drivers[zone]
                
                # Pricing update with feedback loop
                price_delta = self.alpha * imbalance
                
                # Add forecasting adjustment if pricing forecast contribution is active
                if self.forecasting_enabled:
                    forecast_imbalance = self.forecast_demand[zone] - zone_total_drivers[zone]
                    price_delta += self.alpha_f * forecast_imbalance
                
                new_price = self.prices[zone] + price_delta
                
                # Governance rate limit
                if self.governance_enabled:
                    change = new_price - self.prices[zone]
                    change = max(-active_delta, min(active_delta, change))
                    new_price = self.prices[zone] + change
                
                # Boundaries (prices must be positive, min price of 1.0)
                self.prices[zone] = max(1.0, new_price)
        else:
            # Static pricing
            for zone in ZONES:
                self.prices[zone] = self.baseline_prices[zone]

        # --- 4. Demand Generation ---
        new_demand = {}
        realized_demand = {}
        effective_demand = {}
        
        shock_mult = self.get_shock_multiplier()
        for zone in ZONES:
            lambda_val = self.lambdas[zone]
            if zone == "C":
                lambda_val *= shock_mult
                
            raw_arrival = self._poisson_draw(lambda_val)
            
            # Price elasticity response
            price = self.prices[zone]
            realized = max(0, int(round(raw_arrival - self.beta * price)))
            
            # Carry over 50% of unmet demand from last tick (representing customer patience)
            unmet_prev = self.unmet_demand[zone]
            effective = realized + int(round(self.BACKLOG_CARRYOVER_RATE * unmet_prev))
            
            new_demand[zone] = raw_arrival
            realized_demand[zone] = realized
            effective_demand[zone] = effective
            
            # Save for next step pricing calculations
            self.last_demand[zone] = realized
            self.last_effective_demand[zone] = effective

        # --- 5. Trip Assignment (Matching) ---
        served_demand = {}
        
        for zone in ZONES:
            eff = effective_demand[zone]
            
            # Get idle vehicles currently in this zone
            idle_vehicles = [
                v for v in self.agents 
                if v.state == VehicleState.IDLE and v.current_zone == zone
            ]
            self.random.shuffle(idle_vehicles)
            
            num_served = min(len(idle_vehicles), eff)
            served_demand[zone] = num_served
            
            for i in range(num_served):
                vehicle = idle_vehicles[i]
                probs = self.destination_probs[zone]
                dest = self.random.choices(list(probs.keys()), weights=list(probs.values()))[0]
                t_time = self.travel_times[zone][dest]
                vehicle.assign_trip(origin=zone, destination=dest, travel_time=t_time)
                
            # Store unmet demand for the next tick
            self.unmet_demand[zone] = eff - num_served

        # --- 6. Vehicle Rebalancing ---
        total_rebalanced_this_step = 0
        
        if self.rebalancing_enabled:
            # Recompute idle drivers after trip matching
            current_idle = {
                zone: sum(1 for v in self.agents if v.state == VehicleState.IDLE and v.current_zone == zone)
                for zone in ZONES
            }
            
            # Count inbound vehicles already moving toward each zone (both serving and rebalancing)
            inbound_vehicles = {
                zone: sum(1 for v in self.agents if v.state in (VehicleState.SERVING, VehicleState.REBALANCING) and v.destination_zone == zone and v.time_left <= self.rebalancing_horizon)
                for zone in ZONES
            }
            
            # Calculate gap: Expected Demand - (current idle + inbound vehicles)
            # NOTE: Rebalancing always uses forecast_demand as part of core architecture.
            gaps = {
                zone: self.forecast_demand[zone] - current_idle[zone] - inbound_vehicles[zone]
                for zone in ZONES
            }
            
            # Compute deficits and surpluses
            deficits = {}
            surpluses = {}
            for zone in ZONES:
                gap = gaps[zone]
                if self.governance_enabled:
                    deficits[zone] = max(0, int(round(gap - self.theta)))
                    surpluses[zone] = max(0, int(round(-gap - self.theta)))
                else:
                    deficits[zone] = max(0, int(round(gap)))
                    surpluses[zone] = max(0, int(round(-gap)))

            # Evaluate scoring rules for rebalancing: Score_ki = Deficit_i / TravelTime_ki
            rebalance_options = []
            for d_zone in ZONES:
                if deficits[d_zone] > 0:
                    for s_zone in ZONES:
                        if surpluses[s_zone] > 0 and d_zone != s_zone:
                            dist = self.travel_times[s_zone][d_zone]
                            score = deficits[d_zone] / dist
                            rebalance_options.append((score, s_zone, d_zone))
                            
            # Sort options descending by score
            rebalance_options.sort(reverse=True, key=lambda x: x[0])
            
            active_R_max = self.R_max
            
            # Execute rebalancing matches
            for score, s_zone, d_zone in rebalance_options:
                # Check limits
                if deficits[d_zone] <= 0 or surpluses[s_zone] <= 0:
                    continue
                if self.governance_enabled and total_rebalanced_this_step >= active_R_max:
                    break
                    
                idle_in_s = [
                    v for v in self.agents 
                    if v.state == VehicleState.IDLE and v.current_zone == s_zone
                ]
                
                num_to_rebalance = min(len(idle_in_s), deficits[d_zone], surpluses[s_zone])
                if self.governance_enabled:
                    num_to_rebalance = min(num_to_rebalance, active_R_max - total_rebalanced_this_step)
                    
                for i in range(num_to_rebalance):
                    vehicle = idle_in_s[i]
                    travel_time = self.travel_times[s_zone][d_zone]
                    vehicle.assign_rebalance(origin=s_zone, destination=d_zone, travel_time=travel_time)
                    
                deficits[d_zone] -= num_to_rebalance
                surpluses[s_zone] -= num_to_rebalance
                total_rebalanced_this_step += num_to_rebalance

        # --- 7. Metrics Logging ---
        self._log_metrics(new_demand, realized_demand, effective_demand, served_demand, total_rebalanced_this_step, zone_idle_drivers)

    def _log_metrics(self, new_demand, realized_demand, effective_demand, served_demand, total_rebalanced, idle_before_matching):
        """Log state variables and metrics for the current tick."""
        total_fleet = len(self.agents)
        
        # Spatial Imbalance (mean absolute difference between effective demand and idle vehicles across zones, normalized by fleet size)
        raw_imbalance = sum(abs(effective_demand[zone] - idle_before_matching[zone]) for zone in ZONES) / len(ZONES)
        spatial_imbalance = raw_imbalance / total_fleet if total_fleet > 0 else 0.0
        
        # Total revenue in this step (served demand * price)
        step_revenue = sum(served_demand[zone] * self.prices[zone] for zone in ZONES)
        
        step_metrics = {
            "step": self.steps,
            "system": {
                "shock_mode": self.shock_mode,
                "total_new_demand": sum(new_demand.values()),
                "total_realized_demand": sum(realized_demand.values()),
                "total_effective_demand": sum(effective_demand.values()),
                "total_served_demand": sum(served_demand.values()),
                "total_unmet_demand": sum(self.unmet_demand.values()),
                "idle_vehicles": sum(1 for v in self.agents if v.state == VehicleState.IDLE),
                "serving_vehicles": sum(1 for v in self.agents if v.state == VehicleState.SERVING),
                "rebalancing_vehicles": sum(1 for v in self.agents if v.state == VehicleState.REBALANCING),
                "total_rebalanced_dispatched": total_rebalanced,
                "revenue": step_revenue,
                "spatial_imbalance": spatial_imbalance,
                "imbalance_index": spatial_imbalance,
            },
            "zones": {}
        }
        
        # Calculate system-wide service rate & fleet utilization
        eff_total = step_metrics["system"]["total_effective_demand"]
        served_total = step_metrics["system"]["total_served_demand"]
        step_metrics["system"]["service_rate"] = served_total / eff_total if eff_total > 0 else 1.0
        
        idle_total = step_metrics["system"]["idle_vehicles"]
        serving_total = step_metrics["system"]["serving_vehicles"]
        step_metrics["system"]["utilization"] = (total_fleet - idle_total) / total_fleet if total_fleet > 0 else 0.0
        step_metrics["system"]["fleet_utilization"] = serving_total / total_fleet if total_fleet > 0 else 0.0
        
        # Collect zone-level metrics
        for zone in ZONES:
            zone_idle = sum(
                1 for v in self.agents 
                if v.state == VehicleState.IDLE and v.current_zone == zone
            )
            zone_serving = sum(
                1 for v in self.agents 
                if v.state == VehicleState.SERVING and v.origin_zone == zone
            )
            zone_rebalancing = sum(
                1 for v in self.agents 
                if v.state == VehicleState.REBALANCING and v.origin_zone == zone
            )
            
            eff_z = effective_demand[zone]
            served_z = served_demand[zone]
            
            step_metrics["zones"][zone] = {
                "price": self.prices[zone],
                "new_demand": new_demand[zone],
                "realized_demand": realized_demand[zone],
                "effective_demand": eff_z,
                "served_demand": served_z,
                "unmet_demand": self.unmet_demand[zone],
                "idle_vehicles": zone_idle,
                "serving_vehicles": zone_serving,
                "rebalancing_vehicles": zone_rebalancing,
                "total_vehicles": zone_idle,
                "service_rate": served_z / eff_z if eff_z > 0 else 1.0
            }
            
        self.history.append(step_metrics)
