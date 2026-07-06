"""
UI Controls module for the thesis simulation dashboard.
Renders sidebar sliders, inputs, toggles, and buttons.
"""

import streamlit as st
from src.config import TOTAL_VEHICLES


def format_label(label, is_active, is_custom):
    """Format widget label to include bold (locked) or italic (inactive) indicator for CSS selectors."""
    if is_custom:
        return label
    return f"{label} **(locked)**" if is_active else f"{label} *(inactive)*"


def render_locked_toggle(label: str, is_active: bool):
    """
    Render a purely visual, non-interactive fake toggle for locked thesis scenarios.
    Active = blue pill, full text opacity.
    Inactive = grey pill, dimmed text.
    Uses inherited text color so it works in both light and dark Streamlit themes.
    """
    track_bg  = "#2563eb" if is_active else "#4a4d5a"
    knob_left = "calc(100% - 20px)" if is_active else "2px"
    opacity   = "1.0" if is_active else "0.42"

    html = f"""
    <div style="display:flex; align-items:center; gap:8px;
                padding:3px 0 5px 0; opacity:{opacity};">
      <div style="position:relative; width:40px; min-width:40px; height:22px;
                  background:{track_bg}; border-radius:11px;
                  cursor:not-allowed; flex-shrink:0;">
        <div style="position:absolute; top:2px; left:{knob_left};
                    width:18px; height:18px; background:#ffffff;
                    border-radius:50%;"></div>
      </div>
      <span style="font-size:0.875rem; flex:1; min-width:0;">{label}</span>
      <span style="font-size:0.68rem; opacity:0.55; white-space:nowrap;
                   flex-shrink:0; padding-left:2px;">🔒</span>
    </div>
    """
    st.sidebar.markdown(html, unsafe_allow_html=True)



