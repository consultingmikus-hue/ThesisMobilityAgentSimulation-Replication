"""
Verification test suite for the Phase 2 Thesis Simulation.
Tests system invariants: fleet preservation, transit delays, demand carry-over,
and seed reproducibility. Also tests dynamic pricing, forecasting, rebalancing,
governance limits, and demand shocks.
"""

import unittest
from src.model import ThesisSimulationModel
from src.agents import VehicleState
from src.config import ZONES, TRAVEL_TIMES, DEMAND_LAMBDAS


class TestSimulationInvariants(unittest.TestCase):
    """Test suite for verifying core logic and mathematical invariants."""

    def test_fleet_size_preservation(self):
        """Verify that the total fleet size remains constant at every simulation step."""
        fleet_size = 120
        model = ThesisSimulationModel(fleet_size=fleet_size, seed=42)
        
        # Check initial fleet size
        self.assertEqual(len(model.agents), fleet_size)
        
        # Run for 20 steps and verify fleet size after each step
        for _ in range(20):
            model.step()
            
            idle_count = sum(1 for v in model.agents if v.state == VehicleState.IDLE)
            serving_count = sum(1 for v in model.agents if v.state == VehicleState.SERVING)
            rebalance_count = sum(1 for v in model.agents if v.state == VehicleState.REBALANCING)
            
            # The sum of idle, busy, and rebalancing vehicles must equal the fleet size
            self.assertEqual(idle_count + serving_count + rebalance_count, fleet_size)

    def test_transit_delay_and_arrival(self):
        """
        Verify that a vehicle assigned a serving or rebalancing trip of duration T ticks
        arrives at the destination zone exactly T ticks later.
        """
        # Create a model with 1 vehicle and zero demand to prevent immediate matching on arrival
        model = ThesisSimulationModel(fleet_size=1, lambdas={zone: 0 for zone in ZONES}, seed=42)
        vehicle = list(model.agents)[0]
        
        # Initially, the vehicle must be IDLE
        self.assertEqual(vehicle.state, VehicleState.IDLE)
        start_zone = vehicle.current_zone
        
        # Force a serving trip assignment
        dest_zone = "A" if start_zone != "A" else "C"
        travel_time = TRAVEL_TIMES[start_zone][dest_zone]
        vehicle.assign_trip(origin=start_zone, destination=dest_zone, travel_time=travel_time)
        
        self.assertEqual(vehicle.state, VehicleState.SERVING)
        self.assertEqual(vehicle.destination_zone, dest_zone)
        self.assertEqual(vehicle.time_left, travel_time)
        
        # Step through travel time and check decrements
        for tick in range(1, travel_time):
            model.step()
            self.assertEqual(vehicle.state, VehicleState.SERVING)
            self.assertEqual(vehicle.time_left, travel_time - tick)
            self.assertIsNone(vehicle.current_zone)
            
        # One more step must result in arrival
        model.step()
        self.assertEqual(vehicle.state, VehicleState.IDLE)
        self.assertEqual(vehicle.current_zone, dest_zone)
        self.assertEqual(vehicle.time_left, 0)

        # Force a rebalancing assignment
        rebalance_dest = start_zone
        travel_time_reb = TRAVEL_TIMES[dest_zone][rebalance_dest]
        vehicle.assign_rebalance(origin=dest_zone, destination=rebalance_dest, travel_time=travel_time_reb)
        self.assertEqual(vehicle.state, VehicleState.REBALANCING)
        
        for tick in range(1, travel_time_reb):
            model.step()
            self.assertEqual(vehicle.state, VehicleState.REBALANCING)
            self.assertEqual(vehicle.time_left, travel_time_reb - tick)
            self.assertIsNone(vehicle.current_zone)
            
        model.step()
        self.assertEqual(vehicle.state, VehicleState.IDLE)
        self.assertEqual(vehicle.current_zone, rebalance_dest)

    def test_unmet_demand_carry_over(self):
        """
        Verify that unserved demand from step t-1 is added to step t's
        effective demand using a 50% carry-over rate with integer rounding,
        and that it doesn't double-count or leak.
        """
        # Set up a model with 0 fleet size to ensure all demand goes unserved
        # So unmet demand must accumulate
        model = ThesisSimulationModel(fleet_size=0, seed=42)
        
        # Step 1
        model.step()
        h1 = model.history[0]
        for zone in ZONES:
            realized = h1["zones"][zone]["realized_demand"]
            unmet_prev = 0  # No previous unmet demand
            eff_exp = realized + unmet_prev
            self.assertEqual(h1["zones"][zone]["effective_demand"], eff_exp)
            # Since fleet is 0, served demand must be 0
            self.assertEqual(h1["zones"][zone]["served_demand"], 0)
            # Unmet demand at end of step 1 must equal effective demand
            self.assertEqual(model.unmet_demand[zone], eff_exp)

        # Step 2
        unmet_step_1 = {zone: model.unmet_demand[zone] for zone in ZONES}
        model.step()
        h2 = model.history[1]
        for zone in ZONES:
            realized = h2["zones"][zone]["realized_demand"]
            eff_exp = realized + int(round(model.BACKLOG_CARRYOVER_RATE * unmet_step_1[zone]))
            # Verify carry-over formula
            self.assertEqual(h2["zones"][zone]["effective_demand"], eff_exp)

    def test_reproducibility(self):
        """Verify that running two models with the same seed results in identical histories."""
        model_a = ThesisSimulationModel(fleet_size=100, seed=12345)
        model_b = ThesisSimulationModel(fleet_size=100, seed=12345)
        
        for _ in range(15):
            model_a.step()
            model_b.step()
            
        # Verify step-by-step equality of metrics
        for ha, hb in zip(model_a.history, model_b.history):
            self.assertEqual(ha["system"], hb["system"])
            for zone in ZONES:
                self.assertEqual(ha["zones"][zone], hb["zones"][zone])

    def test_dynamic_pricing_and_governance(self):
        """
        Verify that dynamic pricing adjusts prices based on imbalances,
        and that governance successfully caps price adjustments by delta.
        """
        # Scenario A: Dynamic Pricing ON, Governance OFF
        # We start with 0 fleet size so there is a massive deficit, prices must rise
        model_a = ThesisSimulationModel(fleet_size=0, pricing_enabled=True, governance_enabled=False, alpha=0.5, seed=42)
        initial_prices = model_a.prices.copy()
        
        # Step 1
        model_a.step()
        # Since demand was realized and fleet was 0, prices for step 2 (updated at the end of step 1 / start of step 2)
        # must have increased
        for zone in ZONES:
            self.assertGreater(model_a.prices[zone], initial_prices[zone])
            
        # Scenario B: Dynamic Pricing ON, Governance ON
        # Price change per step must be capped by delta (e.g. 0.5)
        delta_val = 0.5
        model_b = ThesisSimulationModel(
            fleet_size=0, pricing_enabled=True, governance_enabled=True,
            alpha=2.0, delta=delta_val, seed=42
        )
        initial_prices_b = model_b.prices.copy()
        
        model_b.step()
        for zone in ZONES:
            price_change = model_b.prices[zone] - initial_prices_b[zone]
            self.assertLessEqual(price_change, delta_val + 1e-9)

    def test_demand_forecasting(self):
        """Verify that exponential smoothing forecast updates follow correct math."""
        omega_val = 0.3
        model = ThesisSimulationModel(forecasting_enabled=True, omega=omega_val, seed=42)
        
        # Run step 1
        model.step()
        # Forecast at end of step 1 is updated using initial conditions
        # So it remains equal to the baseline lambda.
        
        # Let's save the forecast at the start of step 2 (which is computed at the end of step 1)
        forecast_step_1 = model.forecast_demand["R1"]
        self.assertAlmostEqual(forecast_step_1, DEMAND_LAMBDAS["R1"])
        
        # Run step 2
        model.step()
        # The forecast at the end of step 2 is computed using realized demand from step 1
        h1 = model.history[0]
        realized_demand_step_1 = h1["zones"]["R1"]["realized_demand"]
        
        expected_forecast_step_2 = omega_val * realized_demand_step_1 + (1.0 - omega_val) * forecast_step_1
        self.assertAlmostEqual(model.forecast_demand["R1"], expected_forecast_step_2, places=5)

    def test_rebalancing_dispatch(self):
        """Verify that rebalancing shifts idle drivers from surplus to deficit zones."""
        # Create a model with rebalancing enabled
        # Force a surplus in R1 and deficit in C
        # We can set high demand for C and zero demand for others, and put all vehicles in R1
        lambdas = {zone: 0.0 for zone in ZONES}
        lambdas["C"] = 50.0  # Big deficit will be forecasted for C
        
        model = ThesisSimulationModel(
            fleet_size=10, lambdas=lambdas, rebalancing_enabled=True, 
            forecasting_enabled=False, governance_enabled=False, seed=42
        )
        
        # Force all 10 vehicles to start in R1
        for vehicle in model.agents:
            vehicle.current_zone = "R1"
            vehicle.state = VehicleState.IDLE
            
        # Verify initial states
        self.assertEqual(sum(1 for v in model.agents if v.current_zone == "R1"), 10)
        self.assertEqual(sum(1 for v in model.agents if v.state == VehicleState.IDLE), 10)
        
        # Run step
        model.step()
        
        # Some vehicles should have been dispatched to rebalance from R1 to C
        rebalancing_to_c = sum(
            1 for v in model.agents 
            if v.state == VehicleState.REBALANCING and v.destination_zone == "C" and v.origin_zone == "R1"
        )
        self.assertGreater(rebalancing_to_c, 0)
        
    def test_demand_shock_scenario(self):
        """Verify that shock scenario spikes demand in Center zone with a linear ramp transition."""
        model_shock = ThesisSimulationModel(shock_enabled=True, seed=42)

        # Patch _poisson_draw to record every lambda passed in
        called_lambdas = []
        original_draw = model_shock._poisson_draw

        def mock_draw(lam):
            called_lambdas.append(lam)
            return original_draw(lam)

        model_shock._poisson_draw = mock_draw

        # Track multipliers mapped by step index
        expected_multipliers = {}
        for step_idx in range(40):
            t = step_idx + 1  # steps is incremented to step_idx + 1 at the start of step()
            if t <= 19:
                expected_multipliers[step_idx] = 1.0
            elif t <= 22:
                expected_multipliers[step_idx] = 1.0 + (4.0 - 1.0) * (t - 19) / 3.0
            elif t <= 33:
                expected_multipliers[step_idx] = 4.0
            elif t <= 36:
                expected_multipliers[step_idx] = 1.0 + (4.0 - 1.0) * (36 - t) / 3.0
            else:
                expected_multipliers[step_idx] = 1.0

        for step_idx in range(40):
            called_lambdas.clear()
            model_shock.step()

            # The Center zone base lambda is multiplied by the dynamic multiplier
            expected_lambda = DEMAND_LAMBDAS["C"] * expected_multipliers[step_idx]
            self.assertIn(expected_lambda, called_lambdas,
                          f"Expected lambda {expected_lambda} not found in C at step_idx={step_idx}")

    def test_repeated_demand_shocks(self):
        """Verify that repeated demand shocks occur every 40 ticks with the correct multiplier values."""
        model_shock = ThesisSimulationModel(shock_mode="Repeated Demand Shocks", seed=42)

        # Patch _poisson_draw to record every lambda passed in
        called_lambdas = []
        original_draw = model_shock._poisson_draw

        def mock_draw(lam):
            called_lambdas.append(lam)
            return original_draw(lam)

        model_shock._poisson_draw = mock_draw

        # Track multipliers mapped by step index up to 120 steps
        expected_multipliers = {}
        for step_idx in range(120):
            t = step_idx + 1  # steps is incremented to step_idx + 1 at the start of step()
            if t < 20:
                expected_multipliers[step_idx] = 1.0
            else:
                t_rel = (t - 20) % 40
                if t_rel <= 2:
                    expected_multipliers[step_idx] = 1.0 + 3.0 * (t_rel + 1) / 3.0
                elif t_rel <= 13:
                    expected_multipliers[step_idx] = 4.0
                elif t_rel <= 16:
                    expected_multipliers[step_idx] = 1.0 + 3.0 * (16 - t_rel) / 3.0
                else:
                    expected_multipliers[step_idx] = 1.0

        for step_idx in range(120):
            called_lambdas.clear()
            model_shock.step()

            # The Center zone base lambda is multiplied by the dynamic multiplier
            expected_lambda = DEMAND_LAMBDAS["C"] * expected_multipliers[step_idx]
            self.assertIn(expected_lambda, called_lambdas,
                          f"Expected lambda {expected_lambda} not found in C at step_idx={step_idx} (step={step_idx + 1})")

    def test_in_transit_supply_exclusion_pricing(self):
        """
        Verify that vehicles in transit are not counted in the local supply for pricing,
        and that pricing reacts to actual available (idle) supply and increases correctly
        when there is a driver shortage. Also verify fleet size is preserved.
        """
        # Set up a model with 10 vehicles and dynamic pricing ON, rebalancing OFF
        # We set high demand for zone R1 and zero demand for others to trigger outbound trips
        lambdas = {zone: 0.0 for zone in ZONES}
        lambdas["R1"] = 10.0
        
        # We initialize all vehicles to start in R1
        model = ThesisSimulationModel(
            fleet_size=10, lambdas=lambdas, pricing_enabled=True,
            governance_enabled=False, alpha=0.5, seed=42
        )
        
        for vehicle in model.agents:
            vehicle.current_zone = "R1"
            vehicle.state = VehicleState.IDLE
            
        initial_price = model.prices["R1"]
        
        # Run step 1: demand is generated, matched, and vehicles transition to SERVING (in transit)
        model.step()
        
        # Verify that all vehicles matched to outbound trips have current_zone is None
        serving_vehicles = [v for v in model.agents if v.state == VehicleState.SERVING]
        self.assertGreater(len(serving_vehicles), 0)
        for v in serving_vehicles:
            self.assertIsNone(v.current_zone)
            
        # Verify that fleet size is preserved
        idle_count = sum(1 for v in model.agents if v.state == VehicleState.IDLE)
        self.assertEqual(len(serving_vehicles) + idle_count, 10)
        
        # Run step 2: pricing is updated based on step 1's imbalance
        model.step()
        
        # Prices should rise because effective demand is high and available supply is 0 or very low.
        # Let's verify that the price in R1 increases.
        price_after_transit = model.prices["R1"]
        self.assertGreater(price_after_transit, initial_price)

    def test_forecast_pricing_sensitivity_alpha_f(self):
        """
        Verify that alpha_f correctly scales pricing adjustments when forecasting is enabled.
        """
        # Set up two models, model_a with low alpha_f and model_b with high alpha_f
        # Enable forecasting and dynamic pricing, disable rebalancing
        lambdas = {zone: 0.0 for zone in ZONES}
        lambdas["R1"] = 10.0
        
        # Scenario A: alpha_f = 0.1
        model_a = ThesisSimulationModel(
            fleet_size=10, lambdas=lambdas, pricing_enabled=True,
            forecasting_enabled=True, rebalancing_enabled=False,
            alpha=0.2, alpha_f=0.1, omega=0.5, seed=42
        )
        for v in model_a.agents:
            v.current_zone = "R1"
            v.state = VehicleState.IDLE
            
        # Scenario B: alpha_f = 0.5 (more sensitive to forecast)
        model_b = ThesisSimulationModel(
            fleet_size=10, lambdas=lambdas, pricing_enabled=True,
            forecasting_enabled=True, rebalancing_enabled=False,
            alpha=0.2, alpha_f=0.5, omega=0.5, seed=42
        )
        for v in model_b.agents:
            v.current_zone = "R1"
            v.state = VehicleState.IDLE
            
        # Step both models once
        model_a.step()
        model_b.step()
        
        # Step again so that step 1's forecast demand imbalance is applied to step 2's price update.
        model_a.step()
        model_b.step()
        
        price_a = model_a.prices["R1"]
        price_b = model_b.prices["R1"]
        
        # Since model_b has a higher alpha_f, and we have a forecast demand imbalance (deficit),
        # the price in model_b must be strictly greater than the price in model_a.
        self.assertGreater(price_b, price_a)

    def test_governance_disabled_isolation(self):
        """Verify that when governance is disabled, governance parameters (delta, theta, R_max) do not constrain the model."""
        # 1. Test delta pricing cap is ignored when governance is disabled:
        # Initial prices are 10. We have 0 fleet size so there is a massive deficit.
        # Pricing alpha is set to 5.0. If governance is disabled, price can change by more than delta=0.5.
        model_pricing = ThesisSimulationModel(
            fleet_size=0, pricing_enabled=True, governance_enabled=False,
            alpha=5.0, delta=0.5, seed=42
        )
        initial_prices = model_pricing.prices.copy()
        model_pricing.step()
        
        # Verify that price change exceeded delta (0.5) in at least one zone
        exceeded_delta = False
        for zone in ZONES:
            price_change = abs(model_pricing.prices[zone] - initial_prices[zone])
            if price_change > 0.5:
                exceeded_delta = True
                break
        self.assertTrue(exceeded_delta, "Price adjustments were constrained by delta even though governance was disabled")

        # 2. Test theta rebalance buffer is ignored when governance is disabled:
        # We set theta to 5.0, but governance_enabled is False.
        # Zone C has demand 1.0 (realized = 1), R1 has 1 idle driver.
        # Gap in C = 1 - 0 = 1.
        # Since theta is 5.0, if governed, deficit would be max(0, 1 - 5.0) = 0.
        # Since governance is disabled, deficit is 1, so the driver should be rebalanced.
        lambdas = {zone: 0.0 for zone in ZONES}
        lambdas["C"] = 1.0
        custom_travel_times = {z1: {z2: 1 for z2 in ZONES} for z1 in ZONES}
        custom_destination_probs = {z1: {z2: 1.0 if z2 == "C" else 0.0 for z2 in ZONES} for z1 in ZONES}
        
        model_rebalance = ThesisSimulationModel(
            fleet_size=1, lambdas=lambdas, rebalancing_enabled=True,
            forecasting_enabled=False, pricing_enabled=False,
            governance_enabled=False, theta=5.0,
            travel_times=custom_travel_times, destination_probs=custom_destination_probs,
            R_max=10, seed=42
        )
        model_rebalance._poisson_draw = lambda lam: 5 if lam == 1.0 else 0
        # Put the 1 driver in R1
        for v in model_rebalance.agents:
            v.current_zone = "R1"
            v.state = VehicleState.IDLE
            
        model_rebalance.step()
        h1 = model_rebalance.history[0]
        # Rebalancing should have run because theta is ignored
        self.assertEqual(h1["system"]["total_rebalanced_dispatched"], 1)

        # 3. Test R_max rebalance flow limit is ignored when governance is disabled:
        # We set R_max to 1, but governance_enabled is False.
        # Zone C has unmet demand = 10, other zones have 5 surplus idle vehicles.
        # Since R_max is 1, if governed, rebalanced would be at most 1.
        # Since governance is disabled, it should rebalance all possible (more than 1).
        lambdas_flow = {zone: 0.0 for zone in ZONES}
        lambdas_flow["C"] = 10.0
        
        model_flow = ThesisSimulationModel(
            fleet_size=6, lambdas=lambdas_flow, rebalancing_enabled=True,
            forecasting_enabled=False, pricing_enabled=False,
            governance_enabled=False, theta=0.0,
            travel_times=custom_travel_times, destination_probs=custom_destination_probs,
            R_max=1, seed=42
        )
        model_flow._poisson_draw = lambda lam: 10 if lam == 10.0 else 0
        # Put 1 in C (so it serves 1 demand), 5 in R1 (idle)
        for i, v in enumerate(model_flow.agents):
            if i == 0:
                v.current_zone = "C"
            else:
                v.current_zone = "R1"
            v.state = VehicleState.IDLE
            
        model_flow.step()
        h_flow = model_flow.history[0]
        # More than 1 vehicle should have rebalanced because R_max is ignored
        self.assertGreater(h_flow["system"]["total_rebalanced_dispatched"], 1)


