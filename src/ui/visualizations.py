"""
Visualizations module for the thesis simulation dashboard.
Generates Plotly figures for the spatial network map and time series charts.
"""

import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from src.config import ZONES, TRAVEL_TIMES
from src.agents import VehicleState

# Pre-defined coordinates for spatial layout (Modern NetLogo-style arrangement)
# Center in center, residential in suburbs, airport in the far corner
ZONE_POS = {
    "C":  (0.0, 0.0),
    "R1": (-1.8, 1.2),
    "R2": (1.8, 1.2),
    "R3": (-1.8, -1.2),
    "R4": (1.8, -1.2),
    "A":  (3.0, 0.0),
}


def plot_spatial_network(model):
    """
    Generate a Plotly figure representing the spatial zone network.
    - Nodes are sized by idle vehicles and colored by unmet demand ratio.
    - Crawling dots show in-transit vehicles (serving or rebalancing).
    - Connective edges represent travel links.
    """
    fig = go.Figure()
    
    # 1. Draw Travel Links (Edges) between zones
    edge_x = []
    edge_y = []
    for z1 in ZONES:
        for z2 in ZONES:
            if z1 != z2:
                x1, y1 = ZONE_POS[z1]
                x2, y2 = ZONE_POS[z2]
                edge_x.extend([x1, x2, None])
                edge_y.extend([y1, y2, None])
                
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.7, color="rgba(100, 100, 100, 0.3)"),
        hoverinfo="none",
        mode="lines",
        name="Travel Paths",
        showlegend=False
    ))
    
    # 1.5 Draw Active Rebalancing Flows (Thick semi-transparent lines with midpoint arrows)
    rebalance_flows = {}
    for vehicle in model.agents:
        if vehicle.state == VehicleState.REBALANCING:
            orig = vehicle.origin_zone
            dest = vehicle.destination_zone
            if orig and dest:
                rebalance_flows[(orig, dest)] = rebalance_flows.get((orig, dest), 0) + 1

    for (orig, dest), count in rebalance_flows.items():
        if count > 0:
            x_o, y_o = ZONE_POS[orig]
            x_d, y_d = ZONE_POS[dest]
            
            # Midpoint for directional arrow
            x_mid = x_o + 0.5 * (x_d - x_o)
            y_mid = y_o + 0.5 * (y_d - y_o)
            
            # Thick flow line
            width = 1.0 + count * 1.5
            fig.add_trace(go.Scatter(
                x=[x_o, x_d], y=[y_o, y_d],
                mode="lines",
                line=dict(width=width, color="rgba(139, 92, 246, 0.6)"),
                hoverinfo="text",
                text=f"Active Rebalancing Flow: {orig} -> {dest}<br>Vehicles: {count}",
                showlegend=False
            ))
            
            # Midpoint directional arrow
            fig.add_annotation(
                x=x_mid, y=y_mid,
                ax=x_o, ay=y_o,
                xref="x", yref="y",
                axref="x", ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=max(2, int(width * 0.8)),
                arrowcolor="rgba(139, 92, 246, 0.85)",
                standoff=2,
                startstandoff=2
            )

    # 2. Track In-Transit Vehicles (Serving & Rebalancing)
    transit_x = []
    transit_y = []
    transit_colors = []
    transit_texts = []
    
    for vehicle in model.agents:
        if vehicle.state != VehicleState.IDLE:
            # Calculate position along its route based on progress
            orig = vehicle.origin_zone
            dest = vehicle.destination_zone
            
            x_o, y_o = ZONE_POS[orig]
            x_d, y_d = ZONE_POS[dest]
            
            total_time = model.travel_times[orig][dest]
            time_left = vehicle.time_left
            
            # Progress from 0.0 to 1.0 (clamped)
            progress = 1.0 - (time_left / total_time) if total_time > 0 else 1.0
            progress = max(0.0, min(1.0, progress))
            
            # Linear interpolation (add a small offset to separate serving from rebalancing if necessary)
            x_pos = x_o + progress * (x_d - x_o)
            y_pos = y_o + progress * (y_d - y_o)
            
            transit_x.append(x_pos)
            transit_y.append(y_pos)
            
            if vehicle.state == VehicleState.SERVING:
                transit_colors.append("#3b82f6")  # Blue for serving
                transit_texts.append(f"Vehicle serving trip: {orig} ➡️ {dest}<br>Time left: {time_left} ticks")
            else:
                transit_colors.append("#8b5cf6")  # Violet for rebalancing
                transit_texts.append(f"Vehicle rebalancing: {orig} ➡️ {dest}<br>Time left: {time_left} ticks")

    # Add in-transit vehicles to plot
    if transit_x:
        fig.add_trace(go.Scatter(
            x=transit_x, y=transit_y,
            mode="markers",
            marker=dict(
                size=8,
                color=transit_colors,
                line=dict(width=1, color="white")
            ),
            text=transit_texts,
            hoverinfo="text",
            name="In Transit",
            showlegend=False
        ))
        
    # 3. Draw Zone Nodes
    node_x = []
    node_y = []
    node_sizes = []
    node_colors = []
    node_hover_texts = []
    
    for zone in ZONES:
        x, y = ZONE_POS[zone]
        node_x.append(x)
        node_y.append(y)
        
        # Get zone states
        idle_count = sum(1 for v in model.agents if v.state == VehicleState.IDLE and v.current_zone == zone)
        serving_count = sum(1 for v in model.agents if v.state == VehicleState.SERVING and v.origin_zone == zone)
        rebalance_count = sum(1 for v in model.agents if v.state == VehicleState.REBALANCING and v.origin_zone == zone)
        
        price = model.prices[zone]
        unmet = model.unmet_demand[zone]
        
        # Pull last step stats
        history_step = model.history[-1] if model.history else None
        if history_step and zone in history_step["zones"]:
            effective_demand = history_step["zones"][zone]["effective_demand"]
            service_rate = history_step["zones"][zone]["service_rate"]
        else:
            effective_demand = 0
            service_rate = 1.0
            
        # Node size represents current effective demand
        # Ensure a base size so empty zones remain clickable/visible
        size = 16 + int(math.sqrt(effective_demand) * 12)
        node_sizes.append(size)
        
        # Color represents unmet demand ratio (normalized continuously over [0, 1])
        unmet_demand_ratio = unmet / max(effective_demand, 1.0)
        unmet_demand_ratio = max(0.0, min(1.0, unmet_demand_ratio))
        node_colors.append(unmet_demand_ratio)
        
        text = (
            f"<b>Zone {zone}</b><br>"
            f"Price: ${price:.2f}<br>"
            f"Idle Fleet: {idle_count} vehicles<br>"
            f"Effective Demand: {effective_demand}<br>"
            f"Unmet Demand Ratio: {unmet_demand_ratio:.1%}<br>"
            f"Unmet Demand: {unmet}<br>"
            f"Service Rate (Last Step): {service_rate:.1%}"
        )
        node_hover_texts.append(text)
        
        # Add labels to the nodes (current price + current idle vehicles)
        fig.add_annotation(
            x=x, y=y + 0.35,
            text=f"<b>{zone}</b><br>${price:.1f} | Idle: {idle_count}",
            showarrow=False,
            font=dict(size=10, color="white"),
            bgcolor="rgba(20, 20, 20, 0.65)",
            bordercolor="rgba(100, 100, 100, 0.4)",
            borderwidth=1,
            borderpad=3
        )

    # Plot zones
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        marker=dict(
            showscale=False,
            colorscale=[
                [0.0, "#1e1b4b"],     # Dark blue-purple
                [0.33, "#d946ef"],    # Magenta
                [0.66, "#f97316"],    # Orange
                [1.0, "#facc15"]      # Yellow
            ],
            cmin=0.0,
            cmax=1.0,
            color=node_colors,
            size=node_sizes,
            line=dict(width=2, color="white")
        ),
        text=node_hover_texts,
        hoverinfo="text",
        name="Zones",
        showlegend=False
    ))

    # Clean Dark Theme Layout
    fig.update_layout(
        plot_bgcolor="#0f1115",
        paper_bgcolor="#0f1115",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.3, 3.8]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.8, 1.8]),
        margin=dict(l=5, r=5, t=10, b=5),
        height=480,
        showlegend=False
    )
    return fig