def render_sidebar():
    """
    Render all simulation control widgets in the Streamlit sidebar.
    Returns a dictionary of current values.
    """
    st.sidebar.markdown("## Simulation Controls")
    
    # Initialize keys in session state if not present to ensure they are available immediately
    if "preset_selection" not in st.session_state:
        st.session_state.preset_selection = "Passive System"
    if "fleet_size" not in st.session_state:
        st.session_state.fleet_size = TOTAL_VEHICLES
    if "demand_multiplier" not in st.session_state:
        st.session_state.demand_multiplier = 1.0
    if "pricing_on" not in st.session_state:
        st.session_state.pricing_on = False
    if "rebalancing_on" not in st.session_state:
        st.session_state.rebalancing_on = False
    if "forecasting_on" not in st.session_state:
        st.session_state.forecasting_on = False
    if "governance_on" not in st.session_state:
        st.session_state.governance_on = False
    if "adaptive_governance" not in st.session_state:
        st.session_state.adaptive_governance = False
    if "alpha" not in st.session_state:
        st.session_state.alpha = 0.30
    if "alpha_f" not in st.session_state:
        st.session_state.alpha_f = 0.10
    if "beta" not in st.session_state:
        st.session_state.beta = 0.10
    if "omega" not in st.session_state:
        st.session_state.omega = 0.30
    if "delta" not in st.session_state:
        st.session_state.delta = 1.0
    if "theta" not in st.session_state:
        st.session_state.theta = 1.0
    if "R_max" not in st.session_state:
        st.session_state.R_max = 10
    if "shock_mode" not in st.session_state:
        st.session_state.shock_mode = "No Demand Shock"
    if "shock_intensity" not in st.session_state:
        st.session_state.shock_intensity = "4x baseline"

    # Determine if Custom mode is selected
    is_custom = (st.session_state.preset_selection == "Custom")

    # Playback controls
    col1, col2, col3 = st.sidebar.columns(3)
    start_clicked = col1.button("Start", use_container_width=True)
    pause_clicked = col2.button("Pause", use_container_width=True)
    reset_clicked = col3.button("Reset", use_container_width=True)
    
    tick_speed = st.sidebar.slider(
        "Visualization Speed (seconds)", 
        min_value=0.05, max_value=2.0, value=0.3, step=0.05,
        help="Controls only the dashboard playback and refresh speed. Does not affect model time or simulation dynamics."
    )
    
    # Core Parameters
    st.sidebar.subheader("Core Parameters")
    
    fleet_size_label = format_label("Fleet Size (Vehicles)", True, is_custom)
    fleet_size = st.sidebar.slider(
        fleet_size_label, 
        min_value=10, max_value=300, 
        value=int(st.session_state.fleet_size), 
        step=10,
        key="fleet_size",
        disabled=not is_custom
    )
    
    demand_multiplier_label = format_label("Demand Multiplier", True, is_custom)
    demand_multiplier = st.sidebar.slider(
        demand_multiplier_label, 
        min_value=0.1, max_value=3.0, 
        value=float(st.session_state.demand_multiplier), 
        step=0.1,
        key="demand_multiplier",
        disabled=not is_custom
    )
    
    # Scenario Presets Configuration
    PRESETS = {
        "Passive System": {
            "pricing_on": False,
            "rebalancing_on": False,
            "forecasting_on": False,
            "governance_on": False,
            "adaptive_governance": False,
            "fleet_size": TOTAL_VEHICLES,
            "alpha": 0.30,
            "alpha_f": 0.10,
            "beta": 0.10,
            "omega": 0.30,
            "delta": 1.0,
            "theta": 1.0,
            "R_max": 10,
        },
        "Pricing Only": {
            "pricing_on": True,
            "rebalancing_on": False,
            "forecasting_on": True,
            "governance_on": False,
            "adaptive_governance": False,
            "fleet_size": TOTAL_VEHICLES,
            "alpha": 0.30,
            "alpha_f": 0.10,
            "beta": 0.10,
            "omega": 0.30,
            "delta": 1.0,
            "theta": 1.0,
            "R_max": 10,
        },
        "Rebalancing Only": {
            "pricing_on": False,
            "rebalancing_on": True,
            "forecasting_on": False,
            "governance_on": False,
            "adaptive_governance": False,
            "fleet_size": TOTAL_VEHICLES,
            "alpha": 0.30,
            "alpha_f": 0.10,
            "beta": 0.10,
            "omega": 0.30,
            "delta": 1.0,
            "theta": 1.0,
            "R_max": 10,
        },
        "Interaction": {
            "pricing_on": True,
            "rebalancing_on": True,
            "forecasting_on": True,
            "governance_on": False,
            "adaptive_governance": False,
            "fleet_size": TOTAL_VEHICLES,
            "alpha": 0.30,
            "alpha_f": 0.10,
            "beta": 0.10,
            "omega": 0.30,
            "delta": 1.0,
            "theta": 1.0,
            "R_max": 10,
        },
        "Static Governance": {
            "pricing_on": True,
            "rebalancing_on": True,
            "forecasting_on": True,
            "governance_on": True,
            "adaptive_governance": False,
            "fleet_size": TOTAL_VEHICLES,
            "alpha": 0.30,
            "alpha_f": 0.10,
            "beta": 0.10,
            "omega": 0.30,
            "delta": 1.0,
            "theta": 1.0,
            "R_max": 10,
        },
        "Adaptive Governance": {
            "pricing_on": True,
            "rebalancing_on": True,
            "forecasting_on": True,
            "governance_on": True,
            "adaptive_governance": True,
            "fleet_size": TOTAL_VEHICLES,
            "alpha": 0.30,
            "alpha_f": 0.10,
            "beta": 0.10,
            "omega": 0.30,
            "delta": 2.0,
            "theta": 0.0,
            "R_max": 999,
        },
        "Custom": {
            "pricing_on": True,
            "rebalancing_on": True,
            "forecasting_on": True,
            "governance_on": False,
            "adaptive_governance": False,
            "fleet_size": TOTAL_VEHICLES,
            "alpha": 0.30,
            "alpha_f": 0.10,
            "beta": 0.10,
            "omega": 0.30,
            "delta": 1.0,
            "theta": 1.0,
            "R_max": 10,
        }
    }

    def handle_preset_change():
        selected = st.session_state.preset_selection
        if selected in PRESETS:
            for key, val in PRESETS[selected].items():
                st.session_state[key] = val

    st.sidebar.subheader("Scenario Presets & Toggles")
    st.sidebar.selectbox(
        "Scenario Preset",
        ["Passive System", "Pricing Only", "Rebalancing Only", "Interaction", "Static Governance", "Adaptive Governance", "Custom"],
        key="preset_selection",
        on_change=handle_preset_change
    )

    # Read current state values
    pricing_on_val = st.session_state.pricing_on
    rebalancing_on_val = st.session_state.rebalancing_on
    forecasting_on_val = st.session_state.forecasting_on
    governance_on_val = st.session_state.governance_on
    adaptive_governance_val = st.session_state.adaptive_governance

    # Render toggles — use custom HTML fake-toggles for locked scenarios
    # (Streamlit's disabled=True applies an internal opacity filter we cannot override via CSS)
    if is_custom:
        pricing_on = st.sidebar.toggle("Dynamic Pricing", key="pricing_on")
    else:
        render_locked_toggle("Dynamic Pricing", pricing_on_val)
        pricing_on = pricing_on_val

    if is_custom:
        rebalancing_on = st.sidebar.toggle("Heuristic Rebalancing", key="rebalancing_on")
    else:
        render_locked_toggle("Heuristic Rebalancing", rebalancing_on_val)
        rebalancing_on = rebalancing_on_val

    if is_custom:
        forecasting_on = st.sidebar.toggle(
            "Use Forecast in Pricing", key="forecasting_on",
            disabled=not pricing_on
        )
    else:
        render_locked_toggle("Use Forecast in Pricing", pricing_on_val and forecasting_on_val)
        forecasting_on = forecasting_on_val

    if is_custom:
        governance_on = st.sidebar.toggle("Governance Settings", key="governance_on")
    else:
        render_locked_toggle("Governance Settings", governance_on_val)
        governance_on = governance_on_val

    if is_custom:
        adaptive_governance = st.sidebar.toggle(
            "Adaptive Governance Mode", key="adaptive_governance",
            disabled=not governance_on,
            help="If enabled, pricing caps are applied dynamically during spatial stress states."
        )
    else:
        render_locked_toggle("Adaptive Governance Mode", governance_on_val and adaptive_governance_val)
        adaptive_governance = adaptive_governance_val

    
    # Shock Mode Selector (Always editable)
    shock_mode = st.sidebar.radio(
        "Shock Mode",
        ["No Demand Shock", "Demand Shock", "Repeated Demand Shocks"],
        key="shock_mode",
    )
    
    shock_intensity = st.sidebar.selectbox(
        "Shock Intensity",
        ["4x baseline", "6x severe", "8x extreme"],
        key="shock_intensity",
        disabled=(shock_mode == "No Demand Shock")
    )

    # Sidebar summary for current shock
    if shock_mode != "No Demand Shock":
        st.sidebar.markdown(f"""
        <div style="background-color: #1a1c23; border: 1px solid #333945; border-radius: 6px; padding: 10px; margin-top: 10px; margin-bottom: 15px;">
            <div style="font-size: 0.75rem; color: #a3a6b5; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Current Shock</div>
            <div style="font-size: 0.85rem; color: #eaecef; font-weight: 500; margin-top: 4px;">Center zone | {shock_intensity}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Parameter Sliders Grouped by Domain
    st.sidebar.subheader("Model Parameters")
    if is_custom:
        st.sidebar.caption("Edit parameter sliders freely below. Active value modifications will hold.")
    else:
        st.sidebar.caption("Note: Predefined thesis scenarios are locked to their exact parameters. Switch to Custom mode to edit.")
    
    st.sidebar.markdown("#### Pricing Parameters")
    alpha_active = pricing_on
    alpha_label = format_label("Pricing Sensitivity (α)", alpha_active, is_custom)
    alpha = st.sidebar.slider(
        alpha_label, 
        min_value=0.01, max_value=1.0, 
        value=float(st.session_state.alpha), 
        step=0.01,
        key="alpha",
        disabled=not is_custom or not pricing_on,
        help="α: controls price responsiveness to supply-demand imbalances"
    )
    
    alpha_f_active = pricing_on and forecasting_on
    alpha_f_label = format_label("Forecast Pricing Sensitivity (α_f)", alpha_f_active, is_custom)
    alpha_f = st.sidebar.slider(
        alpha_f_label, 
        min_value=0.01, max_value=1.0, 
        value=float(st.session_state.alpha_f), 
        step=0.01,
        key="alpha_f",
        disabled=not is_custom or not pricing_on or not forecasting_on,
        help="α_f: controls price responsiveness to forecast imbalances"
    )
    
    beta_label = format_label("Demand Price Elasticity (β)", True, is_custom)
    beta = st.sidebar.slider(
        beta_label, 
        min_value=0.01, max_value=1.0, 
        value=float(st.session_state.beta), 
        step=0.01,
        key="beta",
        disabled=not is_custom,
        help="β: controls demand response to price"
    )
    
    st.sidebar.markdown("#### Forecasting Parameters")
    omega_active = pricing_on or rebalancing_on
    omega_label = format_label("Forecast Smoothing (ω)", omega_active, is_custom)
    omega = st.sidebar.slider(
        omega_label, 
        min_value=0.05, max_value=1.0, 
        value=float(st.session_state.omega), 
        step=0.05,
        key="omega",
        disabled=not is_custom or not (pricing_on or rebalancing_on),
        help="ω: controls forecast smoothing"
    )

    # --- Rebalancing Parameters ---
    # θ is shown here only when governance is OFF.
    # When governance is ON, θ moves into the Governance Parameters section below.
    theta_val = 0.0 if (governance_on and adaptive_governance) else float(st.session_state.theta)
    if not governance_on:
        st.sidebar.markdown("#### Rebalancing Parameters")
        theta_active = rebalancing_on
        theta_label = format_label("Rebalance Buffer (θ)", theta_active, is_custom)
        theta = st.sidebar.slider(
            theta_label,
            min_value=0.0, max_value=5.0,
            value=theta_val,
            step=0.1,
            key="theta",
            disabled=not is_custom or not rebalancing_on,
            help="θ: ignores small rebalancing gaps"
        )
    else:
        # Keep session state consistent even when slider is hidden
        theta = theta_val

    # --- Governance Parameters ---
    st.sidebar.markdown("#### Governance Parameters")

    # Adaptive Trigger Threshold (only for adaptive governance)
    if governance_on and adaptive_governance:
        model_obj = st.session_state.get("model", None)
        threshold_val = getattr(model_obj, "adaptive_governance_threshold", 0.14)
        threshold_label = format_label("Adaptive Trigger Threshold", True, is_custom)
        st.sidebar.slider(
            threshold_label,
            min_value=0.01, max_value=0.50,
            value=threshold_val,
            step=0.01,
            key="threshold_slider",
            disabled=True,
            help="Imbalance threshold to trigger active governance intervention"
        )

    # θ lives here when governance is ON
    if governance_on:
        theta_active = rebalancing_on and governance_on
        theta_label = format_label("Rebalance Buffer (θ)", theta_active, is_custom)
        theta = st.sidebar.slider(
            theta_label,
            min_value=0.0, max_value=5.0,
            value=theta_val,
            step=0.1,
            key="theta",
            disabled=not is_custom or not rebalancing_on or not governance_on,
            help="θ: ignores small rebalancing gaps"
        )
    
    delta_active = pricing_on and governance_on
    delta_label = format_label("Max Price Adjust (δ)", delta_active, is_custom)
    delta_val = 2.0 if (governance_on and adaptive_governance) else float(st.session_state.delta)
    delta = st.sidebar.slider(
        delta_label, 
        min_value=0.1, max_value=10.0, 
        value=delta_val, 
        step=0.1,
        key="delta",
        disabled=not is_custom or not pricing_on or not governance_on,
        help="δ: caps price changes per step"
    )
    
    R_max_active = rebalancing_on and governance_on
    R_max_label = format_label("Max Rebalance Flow (R_max)", R_max_active, is_custom)
    R_max_val = 999 if (governance_on and adaptive_governance) else int(st.session_state.R_max)
    R_max = st.sidebar.slider(
        R_max_label, 
        min_value=1, max_value=1000 if (governance_on and adaptive_governance) else 100, 
        value=R_max_val, 
        step=1,
        key="R_max",
        disabled=not is_custom or not rebalancing_on or not governance_on,
        help="R_max: caps rebalancing flow per step"
    )
    
    intensity_map = {"4x baseline": 4.0, "6x severe": 6.0, "8x extreme": 8.0}
    shock_intensity_val = intensity_map.get(shock_intensity, 4.0)

    return {
        "start": start_clicked,
        "pause": pause_clicked,
        "reset": reset_clicked,
        "tick_speed": tick_speed,
        "fleet_size": fleet_size,
        "demand_multiplier": demand_multiplier,
        "pricing_on": pricing_on,
        "rebalancing_on": rebalancing_on,
        "forecasting_on": forecasting_on,
        "governance_on": governance_on,
        "adaptive_governance": adaptive_governance,
        "shock_mode": shock_mode,
        "shock_intensity": shock_intensity,
        "shock_intensity_val": shock_intensity_val,
        "alpha": alpha,
        "alpha_f": alpha_f,
        "beta": beta,
        "omega": omega,
        "theta": theta,
        "delta": delta,
        "R_max": R_max
    }