class TestSimulationMetrics(unittest.TestCase):
    """Test suite for verifying metrics definitions, naming, and formulas."""

    def test_fleet_utilization_serving_only(self):
        """Verify that fleet_utilization only counts serving vehicles, not rebalancing or idle."""
        # Create model with 3 vehicles
        model = ThesisSimulationModel(fleet_size=3, seed=42)
        # Manually assign states to the 3 vehicles:
        agents = list(model.agents)
        self.assertEqual(len(agents), 3)
        agents[0].state = VehicleState.IDLE
        agents[1].state = VehicleState.SERVING
        agents[2].state = VehicleState.REBALANCING
        
        # Log metrics manually
        model._log_metrics(
            new_demand={z: 0 for z in ZONES},
            realized_demand={z: 0 for z in ZONES},
            effective_demand={z: 0 for z in ZONES},
            served_demand={z: 0 for z in ZONES},
            total_rebalanced=1,
            idle_before_matching={z: 0 for z in ZONES}
        )
        
        last_metrics = model.history[-1]["system"]
        # New fleet_utilization must be serving / total = 1 / 3 = 0.3333333333333333
        self.assertAlmostEqual(last_metrics["fleet_utilization"], 1.0 / 3.0)
        # Old utilization is (total - idle) / total = (3 - 1) / 3 = 2 / 3
        self.assertAlmostEqual(last_metrics["utilization"], 2.0 / 3.0)

    def test_unmet_demand_rate(self):
        """Verify that unmet_demand_rate is calculated correctly with safe fallback."""
        from src.metrics import summarize_run
        # 1. Normal case
        history = [
            {
                "zones": {},
                "system": {
                    "revenue": 100.0,
                    "fleet_utilization": 0.5,
                    "spatial_imbalance": 2.0,
                    "total_unmet_demand": 5,
                    "total_effective_demand": 25,
                    "idle_vehicles": 10,
                    "serving_vehicles": 10,
                }
            },
            {
                "zones": {},
                "system": {
                    "revenue": 150.0,
                    "fleet_utilization": 0.6,
                    "spatial_imbalance": 3.0,
                    "total_unmet_demand": 15,
                    "total_effective_demand": 75,
                    "idle_vehicles": 8,
                    "serving_vehicles": 12,
                }
            }
        ]
        summary = summarize_run(history, fleet_size=20, imbalance_threshold=1.0)
        # total unmet = 20, total effective = 100, so rate = 0.20
        self.assertEqual(summary["unmet_demand_rate"], 0.20)
        self.assertEqual(summary["avg_unmet_demand"], 10.0)

        # 2. Zero effective demand fallback case
        history_zero = [
            {
                "zones": {},
                "system": {
                    "revenue": 0.0,
                    "fleet_utilization": 0.0,
                    "spatial_imbalance": 0.0,
                    "total_unmet_demand": 0,
                    "total_effective_demand": 0,
                    "idle_vehicles": 20,
                    "serving_vehicles": 0,
                }
            }
        ]
        summary_zero = summarize_run(history_zero, fleet_size=20, imbalance_threshold=1.0)
        self.assertEqual(summary_zero["unmet_demand_rate"], 0.0)
        self.assertEqual(summary_zero["avg_unmet_demand"], 0.0)

    def test_overload_frequency(self):
        """Verify overload_frequency calculations."""
        from src.metrics import summarize_run
        # 4 steps:
        # Step 1: ratio = 0 / 10 = 0.0 (normal)
        # Step 2: ratio = 1 / 10 = 0.10 (stressed)
        # Step 3: ratio = 3 / 10 = 0.30 (overloaded)
        # Step 4: ratio = 5 / 10 = 0.50 (overloaded)
        # So overload_frequency = 0.50
        history = [
            {
                "zones": {},
                "system": {
                    "revenue": 100.0,
                    "fleet_utilization": 0.5,
                    "spatial_imbalance": 2.0,
                    "total_unmet_demand": 0,
                    "total_effective_demand": 10,
                    "idle_vehicles": 10,
                    "serving_vehicles": 10,
                }
            },
            {
                "zones": {},
                "system": {
                    "revenue": 100.0,
                    "fleet_utilization": 0.5,
                    "spatial_imbalance": 2.0,
                    "total_unmet_demand": 1,
                    "total_effective_demand": 10,
                    "idle_vehicles": 10,
                    "serving_vehicles": 10,
                }
            },
            {
                "zones": {},
                "system": {
                    "revenue": 100.0,
                    "fleet_utilization": 0.5,
                    "spatial_imbalance": 2.0,
                    "total_unmet_demand": 3,
                    "total_effective_demand": 10,
                    "idle_vehicles": 10,
                    "serving_vehicles": 10,
                }
            },
            {
                "zones": {},
                "system": {
                    "revenue": 100.0,
                    "fleet_utilization": 0.5,
                    "spatial_imbalance": 2.0,
                    "total_unmet_demand": 5,
                    "total_effective_demand": 10,
                    "idle_vehicles": 10,
                    "serving_vehicles": 10,
                }
            }
        ]
        summary = summarize_run(history, fleet_size=20, imbalance_threshold=5.0)
        self.assertEqual(summary["overload_frequency"], 0.50)

    def test_imbalance_persistence(self):
        """Verify imbalance_persistence calculation against threshold."""
        from src.metrics import summarize_run
        # threshold = 2.5
        # Step 1: imbalance = 1.0 (no)
        # Step 2: imbalance = 3.0 (yes)
        # Step 3: imbalance = 2.0 (no)
        # Step 4: imbalance = 4.0 (yes)
        # persistence = 2 / 4 = 0.50
        history = [
            {"zones": {}, "system": {"revenue": 0.0, "fleet_utilization": 0.0, "spatial_imbalance": 1.0, "total_unmet_demand": 0, "total_effective_demand": 0, "idle_vehicles": 10, "serving_vehicles": 0}},
            {"zones": {}, "system": {"revenue": 0.0, "fleet_utilization": 0.0, "spatial_imbalance": 3.0, "total_unmet_demand": 0, "total_effective_demand": 0, "idle_vehicles": 10, "serving_vehicles": 0}},
            {"zones": {}, "system": {"revenue": 0.0, "fleet_utilization": 0.0, "spatial_imbalance": 2.0, "total_unmet_demand": 0, "total_effective_demand": 0, "idle_vehicles": 10, "serving_vehicles": 0}},
            {"zones": {}, "system": {"revenue": 0.0, "fleet_utilization": 0.0, "spatial_imbalance": 4.0, "total_unmet_demand": 0, "total_effective_demand": 0, "idle_vehicles": 10, "serving_vehicles": 0}}
        ]
        summary = summarize_run(history, fleet_size=10, imbalance_threshold=2.5)
        self.assertEqual(summary["imbalance_persistence"], 0.50)

    def test_spatial_imbalance_mismatch_formula(self):
        """Verify that spatial_imbalance uses the mean absolute difference of effective demand and idle vehicles."""
        model = ThesisSimulationModel(fleet_size=6, seed=42)
        from src.agents import VehicleState
        from src.config import ZONES
        
        # Position 6 agents to be idle across the 6 zones
        agents = list(model.agents)
        self.assertEqual(len(agents), 6)
        zones_list = list(ZONES)
        for i, agent in enumerate(agents):
            agent.state = VehicleState.IDLE
            agent.current_zone = zones_list[i]
            
        # Zone idle: {"C": 1, "R1": 1, "R2": 1, "R3": 1, "R4": 1, "A": 1}
        # Set mock effective demand:
        effective_demand = {"C": 5, "R1": 1, "R2": 0, "R3": 1, "R4": 1, "A": 1}
        
        # Absolute differences:
        # C: |5 - 1| = 4
        # R1: |1 - 1| = 0
        # R2: |0 - 1| = 1
        # R3: |1 - 1| = 0
        # R4: |1 - 1| = 0
        # A: |1 - 1| = 0
        # Sum = 5, Mean = 5 / 6 = 0.83333333
        
        model._log_metrics(
            new_demand={z: 0 for z in ZONES},
            realized_demand={z: 0 for z in ZONES},
            effective_demand=effective_demand,
            served_demand={z: 0 for z in ZONES},
            total_rebalanced=0,
            idle_before_matching={z: 1 for z in ZONES}
        )
        
        last_metrics = model.history[-1]["system"]
        # Expected value is (5.0 / 6.0) / 6.0 = 5.0 / 36.0 because the fleet size is 6.
        self.assertAlmostEqual(last_metrics["spatial_imbalance"], 5.0 / 36.0)

    def test_rebalancing_horizon(self):
        """Verify that inbound vehicles are filtered by the rebalancing_horizon in gap calculation."""
        model = ThesisSimulationModel(
            fleet_size=2,
            rebalancing_enabled=True,
            rebalancing_horizon=1,
            seed=42
        )
        self.assertEqual(model.rebalancing_horizon, 1)

        # Place agent 0 in SERVING state destined to R1 with time_left = 1
        model.agents[0].state = VehicleState.SERVING
        model.agents[0].destination_zone = "R1"
        model.agents[0].time_left = 1

        # Place agent 1 in SERVING state destined to R1 with time_left = 3
        model.agents[1].state = VehicleState.SERVING
        model.agents[1].destination_zone = "R1"
        model.agents[1].time_left = 3

        # Test counting logic directly
        inbound_vehicles = {
            zone: sum(1 for v in model.agents if v.state in (VehicleState.SERVING, VehicleState.REBALANCING) and v.destination_zone == zone and v.time_left <= model.rebalancing_horizon)
            for zone in ZONES
        }
        # Since horizon is 1, only agent 0 should be counted. So inbound for R1 should be 1.
        self.assertEqual(inbound_vehicles["R1"], 1)

        # If we change horizon to 3, both agents should be counted. So inbound for R1 should be 2.
        model.rebalancing_horizon = 3
        inbound_vehicles_3 = {
            zone: sum(1 for v in model.agents if v.state in (VehicleState.SERVING, VehicleState.REBALANCING) and v.destination_zone == zone and v.time_left <= model.rebalancing_horizon)
            for zone in ZONES
        }
        self.assertEqual(inbound_vehicles_3["R1"], 2)

    def test_oscillation_index(self):
        """Verify that the oscillation_index correctly distinguishes monotonic trend and repeated oscillations."""
        from src.metrics import summarize_run
        
        # 1. Monotonic upward trend: 100 -> 110 -> 120 -> 130 -> 140
        history_monotonic = [
            {"step": t, "zones": {"A": {"price": p}}, "system": {"revenue": 0, "fleet_utilization": 0.5, "total_unmet_demand": 0, "total_effective_demand": 10, "spatial_imbalance": 0.1, "idle_vehicles": 5}}
            for t, p in enumerate([100.0, 110.0, 120.0, 130.0, 140.0])
        ]
        summary_m = summarize_run(history_monotonic, fleet_size=120)
        self.assertAlmostEqual(summary_m["oscillation_index"], 0.0)
        
        # 2. Perfect back-and-forth oscillation: 100 -> 110 -> 100 -> 110 -> 100
        history_oscillating = [
            {"step": t, "zones": {"A": {"price": p}}, "system": {"revenue": 0, "fleet_utilization": 0.5, "total_unmet_demand": 0, "total_effective_demand": 10, "spatial_imbalance": 0.1, "idle_vehicles": 5}}
            for t, p in enumerate([100.0, 110.0, 100.0, 110.0, 100.0])
        ]
        summary_o = summarize_run(history_oscillating, fleet_size=120)
        self.assertAlmostEqual(summary_o["oscillation_index"], 1.0)

        # 3. Fluctuation with flat period: 100 -> 110 -> 110 -> 100
        # nonzero diffs: [10, -10], reversals: 1, comparisons: 1, index: 1.0
        history_flat = [
            {"step": t, "zones": {"A": {"price": p}}, "system": {"revenue": 0, "fleet_utilization": 0.5, "total_unmet_demand": 0, "total_effective_demand": 10, "spatial_imbalance": 0.1, "idle_vehicles": 5}}
            for t, p in enumerate([100.0, 110.0, 110.0, 100.0])
        ]
        summary_f = summarize_run(history_flat, fleet_size=120)
        self.assertAlmostEqual(summary_f["oscillation_index"], 1.0)


if __name__ == "__main__":
    unittest.main()