def plot_prices_chart(history):
    """Plot price trends for each zone over ticks, aggregating residential zones."""
    fig = go.Figure()
    if not history:
        return fig
        
    steps = [h["step"] for h in history]
    
    # 1. Residential Avg Price
    res_avg_prices = [
        sum(h["zones"][z]["price"] for z in ["R1", "R2", "R3", "R4"]) / 4.0
        for h in history
    ]
    fig.add_trace(go.Scatter(x=steps, y=res_avg_prices, mode="lines+markers", name="Residential Avg", line=dict(color="#60a5fa", width=2), marker=dict(size=4)))
    
    # 2. Center Price
    center_prices = [h["zones"]["C"]["price"] for h in history]
    fig.add_trace(go.Scatter(x=steps, y=center_prices, mode="lines+markers", name="Center", line=dict(color="#d946ef", width=2), marker=dict(size=4)))
    
    # 3. Airport Price
    airport_prices = [h["zones"]["A"]["price"] for h in history]
    fig.add_trace(go.Scatter(x=steps, y=airport_prices, mode="lines+markers", name="Airport", line=dict(color="#facc15", width=2), marker=dict(size=4)))
        
    # Baseline reference lines (static values from config)
    fig.add_hline(y=15.0, line_dash="dash", line_color="rgba(96, 165, 250, 0.4)", line_width=1)
    fig.add_hline(y=18.0, line_dash="dash", line_color="rgba(217, 70, 239, 0.4)", line_width=1)
    fig.add_hline(y=25.0, line_dash="dash", line_color="rgba(250, 204, 21, 0.4)", line_width=1)
        
    fig.update_layout(
        xaxis=dict(
            title=dict(text="Simulation Ticks", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0")
        ),
        yaxis=dict(
            title=dict(text="Price ($)", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0")
        ),
        plot_bgcolor="#181a20",
        paper_bgcolor="#181a20",
        font=dict(color="white"),
        height=270,
        margin=dict(l=35, r=10, t=10, b=45),
        legend=dict(
            orientation="h", x=0.5, y=-0.35, xanchor="center",
            font=dict(size=9, color="#eaecef")
        )
    )
    add_shock_shading(fig, history)
    return fig


def plot_unmet_demand_chart(history):
    """Plot unmet demand per zone over ticks, aggregating residential zones."""
    fig = go.Figure()
    if not history:
        return fig
        
    steps = [h["step"] for h in history]
    
    # 1. Residential Avg Unmet Demand
    res_avg_unmet = [
        sum(h["zones"][z]["unmet_demand"] for z in ["R1", "R2", "R3", "R4"]) / 4.0
        for h in history
    ]
    fig.add_trace(go.Scatter(x=steps, y=res_avg_unmet, mode="lines+markers", name="Residential Avg", line=dict(color="#60a5fa", width=2), marker=dict(size=4)))
    
    # 2. Center Unmet Demand
    center_unmet = [h["zones"]["C"]["unmet_demand"] for h in history]
    fig.add_trace(go.Scatter(x=steps, y=center_unmet, mode="lines+markers", name="Center", line=dict(color="#d946ef", width=2), marker=dict(size=4)))
    
    # 3. Airport Unmet Demand
    airport_unmet = [h["zones"]["A"]["unmet_demand"] for h in history]
    fig.add_trace(go.Scatter(x=steps, y=airport_unmet, mode="lines+markers", name="Airport", line=dict(color="#facc15", width=2), marker=dict(size=4)))
        
    fig.update_layout(
        xaxis=dict(
            title=dict(text="Simulation Ticks", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0")
        ),
        yaxis=dict(
            title=dict(text="Requests", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0")
        ),
        plot_bgcolor="#181a20",
        paper_bgcolor="#181a20",
        font=dict(color="white"),
        height=270,
        margin=dict(l=35, r=10, t=10, b=45),
        showlegend=False
    )
    add_shock_shading(fig, history)
    return fig


def plot_fleet_states_chart(history):
    """Plot global fleet distribution (Idle vs Serving vs Rebalancing)."""
    fig = go.Figure()
    if not history:
        return fig
        
    steps = [h["step"] for h in history]
    idle = [h["system"]["idle_vehicles"] for h in history]
    serving = [h["system"]["serving_vehicles"] for h in history]
    rebalance = [h["system"]["rebalancing_vehicles"] for h in history]
    
    fig.add_trace(go.Scatter(
        x=steps, y=idle, mode="lines", name="Idle",
        stackgroup="one", fillcolor="rgba(100, 100, 100, 0.4)", line=dict(color="#888", width=1)
    ))
    fig.add_trace(go.Scatter(
        x=steps, y=serving, mode="lines", name="Serving",
        stackgroup="one", fillcolor="rgba(0, 212, 255, 0.4)", line=dict(color="#00d4ff", width=1)
    ))
    fig.add_trace(go.Scatter(
        x=steps, y=rebalance, mode="lines", name="Rebalancing",
        stackgroup="one", fillcolor="rgba(255, 140, 0, 0.4)", line=dict(color="#ff8c00", width=1)
    ))
    
    fig.update_layout(
        xaxis=dict(
            title=dict(text="Simulation Ticks", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0")
        ),
        yaxis=dict(
            title=dict(text="Vehicles Count", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0")
        ),
        plot_bgcolor="#181a20",
        paper_bgcolor="#181a20",
        font=dict(color="white"),
        height=270,
        margin=dict(l=35, r=10, t=10, b=45),
        legend=dict(
            orientation="h", x=0.5, y=-0.35, xanchor="center",
            font=dict(size=9, color="#eaecef")
        )
    )
    add_shock_shading(fig, history)
    return fig


def plot_imbalance_chart(history):
    """Plot the spatial imbalance index and system service rate over ticks."""
    fig = go.Figure()
    if not history:
        return fig
        
    steps = [h["step"] for h in history]
    imbalance = [h["system"].get("spatial_imbalance", h["system"].get("imbalance_index", 0.0)) for h in history]
    service_rate = [h["system"]["service_rate"] * 100 for h in history]  # In %
    
    fig.add_trace(go.Scatter(
        x=steps, y=imbalance, mode="lines", name="Imbalance Index (LHS)",
        line=dict(color="#e06666", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=steps, y=service_rate, mode="lines", name="Service Rate % (RHS)",
        line=dict(color="#93c47d", width=2), yaxis="y2"
    ))
    
    fig.update_layout(
        xaxis=dict(
            title=dict(text="Simulation Ticks", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0")
        ),
        yaxis=dict(
            title=dict(text="Imbalance Index", font=dict(color="#e06666", size=10)),
            tickfont=dict(color="#e06666", size=9)
        ),
        yaxis2=dict(
            title=dict(text="Service Rate %", font=dict(color="#93c47d", size=10)),
            tickfont=dict(color="#93c47d", size=9),
            overlaying="y", side="right", range=[0, 105]
        ),
        plot_bgcolor="#181a20",
        paper_bgcolor="#181a20",
        font=dict(color="white"),
        height=270,
        margin=dict(l=35, r=35, t=10, b=45),
        legend=dict(
            orientation="h", x=0.5, y=-0.35, xanchor="center",
            font=dict(size=9, color="#eaecef")
        )
    )
    add_shock_shading(fig, history)
    return fig


def add_shock_shading(fig, history):
    """Add subtle background shading for active demand shock periods."""
    if not history:
        return fig
    last_entry = history[-1]
    shock_mode = last_entry.get("system", {}).get("shock_mode", "No Demand Shock")
    if shock_mode == "No Demand Shock":
        return fig
        
    max_step = max(h["step"] for h in history)
    
    intervals = []
    if shock_mode == "Demand Shock":
        intervals.append((20, 36))
    elif shock_mode == "Repeated Demand Shocks":
        # Repeated shocks start at 20, 60, 100, ... and last 16 ticks (until tick 36, 76, 116, ...)
        start = 20
        while start <= max_step + 40:
            intervals.append((start, start + 16))
            start += 40
            
    for start, end in intervals:
        if start <= max_step:
            fig.add_vrect(
                x0=start, x1=min(end, max_step),
                fillcolor="rgba(239, 68, 68, 0.08)",
                layer="below",
                line_width=0,
                annotation_text="SHOCK" if start == 20 else "",
                annotation_position="inside top left",
                annotation_font=dict(size=8, color="rgba(239, 68, 68, 0.5)")
            )
    return fig


def plot_stability_space_chart(history, adaptive_threshold=0.15):
    """Plot the Stability Space trajectory: Imbalance Index (X) vs Service Rate % (Y)."""
    fig = go.Figure()
    if not history:
        return fig
        
    imbalance = [h["system"].get("spatial_imbalance", h["system"].get("imbalance_index", 0.0)) for h in history]
    service_rate = [h["system"]["service_rate"] * 100 for h in history]  # In %
    steps = [h["step"] for h in history]
    
    max_imb = max(imbalance) if imbalance else 0.0
    # Dynamic range with a tight default upper bound of 0.25 and a 10% safety margin:
    max_x = max(0.25, max_imb * 1.10)
    imb_range = [-0.015, max_x]
    
    # 1. Add objective vertical reference line at the governance trigger threshold
    fig.add_vline(
        x=adaptive_threshold,
        line_dash="dash",
        line_color="rgba(255, 140, 0, 0.65)",  # Subtle stress orange
        line_width=1.5,
        annotation_text="Governance trigger threshold",
        annotation_position="top right",
        annotation_font=dict(size=9, color="rgba(255, 140, 0, 0.8)", family="Outfit")
    )
    
    # 2. Connected line trajectory (translucent purple/violet)
    fig.add_trace(go.Scatter(
        x=imbalance, y=service_rate,
        mode="lines",
        name="Trajectory Path",
        line=dict(color="rgba(139, 92, 246, 0.4)", width=2),
        hoverinfo="skip"
    ))
    
    # 3. Historical points with gradient (earlier points lighter/faded)
    fig.add_trace(go.Scatter(
        x=imbalance, y=service_rate,
        mode="markers",
        name="Ticks Trajectory",
        marker=dict(
            size=6,
            color=steps,
            colorscale=[
                [0, "rgba(80, 80, 100, 0.25)"],
                [0.5, "rgba(100, 110, 150, 0.65)"],
                [1.0, "rgba(0, 212, 255, 0.95)"]
            ],
            showscale=False
        ),
        text=[f"Tick {s}<br>Imbalance: {imb:.3f}<br>Service Rate: {sr:.1f}%" for s, imb, sr in zip(steps, imbalance, service_rate)],
        hoverinfo="text"
    ))
    
    # 4. Highlight the current (latest) position with a prominent yellow glowing target marker
    if len(history) > 0:
        # Outer glowing outer ring
        fig.add_trace(go.Scatter(
            x=[imbalance[-1]], y=[service_rate[-1]],
            mode="markers",
            name="Current Glow",
            marker=dict(
                size=20,
                color="rgba(250, 204, 21, 0.22)",
                line=dict(color="#facc15", width=1.5),
            ),
            hoverinfo="skip"
        ))
        
        # Inner target dot
        fig.add_trace(go.Scatter(
            x=[imbalance[-1]], y=[service_rate[-1]],
            mode="markers+text",
            name="Current Position",
            marker=dict(
                size=11,
                color="#facc15",
                line=dict(color="#ffffff", width=2),
                symbol="circle-dot"
            ),
            text=["Current"],
            textposition="top center",
            textfont=dict(size=9, color="#facc15", family="Outfit"),
            hoverinfo="text"
        ))
        
    fig.update_layout(
        xaxis=dict(
            title=dict(text="Spatial Imbalance Index", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0"),
            range=imb_range,
            gridcolor="#22252c",
            zerolinecolor="#22252c"
        ),
        yaxis=dict(
            title=dict(text="Service Rate %", font=dict(size=10, color="#c5c7d0")),
            tickfont=dict(size=9, color="#c5c7d0"),
            range=[-5, 105],
            gridcolor="#22252c",
            zerolinecolor="#22252c"
        ),
        plot_bgcolor="#181a20",
        paper_bgcolor="#181a20",
        font=dict(color="white"),
        height=270,
        margin=dict(l=35, r=10, t=10, b=45),
        showlegend=False
    )
    return fig

