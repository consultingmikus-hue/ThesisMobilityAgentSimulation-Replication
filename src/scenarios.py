"""
Scenario and governance parameter definitions for the thesis simulation experiments.
"""

# Reusable scenario presets
SCENARIOS = {
    "passive": {
        "pricing_enabled": False,
        "rebalancing_enabled": False,
        "forecasting_enabled": False,  # Pricing is OFF, so pricing forecast is OFF
        "governance_enabled": False,
        "shock_mode": "No Demand Shock",
    },
    "pricing_only": {
        "pricing_enabled": True,
        "rebalancing_enabled": False,
        "forecasting_enabled": True,   # Pricing is ON, pricing forecast is ON by default
        "governance_enabled": False,
        "shock_mode": "No Demand Shock",
    },
    "rebalancing_only": {
        "pricing_enabled": False,
        "rebalancing_enabled": True,
        "forecasting_enabled": False,  # Pricing is OFF, so pricing forecast is OFF
        "governance_enabled": False,
        "shock_mode": "No Demand Shock",
    },
    "interaction": {
        "pricing_enabled": True,
        "rebalancing_enabled": True,
        "forecasting_enabled": True,   # Pricing is ON, pricing forecast is ON by default
        "governance_enabled": False,
        "shock_mode": "No Demand Shock",
    },
    "governance": {
        "pricing_enabled": True,
        "rebalancing_enabled": True,
        "forecasting_enabled": True,   # Pricing is ON, pricing forecast is ON by default
        "governance_enabled": True,
        "shock_mode": "No Demand Shock",
    },
    "interaction_demand_shock": {
        "pricing_enabled": True,
        "rebalancing_enabled": True,
        "forecasting_enabled": True,   # Pricing is ON, pricing forecast is ON by default
        "governance_enabled": False,
        "shock_mode": "Demand Shock",
    },
    "governance_demand_shock": {
        "pricing_enabled": True,
        "rebalancing_enabled": True,
        "forecasting_enabled": True,   # Pricing is ON, pricing forecast is ON by default
        "governance_enabled": True,
        "shock_mode": "Demand Shock",
    },
    "interaction_repeated_demand_shocks": {
        "pricing_enabled": True,
        "rebalancing_enabled": True,
        "forecasting_enabled": True,   # Pricing is ON, pricing forecast is ON by default
        "governance_enabled": False,
        "shock_mode": "Repeated Demand Shocks",
    },
    "governance_repeated_demand_shocks": {
        "pricing_enabled": True,
        "rebalancing_enabled": True,
        "forecasting_enabled": True,   # Pricing is ON, pricing forecast is ON by default
        "governance_enabled": True,
        "shock_mode": "Repeated Demand Shocks",
    }
}

# Governance parameter sensitivity analysis grid ranges (Authoritative Thesis Design)
GOVERNANCE_GRID = {
    "deltas": [1.0, 2.0, 4.0],
    "thetas": [1.0, 2.0, 4.0],
    "R_maxs": [10, 25, 40]
}

# Optional UI convenience presets (Non-Experimental, for dashboard visualization testing only)
GOVERNANCE_SETTINGS = {
    "weak_governance": {
        "delta": 6.0,
        "theta": 1.0,
        "R_max": 60,
    },
    "medium_governance": {
        "delta": 2.5,
        "theta": 1.5,
        "R_max": 40,
    },
    "strong_governance": {
        "delta": 2.0,
        "theta": 3.0,
        "R_max": 25,
    }
}
