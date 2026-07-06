"""
Configuration module for the agent-based thesis simulation.
Defines parameters, zones, travel time matrix, destination probabilities,
demand generation coefficients, and initial settings for Phase 1.
"""

# Spatial Zones
ZONES = ["R1", "R2", "R3", "R4", "C", "A"]

# Fixed Travel Times between zones (in ticks/steps)
# One simulation tick represents approximately five minutes of platform operations. 
# This interval reflects short matching cycles and stylized urban travel times between zones within the platform environment.
# Intra-zone trips require a minimum of 1 tick (approx. 5 minutes).
TRAVEL_TIMES = {
    "C":  {"C": 1, "A": 4, "R1": 2, "R2": 2, "R3": 2, "R4": 2},
    "A":  {"C": 4, "A": 1, "R1": 3, "R2": 3, "R3": 3, "R4": 3},
    "R1": {"C": 2, "A": 3, "R1": 1, "R2": 1, "R3": 1, "R4": 1},
    "R2": {"C": 2, "A": 3, "R1": 1, "R2": 1, "R3": 1, "R4": 1},
    "R3": {"C": 2, "A": 3, "R1": 1, "R2": 1, "R3": 1, "R4": 1},
    "R4": {"C": 2, "A": 3, "R1": 1, "R2": 1, "R3": 1, "R4": 1},
}

# Destination Probability Matrix
# For each origin zone, probability distribution of trips heading to each destination zone.
# Rows must sum to 1.0.
DESTINATION_PROBS = {
    "R1": {"R1": 0.075, "R2": 0.075, "R3": 0.075, "R4": 0.075, "C": 0.50, "A": 0.20},
    "R2": {"R1": 0.075, "R2": 0.075, "R3": 0.075, "R4": 0.075, "C": 0.50, "A": 0.20},
    "R3": {"R1": 0.075, "R2": 0.075, "R3": 0.075, "R4": 0.075, "C": 0.50, "A": 0.20},
    "R4": {"R1": 0.075, "R2": 0.075, "R3": 0.075, "R4": 0.075, "C": 0.50, "A": 0.20},
    "C":  {"R1": 0.1125, "R2": 0.1125, "R3": 0.1125, "R4": 0.1125, "C": 0.30, "A": 0.25},
    "A":  {"R1": 0.0875, "R2": 0.0875, "R3": 0.0875, "R4": 0.0875, "C": 0.60, "A": 0.05},
}

# Demand parameters (Poisson arrival intensities lambda per tick)
DEMAND_LAMBDAS = {
    "R1": 3.0,
    "R2": 3.0,
    "R3": 3.0,
    "R4": 3.0,
    "C":  6.0,
    "A":  4.0,
}

# Elasticity and static/baseline pricing parameters
# In Phase 1, pricing is static and remains at BASELINE_PRICES.
# Price response: Demand = max(0, NewDemand - BETA * Price)
BETA = 0.1
BASELINE_PRICES = {
    "R1": 15.0,
    "R2": 15.0,
    "R3": 15.0,
    "R4": 15.0,
    "C":  18.0,
    "A":  25.0,
}

# Fleet configuration
TOTAL_VEHICLES = 80
