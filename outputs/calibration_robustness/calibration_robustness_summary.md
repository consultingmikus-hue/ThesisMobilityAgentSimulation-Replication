# Calibration Robustness Analysis

This report provides a structural calibration robustness check for the thesis simulation framework. It evaluates whether key operational outcomes are robust or highly sensitive to two critical design parameters: **(1) Fleet Size ($N$)** and **(2) Dynamic Pricing Sensitivity ($\alpha$)**.

All simulations were executed with $50\%$ backlog carry-over and without demand shocks (50 seeds per configuration, 500 ticks each).

## 1. Fleet Size Sensitivity Analysis

This analysis tests fleet sizes $N \in \{40, 50, 60, 80, 100\}$ under the default dynamic pricing sensitivity ($\alpha = 0.3$). By exploring sizes below the $N = 80$ baseline, we assess how capacity constraints influence pricing dynamics and matching stability under scarcity.

### Table 1: Fleet Size Sensitivity Metrics (Aggregated Means)

| Fleet Size ($N$) | Service Rate | Overload Freq. | Revenue / Vehicle | Price Volatility | Avg. Idle Vehicles | Average Price | Completed Trips |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **40** | 70.55% | 44.61% | $1236.68 | 1.465 | 4.65 | $10.71 | 6611.9 |
| **50** | 76.31% | 29.23% | $746.55 | 1.490 | 8.53 | $6.90 | 7792.7 |
| **60** | 78.93% | 23.14% | $528.64 | 1.433 | 16.16 | $5.46 | 8299.9 |
| **80** | 79.38% | 22.54% | $385.09 | 1.499 | 35.93 | $5.27 | 8380.9 |
| **100** | 79.49% | 22.17% | $301.55 | 1.479 | 55.76 | $5.13 | 8419.8 |

## 2. Dynamic Pricing Sensitivity Robustness (at $N = 60$)

To verify pricing dynamics under moderate capacity constraints, we sweep dynamic pricing sensitivity $\alpha \in \{0.1, 0.2, 0.3, 0.4\}$ at a reference fleet size of $N = 60$ vehicles.

### Table 2: Pricing Sensitivity Metrics (Aggregated Means at N=60)

| Alpha ($\alpha$) | Service Rate | Overload Freq. | Revenue / Vehicle | Price Volatility | Avg. Idle Vehicles | Average Price | Completed Trips |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.1** | 77.86% | 25.35% | $480.64 | 1.391 | 15.63 | $4.76 | 8341.8 |
| **0.2** | 78.62% | 23.57% | $500.30 | 1.288 | 15.89 | $5.06 | 8325.9 |
| **0.3** | 78.93% | 23.14% | $528.64 | 1.433 | 16.16 | $5.46 | 8299.9 |
| **0.4** | 79.10% | 22.40% | $554.93 | 1.585 | 16.66 | $5.88 | 8210.1 |

## 3. Methodological Interpretation

### Fleet Size Sensitivity ($N$)
As fleet size increases, the system transitions smoothly from structural scarcity to oversupply. Under scarcity ($N = 40$), the service rate drops to **70.55%** due to vehicle constraints, and completed trips decrease to **6611.9** (down from **8380.9** at the $N=80$ baseline). Average prices rise to **$10.71** because the shortage triggers high pricing adjustments, which drives revenue per vehicle up to **$1236.68** since active vehicles are highly utilized at premium rates. 

As fleet capacity grows to $N=100$, idle capacity increases substantially (average idle vehicles rises to **55.76**), acting as a buffer that handles spatial demand imbalances. This increases the service rate to **79.49%** and decreases the overload frequency to **22.17%**. 

Importantly, the relationship is monotonic and exhibits diminishing marginal returns: increasing fleet size from $N=60$ to $N=80$ increases the service rate by **0.45%** (from 78.93% to 79.38%), while expanding it further to $N=100$ only yields a **0.11%** improvement (to 79.49%) while significantly inflating idle overhead. This confirms that $N=80$ represents a well-chosen calibration baseline—balancing operational matching performance against fleet idle costs.

### Dynamic Pricing Sensitivity ($\alpha$)
Varying the dynamic pricing sensitivity parameter ($\alpha$) at the reference fleet size of $N=60$ demonstrates that the qualitative conclusions remain stable. As $\alpha$ increases from $0.1$ to $0.4$, price volatility rises from **1.391** to **1.585**, reflecting more aggressive price adjustments in response to supply imbalances. 

Despite higher volatility, the platform's core operational metrics remain robust: the service rate stays within a narrow band of **77.86% to 79.10%**, and completed trips vary by less than $2\%$ (from **8341.8** to **8210.1**). The average price adjusts from **$4.76** to **$5.88** (a difference of **$1.12**). 

This confirms that the Dynamic Pricing sensitivity parameter alters the volatility and speed of market clearing but does not disrupt the fundamental spatial stability or matching capability of the platform.

### Conclusion
This robustness check demonstrates that the simulation's behaviors are stable structural outcomes of the matching and feedback architecture, rather than artifacts of a highly fragile parameter combination. The smooth, predictable shifts observed under capacity variation ($N$) and adjustment speed variation ($\alpha$) validate the model's calibration choices for the main thesis runs.

