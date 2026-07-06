# Exploratory Adaptive Governance Extension: Stress Tests and Robustness Analysis

This report documents the design, results, and interpretation of the exploratory adaptive governance extension under the final calibrated model configuration ($N = 80$ vehicles, $50\%$ backlog carry-over rate). All findings are derived from the 50-seed Monte Carlo stress tests and one-factor-at-a-time (OFAT) parameter sweeps.

---

## 1. Motivation

The baseline simulation model showed that while the system is highly efficient under normal demand conditions, severe demand surges (such as repeated demand shocks) can induce price instability and supply distribution challenges. 

This exploratory extension investigates whether an **event-triggered adaptive governance mechanism** can serve as an emergency stabilization buffer. By analyzing the system under multiple shock intensities ($4.0\times$, $6.0\times$, and $8.0\times$ peak demand multipliers), we identify the boundary conditions under which dynamic governance triggers activate and evaluate whether they can mitigate volatility without imposing the continuous efficiency penalties of static controls.

---

## 2. Adaptive Governance Design

Unlike static governance, which remains permanently active, the event-triggered adaptive governance mechanism implements a split-state framework:
* **Activation Rule (Event-Triggered)**: The mechanism remains dormant during normal operation and activates only in response to a systemic crisis. The trigger is activated at tick $t$ if the spatial imbalance of the previous tick exceeds $0.14$ ($I_{t-1} > 0.14$) **and** the platform has experienced an overload state (unmet demand ratio $\ge 0.30$) for at least 3 of the last 5 ticks.
* **Pricing Dampening**: Based on findings from static governance sweeps showing that rebalancing constraints degrade matching efficiency, the adaptive mechanism focuses exclusively on pricing constraints. When active, it caps price adjustments at a maximum of $\delta = 2.0$ per tick.
* **Unconstrained Rebalancing**: To preserve spatial recovery and maximize passenger matching, rebalancing remains unconstrained ($\theta = 0.0$ and $R_{max} = 999$) in both normal and active stress states.

---

## 3. Experimental Setup

* **Model Calibration**: $N = 80$ total vehicles, $50\%$ backlog carry-over rate with nearest integer rounding.
* **Scenarios**: Unconstrained *Interaction* baseline versus *Event-Triggered Adaptive Governance*.
* **Shock Intensities**: Repeated demand shocks with peak multipliers of $4.0\times$, $6.0\times$, and $8.0\times$ in the center zone.
* **Execution**: 50 random seeds per configuration, 500 ticks per simulation run.

---

## 4. Simulation Results

The table below summarizes the aggregated means across the 50 Monte Carlo seeds for both regimes.

### Table 1: Stress Test Results (50 seeds, 500 ticks, N=80)

| Shock | Scenario | Service Rate | Overload Freq. | Revenue/Veh. | Price Volatility | Avg. Imbalance | Max Imbalance | Activation % |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **4.0\times** | Interaction | 73.05% | 33.52% | \$1232.11 | 2.951 | 0.074 | 0.139 | 0.00% |
| **4.0\times** | Adaptive Gov | 73.05% | 33.54% | \$1231.59 | 2.948 | 0.074 | 0.139 | **0.00%** |
| **6.0\times** | Interaction | 61.44% | 48.89% | \$2541.42 | 6.706 | 0.086 | 0.149 | 0.00% |
| **6.0\times** | Adaptive Gov | 61.50% | 48.71% | \$2520.00 | 6.618 | 0.086 | 0.148 | **0.24%** |
| **8.0\times** | Interaction | 51.95% | 56.44% | \$3943.94 | 10.937 | 0.100 | 0.183 | 0.00% |
| **8.0\times** | Adaptive Gov | 50.67% | 55.22% | \$3219.00 | 9.134 | 0.101 | 0.190 | **6.98%** |

### Table 2: Relative Performance Changes (Adaptive vs. Interaction)

| Shock | Service Rate | Overload Freq. | Revenue/Veh. | Price Volatility | Volatility Change | Max Imbalance |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **4.0\times** | +0.00% | +0.01% | -\$0.52 | -0.003 | **-0.08%** | 0.000 |
| **6.0\times** | +0.06% | -0.18% | -\$21.42 | -0.088 | **-1.31%** | -0.001 |
| **8.0\times** | -1.28% | -1.21% | -\$724.94 | -1.802 | **-16.48%** | +0.007 |

*Key Takeaway*: Under moderate shock conditions (4.0x), the spatial imbalance never crosses the 0.14 threshold, leaving the adaptive mechanism completely inactive (0.00% activation). At 8.0x, it activates for approximately 7% of ticks, successfully reducing price volatility by **16.5%** with only a minor ($1.28\%$) service rate change.

---

## 5. Parameter Robustness Analysis

To verify that the stabilization benefits of event-triggered governance are not highly dependent on our specific design choice of unconstrained rebalancing, we perform a one-factor-at-a-time (OFAT) parameter sweep under the extreme $8.0\times$ repeated shock.

### Table 3: OFAT Robustness Results under 8.0x shock (50 seeds, N=80)

| Parameter Group | $\delta$ | $\theta$ | $R_{max}$ | Service Rate | Overload Freq. | Revenue/Veh. | Price Volatility | Avg. Imbalance | Activation % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Price Damping ($\delta$)** | 1.0 | 0.0 | 999 | 50.41% | 55.49% | \$3121.66 | 8.938 | 0.101 | 7.52% |
| | **2.0** | **0.0** | **999** | **50.67%** | **55.22%** | **\$3219.00** | **9.134** | **0.101** | **6.98%** |
| | 3.0 | 0.0 | 999 | 50.74% | 55.80% | \$3260.81 | 9.211 | 0.101 | 6.85% |
| **Reb. Threshold ($\theta$)** | 2.0 | 0.0 | 999 | 50.67% | 55.22% | \$3219.00 | 9.134 | 0.101 | 6.98% |
| | 2.0 | 1.0 | 999 | 50.35% | 55.70% | \$3146.46 | 8.988 | 0.101 | 7.71% |
| | 2.0 | 2.0 | 999 | 50.49% | 55.92% | \$3161.10 | 9.027 | 0.101 | 7.88% |
| **Reb. Limit ($R_{max}$)** | 2.0 | 0.0 | 999 | 50.67% | 55.22% | \$3219.00 | 9.134 | 0.101 | 6.98% |
| | 2.0 | 0.0 | 15 | 50.59% | 55.56% | \$3213.32 | 9.146 | 0.101 | 6.97% |
| | 2.0 | 0.0 | 10 | 50.56% | 55.19% | \$3196.25 | 9.093 | 0.101 | 7.22% |

*Interpretation of Robustness*: The qualitative behavior of the stabilization mechanism is robust. Modifying the price damping limit ($\delta \in [1.0, 3.0]$) behaves predictably, with tighter limits suppressing volatility more at the cost of marginally higher activation frequencies. Restricting rebalancing (via $\theta > 0$ or $R_{max} < 999$) alters metrics slightly but does not disrupt the core capability of the adaptive framework to suppress runaway prices under severe shock.

---


