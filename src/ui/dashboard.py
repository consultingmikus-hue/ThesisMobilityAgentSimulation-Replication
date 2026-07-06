"""
Main Dashboard module for the thesis simulation.
Orchestrates Streamlit session state, layouts, metrics monitors,
and loops model execution for live updates.
"""

import time
import streamlit as st
import numpy as np

# Set page config as the very first Streamlit command
st.set_page_config(
    page_title="Thesis Platform Simulation Twin",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

import os
import sys
# Ensure the parent directory is in sys.path to resolve src package imports correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import importlib
import src.model
import src.ui.controls
importlib.reload(src.model)
importlib.reload(src.ui.controls)
from src.model import ThesisSimulationModel
from src.config import DEMAND_LAMBDAS, ZONES
from src.ui.controls import render_sidebar
from src.ui.visualizations import (
    plot_spatial_network,
    plot_prices_chart,
    plot_unmet_demand_chart,
    plot_fleet_states_chart,
    plot_imbalance_chart,
    plot_stability_space_chart
)

# Custom premium styling for dark mode and NetLogo-style monitors
st.markdown("""
<style>
    /* Premium font and body style */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Prevent Plotly iframe white flash during redraws */
    iframe {
        background-color: transparent !important;
    }
    div[data-testid="stPlotlyChart"] {
        background-color: transparent !important;
    }
    .stPlotlyChart {
        background-color: transparent !important;
    }
    
    /* Force dark background ONLY on the main content area to eliminate flash transparency without affecting the sidebar */
    section.main, section[data-testid="stMain"], div[data-testid="stPlotlyChart"], .stPlotlyChart {
        background-color: #0e1117 !important;
    }
    
    /* Premium Title styling */
    .dashboard-title {
        font-weight: 700;
        color: #eaecef;
        font-size: 2.2rem;
        margin-bottom: 0.1rem;
        text-align: left;
    }
    
    .dashboard-subtitle {
        font-weight: 300;
        color: #c5c7d0; /* Increased contrast slate gray */
        font-size: 1.0rem;
        margin-bottom: 1.5rem;
    }
    
    /* Monitor block styling (Modernized NetLogo monitors) */
    /* Row 1 cards (Visual Dominance) */
    .monitor-card-r1 {
        background-color: #181a20;
        border: 1px solid #2d3139;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s, border-color 0.2s;
    }
    .monitor-card-r1:hover {
        border-color: #2563eb;
        transform: translateY(-2px);
    }
    .monitor-label-r1 {
        font-size: 0.8rem;
        font-weight: 600;
        color: #c5c7d0; /* Increased contrast slate gray */
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 4px;
    }
    .monitor-value-r1 {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
    }

    /* Row 2 cards (Secondary, Subtle) */
    .monitor-card-r2 {
        background-color: #111317;
        border: 1px solid #22252c;
        border-radius: 8px;
        padding: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
        transition: transform 0.15s, border-color 0.15s;
    }
    .monitor-card-r2:hover {
        border-color: #93c47d;
        transform: translateY(-1px);
    }
    .monitor-label-r2 {
        font-size: 0.72rem;
        font-weight: 500;
        color: #a3a6b5; /* Increased contrast medium slate gray */
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 2px;
    }
    .monitor-value-r2 {
        font-size: 1.25rem;
        font-weight: 600;
        color: #eaecef; /* Increased contrast text gray */
    }
    
    .monitor-value-highlight {
        color: #2563eb;
    }

    /* ── Streamlit native widget contrast overrides ─────────────────────────
       Target Streamlit's generated class names for tabs, checkboxes, toggles,
       radio buttons, and sidebar text so they render legibly on projectors.
       All selectors use !important to win over Streamlit's own specificity. */

    /* Tab bar buttons (active + inactive) */
    button[data-baseweb="tab"] {
        color: #c5c7d0 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #eaecef !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #eaecef !important;
        font-weight: 600 !important;
    }

    /* Checkbox and toggle labels — target all nesting levels Streamlit uses */
    .stCheckbox label,
    .stCheckbox label p,
    .stCheckbox span,
    div[data-testid="stCheckbox"] label,
    div[data-testid="stCheckbox"] label p,
    div[data-testid="stCheckbox"] p,
    div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"],
    div[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p {
        color: #c5c7d0 !important;
        font-size: 0.9rem !important;
    }
    /* Widget label generic — covers checkboxes, toggles, sliders, selects */
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p,
    label[data-testid="stWidgetLabel"],
    label[data-testid="stWidgetLabel"] p {
        color: #c5c7d0 !important;
    }
    .stToggle label,
    .stToggle label p,
    div[data-testid="stToggle"] label,
    div[data-testid="stToggle"] label p,
    div[data-testid="stToggle"] [data-testid="stWidgetLabel"] p {
        color: #c5c7d0 !important;
    }

    /* Radio button labels */
    .stRadio label,
    div[data-testid="stRadio"] label {
        color: #c5c7d0 !important;
    }

    /* Sidebar subheaders, section text, captions */
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] .stMarkdown h4 {
        color: #c5c7d0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stCaption"] {
        color: #a3a6b5 !important;
    }

    /* Slider label text */
    .stSlider label {
        color: #c5c7d0 !important;
    }
    .stSlider [data-testid="stTickBar"] {
        color: #a3a6b5 !important;
    }

    /* Selectbox label */
    .stSelectbox label {
        color: #c5c7d0 !important;
    }

    /* General small caption / helper text in main area */
    [data-testid="stCaption"],
    small {
        color: #a3a6b5 !important;
    }

    /* Style disabled checked toggles to look visually active but locked (strong blue) */
    div[data-testid="stToggle"] button[aria-checked="true"][disabled],
    div[data-testid="stToggle"] input[type="checkbox"]:checked:disabled ~ div,
    div[data-testid="stToggle"] input[type="checkbox"]:checked:disabled ~ span,
    .stToggle button[aria-checked="true"][disabled],
    .stToggle input[type="checkbox"]:checked:disabled ~ div,
    .stToggle input[type="checkbox"]:checked:disabled ~ span {
        background-color: #2563eb !important;
        background: #2563eb !important;
        opacity: 0.85 !important;
        cursor: not-allowed !important;
    }
    div[data-testid="stToggle"] button[aria-checked="true"][disabled] div[data-testid="stTogglePill"],
    div[data-testid="stToggle"] button[aria-checked="true"][disabled] [data-testid="stTogglePill"],
    div[data-testid="stToggle"] input[type="checkbox"]:checked:disabled ~ div [data-testid="stTogglePill"],
    div[data-testid="stToggle"] input[type="checkbox"]:checked:disabled ~ div span,
    div[data-testid="stToggle"] input[type="checkbox"]:checked:disabled ~ div div,
    .stToggle button[aria-checked="true"][disabled] [data-testid="stTogglePill"],
    .stToggle input[type="checkbox"]:checked:disabled ~ div [data-testid="stTogglePill"],
    .stToggle input[type="checkbox"]:checked:disabled ~ span [data-testid="stTogglePill"],
    .stToggle input[type="checkbox"]:checked:disabled ~ div span,
    .stToggle input[type="checkbox"]:checked:disabled ~ div div {
        background-color: #ffffff !important;
    }
    div[data-testid="stToggle"] button[aria-checked="true"][disabled] > div {
        background-color: #2563eb !important;
    }
    /* Style disabled unchecked toggles to look grey */
    div[data-testid="stToggle"] button[aria-checked="false"][disabled],
    div[data-testid="stToggle"] input[type="checkbox"]:not(:checked):disabled ~ div,
    div[data-testid="stToggle"] input[type="checkbox"]:not(:checked):disabled ~ span,
    .stToggle button[aria-checked="false"][disabled],
    .stToggle input[type="checkbox"]:not(:checked):disabled ~ div,
    .stToggle input[type="checkbox"]:not(:checked):disabled ~ span {
        background-color: #31333f !important;
        background: #31333f !important;
        opacity: 0.40 !important;
        cursor: not-allowed !important;
    }

    /* Style active locked sliders (with strong tag in label) to look active (strong blue) */
    div[data-testid="stSlider"]:has(label strong) [role="slider"] {
        background-color: #2563eb !important;
        border-color: #2563eb !important;
        opacity: 1 !important;
    }
    div[data-testid="stSlider"]:has(label strong) [data-testid="stSliderTrack"] > div > div {
        background-color: #2563eb !important;
        opacity: 0.85 !important;
    }
    /* Handle styling for different Streamlit slider markup variations */
    div[data-testid="stSlider"]:has(label strong) [data-disabled="true"] div[style*="background"] {
        background: #2563eb !important;
        opacity: 0.85 !important;
    }

    /* CSS Tooltip on Hover for disabled toggles and sliders */
    div[data-testid="stToggle"]:has(button[disabled]),
    div[data-testid="stToggle"]:has(input[disabled]),
    div[data-testid="stSlider"]:has([data-disabled="true"]) {
        position: relative !important;
    }
    div[data-testid="stToggle"]:has(button[disabled]):hover::after,
    div[data-testid="stToggle"]:has(input[disabled]):hover::after,
    div[data-testid="stSlider"]:has([data-disabled="true"]):hover::after {
        content: "Locked scenario. Use Custom to edit." !important;
        position: absolute !important;
        background-color: #1a1c23 !important;
        color: #eaecef !important;
        border: 1px solid #2563eb !important;
        padding: 6px 10px !important;
        border-radius: 4px !important;
        font-size: 0.78rem !important;
        font-family: sans-serif !important;
        font-weight: 500 !important;
        white-space: nowrap !important;
        z-index: 999999 !important;
        bottom: 100% !important;
        left: 50% !important;
        transform: translateX(-50%) translateY(-5px) !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4) !important;
        pointer-events: none !important;
    }

    /* Disable typing search in Selectbox */
    div[data-testid="stSelectbox"] input {
        pointer-events: none !important;
        caret-color: transparent !important;
        user-select: none !important;
    }
    div[data-testid="stSelectbox"] div[role="combobox"] {
        cursor: pointer !important;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state(fleet_size, shock_intensity_val):
    """Initialize Streamlit session state keys if they don't exist."""
    if "model" not in st.session_state:
        st.session_state.model = ThesisSimulationModel(
            fleet_size=fleet_size, 
            seed=42, 
            shock_intensity=shock_intensity_val,
            adaptive_governance_threshold=0.14
        )
    if "is_running" not in st.session_state:
        st.session_state.is_running = False
    if "tick_count" not in st.session_state:
        st.session_state.tick_count = 0


# 1. Sidebar Controls
controls = render_sidebar()

# Initialize session state (using sidebar fleet size as default)
init_session_state(controls["fleet_size"], controls["shock_intensity_val"])

# Retrieve references
model = st.session_state.model
is_running = st.session_state.is_running

# 2. Control Actions handling (Reset, Start, Pause)
if controls["reset"]:
    st.session_state.model = ThesisSimulationModel(
        fleet_size=controls["fleet_size"], 
        seed=42, 
        shock_intensity=controls["shock_intensity_val"],
        adaptive_governance_threshold=0.14
    )
    st.session_state.is_running = False
    st.session_state.tick_count = 0
    st.rerun()

if controls["start"]:
    st.session_state.is_running = True
    st.rerun()

if controls["pause"]:
    st.session_state.is_running = False
    st.rerun()

# 3. Synchronize UI parameters to the Model dynamically
model.alpha = controls["alpha"]
model.alpha_f = controls["alpha_f"]
model.beta = controls["beta"]
model.omega = controls["omega"]
model.theta = controls["theta"]
model.delta = controls["delta"]
model.R_max = controls["R_max"]

model.pricing_enabled = controls["pricing_on"]
model.rebalancing_enabled = controls["rebalancing_on"]
model.forecasting_enabled = controls["forecasting_on"]
model.governance_enabled = controls["governance_on"]
model.adaptive_governance = controls["adaptive_governance"]
model.shock_mode = controls["shock_mode"]
model.shock_intensity = controls["shock_intensity_val"]

# Update fleet size if changed via sidebar
if controls["fleet_size"] != model.fleet_size:
    st.session_state.model = ThesisSimulationModel(
        fleet_size=controls["fleet_size"], 
        seed=42, 
        shock_intensity=controls["shock_intensity_val"],
        adaptive_governance_threshold=0.14
    )
    st.session_state.is_running = False
    st.session_state.tick_count = 0
    st.rerun()

# Update base demands according to multiplier
model.lambdas = {zone: DEMAND_LAMBDAS[zone] * controls["demand_multiplier"] for zone in ZONES}

# --- Header Section ---
st.markdown('<div class="dashboard-title">Ride-Hailing Platform Simulation</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Pricing • Rebalancing • Governance Dynamics</div>', unsafe_allow_html=True)

# --- 4. Live NetLogo-style Monitors & Layout Fragment ---
run_every = controls["tick_speed"] if st.session_state.is_running else None

@st.fragment(run_every=run_every)
def render_live_dashboard(model, controls):
    # Gather current metrics for display
    current_step = st.session_state.tick_count
    history = model.history

    if history:
        last_h = history[-1]
        service_rate = last_h["system"]["service_rate"]
        utilization = last_h["system"].get("fleet_utilization", last_h["system"].get("utilization", 0.0))
        transit_count = last_h["system"]["serving_vehicles"] + last_h["system"]["rebalancing_vehicles"]
        imbalance = last_h["system"].get("spatial_imbalance", last_h["system"].get("imbalance_index", 0.0))
        unmet_demand = last_h["system"]["total_unmet_demand"]
        
        # Calculate live system status based on current unmet demand ratio
        eff = last_h["system"].get("total_effective_demand", 0.0)
        unmet_ratio = unmet_demand / eff if eff > 0.0 else 0.0
        
        if unmet_ratio < 0.05:
            status_text = "NORMAL"
            status_color = "#93c47d"  # Green
        elif unmet_ratio < 0.30:
            status_text = "STRESSED"
            status_color = "#ff8c00"  # Yellow/Orange
        else:
            status_text = "OVERLOADED"
            status_color = "#e06666"  # Red
    else:
        service_rate = 1.0
        utilization = 0.0
        transit_count = 0
        imbalance = 0.0
        unmet_demand = 0
        unmet_ratio = 0.0
        status_text = "NORMAL"
        status_color = "#93c47d"

    # Spatial Imbalance color: neutral below governance trigger, orange at/above it
    gov_threshold = model.adaptive_governance_threshold
    imbalance_color = "#ff8c00" if imbalance >= gov_threshold else "#eaecef"

    # Calculate cumulative and statistical metrics
    cum_revenue = sum(h["system"]["revenue"] for h in history) if history else 0.0
    avg_service_rate = sum(h["system"]["service_rate"] for h in history) / len(history) if history else 1.0
    avg_utilization = sum(h["system"].get("fleet_utilization", h["system"].get("utilization", 0.0)) for h in history) / len(history) if history else 0.0
    avg_spatial_imbalance = sum(h["system"]["spatial_imbalance"] for h in history) / len(history) if history else 0.0
    total_trips = sum(h["system"]["total_served_demand"] for h in history) if history else 0
    fleet_size = model.fleet_size
    rev_per_vehicle = cum_revenue / fleet_size if fleet_size > 0 else 0.0

    # Calculate running Thesis Metrics
    import statistics
    
    # 1. Price Volatility
    avg_prices = []
    for h in history:
        zones = h["zones"]
        if zones:
            avg_price_t = sum(zones[z]["price"] for z in zones) / len(zones)
        else:
            avg_price_t = 0.0
        avg_prices.append(avg_price_t)
    price_volatility = statistics.pstdev(avg_prices) if len(avg_prices) > 1 else 0.0
    
    # 2. Overload Frequency
    overload_ticks = 0
    for h in history:
        eff = h["system"]["total_effective_demand"]
        unmet = h["system"]["total_unmet_demand"]
        ratio = unmet / eff if eff > 0 else 0.0
        if ratio >= 0.30:
            overload_ticks += 1
    overload_frequency = overload_ticks / len(history) if history else 0.0
    
    # 3. Governance Activation
    if not model.governance_enabled:
        gov_activation_str = "N/A"
    elif not getattr(model, "adaptive_governance", False):
        gov_activation_str = "Always Active"
    else:
        active_ticks = 0
        threshold = model.adaptive_governance_threshold
        for i in range(1, len(history)):
            prev_imb = history[i-1]["system"]["spatial_imbalance"]
            if prev_imb > threshold:
                active_ticks += 1
        gov_activation_ratio = active_ticks / len(history) if history else 0.0
        gov_activation_str = f"{gov_activation_ratio:.1%}"

    # GATHER SHOCK DETAILS FOR THE EXECUTIVE PANEL
    t = current_step
    shock_mult_base = model.get_shock_multiplier()
    demand_multiplier = controls.get("demand_multiplier", 1.0)
    current_shock_mult = shock_mult_base * demand_multiplier
    
    shock_phase = "No Shock"
    shock_status = "INACTIVE"
    shock_icon = "💤"
    shock_bg = "#111317"
    shock_border = "#22252c"
    shock_text_color = "#c5c7d0"
    
    if model.shock_mode == "No Demand Shock":
        shock_phase = "N/A"
    else:
        is_active = model.is_shock_active
        if model.shock_mode == "Demand Shock":
            if t <= 19:
                shock_phase = "Pre-Shock"
            elif t <= 22:
                shock_phase = "Ramp-Up"
                shock_status = "ACTIVE"
                shock_icon = "🔥"
                shock_bg = "#2a1e1e"
                shock_border = "#e06666"
                shock_text_color = "#ffffff"
            elif t <= 33:
                shock_phase = "Peak Surge"
                shock_status = "ACTIVE"
                shock_icon = "🔥"
                shock_bg = "#3d1e1e"
                shock_border = "#e06666"
                shock_text_color = "#ffffff"
            elif t <= 36:
                shock_phase = "Ramp-Down"
                shock_status = "ACTIVE"
                shock_icon = "🔥"
                shock_bg = "#2a1e1e"
                shock_border = "#e06666"
                shock_text_color = "#ffffff"
            else:
                shock_phase = "Post-Shock"
        elif model.shock_mode == "Repeated Demand Shocks":
            if t < 20:
                shock_phase = "Pre-Shock"
            else:
                t_rel = (t - 20) % 40
                if t_rel <= 2:
                    shock_phase = "Ramp-Up"
                    shock_status = "ACTIVE"
                    shock_icon = "🔥"
                    shock_bg = "#2a1e1e"
                    shock_border = "#e06666"
                    shock_text_color = "#ffffff"
                elif t_rel <= 13:
                    shock_phase = "Peak Surge"
                    shock_status = "ACTIVE"
                    shock_icon = "🔥"
                    shock_bg = "#3d1e1e"
                    shock_border = "#e06666"
                    shock_text_color = "#ffffff"
                elif t_rel <= 16:
                    shock_phase = "Ramp-Down"
                    shock_status = "ACTIVE"
                    shock_icon = "🔥"
                    shock_bg = "#2a1e1e"
                    shock_border = "#e06666"
                    shock_text_color = "#ffffff"
                else:
                    shock_phase = "Inter-Shock Lull"

    # GATHER GOVERNANCE DETAILS FOR THE EXECUTIVE PANEL
    gov_enabled = model.governance_enabled
    adaptive_gov = getattr(model, "adaptive_governance", False)
    
    gov_status = "GOVERNANCE OFF"
    gov_icon = "💤"
    gov_bg = "#111317"
    gov_border = "#22252c"
    gov_text_color = "#c5c7d0"
    gov_sub = "Unconstrained Dynamic Response"
    
    if gov_enabled:
        if adaptive_gov:
            last_imb = history[-1]["system"]["spatial_imbalance"] if len(history) > 0 else 0.0
            threshold = model.adaptive_governance_threshold
            is_stressed = (last_imb > threshold)
            
            if is_stressed:
                gov_status = "ADAPTIVE ACTIVE"
                gov_icon = "🧿"
                gov_bg = "#2d2013"
                gov_border = "#ff8c00"
                gov_text_color = "#ffffff"
                gov_sub = f"Imbalance: {last_imb:.3f} / {threshold:.3f}<br>Governance intervention active"
            else:
                gov_status = "ADAPTIVE DORMANT"
                gov_icon = "🧿"
                gov_bg = "#141e16"
                gov_border = "#93c47d"
                gov_text_color = "#eaecef"
                gov_sub = f"Imbalance: {last_imb:.3f} / {threshold:.3f}<br>Waiting for trigger"
        else:
            gov_status = "STATIC ACTIVE"
            gov_icon = "🧿"
            gov_bg = "#121921"
            gov_border = "#2563eb"
            gov_text_color = "#ffffff"
            gov_sub = f"Fixed Caps: δ={model.delta:.1f} | R_max={model.R_max}"

    # STRESS BG SELECTION
    if unmet_ratio < 0.05:
        stress_bg = "#141e16"
    elif unmet_ratio < 0.30:
        stress_bg = "#2d2013"
    else:
        stress_bg = "#2a1919"

    # ROW 0: Executive Status Row (Shock, Governance, Stress)
    exec_col1, exec_col2, exec_col3 = st.columns(3)
    
    with exec_col1:
        st.markdown(f"""<div class="monitor-card-r1" style="border-color: {shock_border}; background-color: {shock_bg}; padding: 18px 12px; height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <div class="monitor-label-r1" style="color: {shock_border if shock_status == 'ACTIVE' else '#c5c7d0'};">Demand Shock Status</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: {shock_text_color}; display: flex; align-items: center; justify-content: center; gap: 6px; padding-top: 2px;">{shock_icon} {shock_status}</div>
            <div style="font-size: 0.72rem; color: #c5c7d0; margin-top: 6px; font-weight: 500;">Zone: Center | Intensity: {current_shock_mult:.1f}x ({shock_phase})</div>
        </div>""", unsafe_allow_html=True)
        
    with exec_col2:
        st.markdown(f"""<div class="monitor-card-r1" style="border-color: {gov_border}; background-color: {gov_bg}; padding: 18px 12px; height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <div class="monitor-label-r1" style="color: {gov_border if 'ACTIVE' in gov_status else '#c5c7d0'};">Governance Status</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: {gov_text_color}; display: flex; align-items: center; justify-content: center; gap: 6px; padding-top: 2px;">{gov_icon} {gov_status}</div>
            <div style="font-size: 0.72rem; color: #c5c7d0; margin-top: 6px; font-weight: 500; line-height: 1.25; text-align: center;">{gov_sub}</div>
        </div>""", unsafe_allow_html=True)
        
    with exec_col3:
        st.markdown(f"""<div class="monitor-card-r1" style="border-color: {status_color}; background-color: {stress_bg}; padding: 18px 12px; height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <div class="monitor-label-r1" style="color: {status_color};">Current System Stress</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: {status_color}; display: flex; align-items: center; justify-content: center; gap: 4px; padding-top: 2px;">{status_text}</div>
            <div style="font-size: 0.72rem; color: #c5c7d0; margin-top: 6px; font-weight: 500;">Unmet Ratio: {unmet_ratio:.2f}</div>
        </div>""", unsafe_allow_html=True)

    # SECTION 1: Run Metrics
    st.markdown('<div style="font-size: 0.75rem; font-weight: 600; color: #a3a6b5; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 15px; margin-bottom: 5px; text-align: left;">Run Metrics</div>', unsafe_allow_html=True)
    run_col1, run_col2, run_col3, run_col4, run_col5, run_col6 = st.columns(6)

    with run_col1:
        st.markdown(f"""<div class="monitor-card-r1">
            <div class="monitor-label-r1">Avg Service Rate</div>
            <div class="monitor-value-r1">{avg_service_rate:.1%}</div>
        </div>""", unsafe_allow_html=True)

    with run_col2:
        st.markdown(f"""<div class="monitor-card-r1">
            <div class="monitor-label-r1">Avg Fleet Utilization</div>
            <div class="monitor-value-r1">{avg_utilization:.1%}</div>
        </div>""", unsafe_allow_html=True)

    with run_col3:
        st.markdown(f"""<div class="monitor-card-r1">
            <div class="monitor-label-r1">Avg Spatial Imbalance</div>
            <div class="monitor-value-r1">{avg_spatial_imbalance:.3f}</div>
        </div>""", unsafe_allow_html=True)

    with run_col4:
        st.markdown(f"""<div class="monitor-card-r1">
            <div class="monitor-label-r1">Revenue per Vehicle</div>
            <div class="monitor-value-r1">${rev_per_vehicle:,.2f}</div>
        </div>""", unsafe_allow_html=True)

    with run_col5:
        st.markdown(f"""<div class="monitor-card-r1">
            <div class="monitor-label-r1">Price Volatility</div>
            <div class="monitor-value-r1">{price_volatility:.3f}</div>
        </div>""", unsafe_allow_html=True)

    with run_col6:
        st.markdown(f"""<div class="monitor-card-r1">
            <div class="monitor-label-r1">Overload Frequency</div>
            <div class="monitor-value-r1">{overload_frequency:.1%}</div>
        </div>""", unsafe_allow_html=True)

    # SECTION 2: Current State
    st.markdown('<div style="font-size: 0.75rem; font-weight: 600; color: #a3a6b5; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 15px; margin-bottom: 5px; text-align: left;">Current State</div>', unsafe_allow_html=True)
    curr_col1, curr_col2, curr_col3, curr_col4 = st.columns(4)

    with curr_col1:
        st.markdown(f"""<div class="monitor-card-r2">
            <div class="monitor-label-r2">Current Service Rate</div>
            <div class="monitor-value-r2">{service_rate:.1%}</div>
        </div>""", unsafe_allow_html=True)

    with curr_col2:
        st.markdown(f"""<div class="monitor-card-r2">
            <div class="monitor-label-r2">Current Fleet Utilization</div>
            <div class="monitor-value-r2">{utilization:.1%}</div>
        </div>""", unsafe_allow_html=True)

    with curr_col3:
        st.markdown(f"""<div class="monitor-card-r2">
            <div class="monitor-label-r2">Current Spatial Imbalance</div>
            <div class="monitor-value-r2" style="color: {imbalance_color};">{imbalance:.3f}</div>
        </div>""", unsafe_allow_html=True)

    with curr_col4:
        st.markdown(f"""<div class="monitor-card-r2">
            <div class="monitor-label-r2">Current Unmet Demand</div>
            <div class="monitor-value-r2">{unmet_demand}</div>
        </div>""", unsafe_allow_html=True)

    # SECTION 3: Diagnostics
    st.markdown('<div style="font-size: 0.75rem; font-weight: 600; color: #a3a6b5; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 15px; margin-bottom: 5px; text-align: left;">Diagnostics</div>', unsafe_allow_html=True)
    diag_col1, diag_col2, diag_col3 = st.columns(3)

    with diag_col1:
        st.markdown(f"""<div class="monitor-card-r2">
            <div class="monitor-label-r2">Governance Activation</div>
            <div class="monitor-value-r2">{gov_activation_str}</div>
        </div>""", unsafe_allow_html=True)

    with diag_col2:
        st.markdown(f"""<div class="monitor-card-r2">
            <div class="monitor-label-r2">Trips Served</div>
            <div class="monitor-value-r2">{total_trips:,}</div>
        </div>""", unsafe_allow_html=True)

    with diag_col3:
        st.markdown(f"""<div class="monitor-card-r2">
            <div class="monitor-label-r2">Tick</div>
            <div class="monitor-value-r2">{current_step}</div>
        </div>""", unsafe_allow_html=True)

    st.write("")  # Margin space

    # --- 5. Main Content Panel ---
    col_map, col_charts = st.columns([5, 5])

    with col_map:
        # Render the interactive spatial map with crawling vehicle dots
        map_fig = plot_spatial_network(model)
        st.plotly_chart(map_fig, use_container_width=True, key="spatial_network_map")
        
        # Dark unified spatial legend directly underneath the map
        st.markdown("""<div style="background-color: #0f1115; border: 1px solid #1f242e; border-radius: 6px; padding: 12px 16px; margin-top: -12px; margin-bottom: 15px; display: flex; justify-content: space-around; align-items: center; gap: 15px; flex-wrap: wrap; width: 100%;">
<!-- 1. Color Scale (Unmet Demand Ratio) -->
<div style="display: flex; align-items: center; gap: 8px;">
    <span style="font-size: 0.9rem; color: #c5c7d0; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Unmet Ratio:</span>
    <span style="font-size: 0.85rem; color: #a3a6b5;">0.0</span>
    <div style="width: 80px; height: 6px; border-radius: 3px; background: linear-gradient(to right, #1e1b4b, #d946ef, #f97316, #facc15); border: 1px solid rgba(255, 255, 255, 0.05); margin: 0 4px;"></div>
    <span style="font-size: 0.85rem; color: #a3a6b5;">1.0</span>
</div>

<!-- Vertical Separator -->
<div style="width: 1px; height: 16px; background-color: #1f242e;"></div>

<!-- 2. Vehicle Indicators -->
<div style="display: flex; align-items: center; gap: 15px;">
    <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.9rem; color: #d1d4dc;">
        <span style="color: #3b82f6; font-size: 1.2rem; line-height: 1;">●</span> Passenger Trips
    </span>
    <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.9rem; color: #d1d4dc;">
        <span style="color: #8b5cf6; font-size: 1.2rem; line-height: 1;">●</span> Rebalancing Flows
    </span>
</div>

<!-- Vertical Separator -->
<div style="width: 1px; height: 16px; background-color: #1f242e;"></div>

<!-- 3. Circle Size (Demand) -->
<div style="display: flex; align-items: center; gap: 8px;">
    <span style="font-size: 0.9rem; color: #c5c7d0; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 4px;">Demand:</span>
    <span style="width: 5px; height: 5px; border-radius: 50%; background-color: #a3a6b5; display: inline-block; vertical-align: middle;"></span>
    <span style="font-size: 0.85rem; color: #a3a6b5; margin-right: 4px;">Low</span>
    <span style="width: 10px; height: 10px; border-radius: 50%; background-color: #a3a6b5; display: inline-block; vertical-align: middle;"></span>
    <span style="font-size: 0.85rem; color: #a3a6b5; margin-right: 4px;">Med</span>
    <span style="width: 16px; height: 16px; border-radius: 50%; background-color: #a3a6b5; display: inline-block; vertical-align: middle;"></span>
    <span style="font-size: 0.85rem; color: #a3a6b5;">High</span>
</div>
</div>""", unsafe_allow_html=True)




    with col_charts:
        # Toggle to show all charts simultaneously
        show_all = st.checkbox("Show All Charts", value=True, help="Display all four analysis charts simultaneously in a 2x2 grid instead of tabs.")
        
        if show_all:
            # Row 1 of 2x2 grid
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>Vehicle Allocation</div>", unsafe_allow_html=True)
                fleet_fig = plot_fleet_states_chart(history)
                st.plotly_chart(fleet_fig, use_container_width=True, key="all_fleet_operational_states_chart")
            with t_col2:
                st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>System Imbalance & Service Rate</div>", unsafe_allow_html=True)
                imbal_fig = plot_imbalance_chart(history)
                st.plotly_chart(imbal_fig, use_container_width=True, key="all_spatial_imbalance_performance_chart")
                
            # Row 2 of 2x2 grid
            t_col3, t_col4 = st.columns(2)
            with t_col3:
                st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>Dynamic Zone Prices</div>", unsafe_allow_html=True)
                prices_fig = plot_prices_chart(history)
                st.plotly_chart(prices_fig, use_container_width=True, key="all_dynamic_prices_trend_chart")
            with t_col4:
                st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>Unmet Demand</div>", unsafe_allow_html=True)
                unmet_fig = plot_unmet_demand_chart(history)
                st.plotly_chart(unmet_fig, use_container_width=True, key="all_unmet_demand_queue_chart")
                
            # Row 3: Stability Space chart placed below the grid
            st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-top: 15px; margin-bottom: 5px; text-align: center;'>Stability Space (Imbalance vs Service Rate)</div>", unsafe_allow_html=True)
            stability_fig = plot_stability_space_chart(history, model.adaptive_governance_threshold)
            st.plotly_chart(stability_fig, use_container_width=True, key="all_stability_space_chart")
        else:
            # Grid for time series charts in tabs, with Stability Space as a 3rd tab
            chart_tabs = st.tabs(["Fleet & Balance", "Prices & Unmet", "Stability Space"])
            
            with chart_tabs[0]:
                t_col1, t_col2 = st.columns(2)
                with t_col1:
                    st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>Vehicle Allocation</div>", unsafe_allow_html=True)
                    fleet_fig = plot_fleet_states_chart(history)
                    st.plotly_chart(fleet_fig, use_container_width=True, key="fleet_operational_states_chart")
                with t_col2:
                    st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>System Imbalance & Service Rate</div>", unsafe_allow_html=True)
                    imbal_fig = plot_imbalance_chart(history)
                    st.plotly_chart(imbal_fig, use_container_width=True, key="spatial_imbalance_performance_chart")
                    
            with chart_tabs[1]:
                t_col3, t_col4 = st.columns(2)
                with t_col3:
                    st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>Dynamic Zone Prices</div>", unsafe_allow_html=True)
                    prices_fig = plot_prices_chart(history)
                    st.plotly_chart(prices_fig, use_container_width=True, key="dynamic_prices_trend_chart")
                with t_col4:
                    st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>Unmet Demand</div>", unsafe_allow_html=True)
                    unmet_fig = plot_unmet_demand_chart(history)
                    st.plotly_chart(unmet_fig, use_container_width=True, key="unmet_demand_queue_chart")
                    
            with chart_tabs[2]:
                st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #eaecef; margin-bottom: 5px; text-align: center;'>Stability Space (Imbalance vs Service Rate)</div>", unsafe_allow_html=True)
                stability_fig = plot_stability_space_chart(history, model.adaptive_governance_threshold)
                st.plotly_chart(stability_fig, use_container_width=True, key="stability_space_chart")





    # --- 6. Simulation Loop runner ---
    if st.session_state.is_running:
        # Step the model
        model.step()
        st.session_state.tick_count += 1

# Render the fragment-isolated dashboard area
render_live_dashboard(model, controls)
