# Calibration Robustness: Revenue and Throughput Decomposition

This report evaluates the operational and financial outcomes of the platform under various fleet sizes and scenario configurations. Specifically, we analyze whether the choice of structural fleet size calibration ($N=80$) influences the economic interpretation of platform dynamics, and whether pricing-enabled coordination becomes more economically meaningful under structural capacity constraints.

## 1. Fleet-Size Revenue and Throughput Decomposition (Interaction Scenario)

The following table shows the metrics computed under varying fleet sizes ($N \in \{40, 50, 60, 80, 100\}$) for the unconstrained Interaction scenario (pricing and rebalancing active, means across 50 seeds, 500 ticks each):

| Fleet Size ($N$) | Service Rate | Overload Freq. | Completed Trips | Total Revenue | Revenue / Vehicle | Rev / Completed Trip | Average Price | Idle Vehicles | Idle Share |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **40** | 70.55% | 44.61% | 6611.9 | $49467.33 | $1236.68 | $7.48 | $10.71 | 4.65 | 11.64% |
| **50** | 76.31% | 29.23% | 7792.7 | $37327.69 | $746.55 | $4.79 | $6.90 | 8.53 | 17.06% |
| **60** | 78.93% | 23.14% | 8299.9 | $31718.30 | $528.64 | $3.82 | $5.46 | 16.16 | 26.93% |
| **80** | 79.38% | 22.54% | 8380.9 | $30806.95 | $385.09 | $3.68 | $5.27 | 35.93 | 44.91% |
| **100** | 79.49% | 22.17% | 8419.8 | $30155.21 | $301.55 | $3.58 | $5.13 | 55.76 | 55.76% |

## 2. Main Scenario Revenue and Throughput Decomposition (N=80 Baseline)

This table presents the decomposition for the five core scenarios evaluated under the thesis calibration baseline ($N=80$, means across 50 seeds, 500 ticks each):

| Scenario | Service Rate | Overload Freq. | Completed Trips | Total Revenue | Revenue / Vehicle | Rev / Completed Trip | Average Price | Idle Vehicles | Idle Share | Mismatch (Imbalance) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Passive** | 60.28% | 65.43% | 4490.8 | $81487.68 | $1018.60 | $18.15 | $17.17 | 59.14 | 73.92% | 0.136 |
| **Pricing Only** | 70.58% | 45.47% | 6987.3 | $38195.51 | $477.44 | $5.47 | $9.30 | 47.45 | 59.31% | 0.111 |
| **Rebalancing Only** | 74.52% | 35.58% | 5080.5 | $90529.92 | $1131.62 | $17.82 | $17.17 | 53.82 | 67.27% | 0.123 |
| **Interaction** | 79.38% | 22.54% | 8380.9 | $30806.95 | $385.09 | $3.68 | $5.27 | 35.93 | 44.91% | 0.089 |
| **Governance** | 75.65% | 31.81% | 7509.3 | $39411.36 | $492.64 | $5.25 | $8.06 | 42.33 | 52.91% | 0.101 |

## 3. Capacity-Regime Scenario Comparison (N=40 and N=60)

To understand how capacity scarcity alters coordination dynamics, we evaluate the baseline scenarios under constrained fleet sizes ($N=40$ and $N=60$):

### Table 3a: Metrics under Capacity Scarcity ($N=40$)

| Scenario | Service Rate | Overload Freq. | Completed Trips | Total Revenue | Revenue / Vehicle | Rev / Completed Trip | Average Price | Idle Vehicles | Idle Share | Mismatch |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Passive** | 54.41% | 76.03% | 4199.2 | $76348.08 | $1908.70 | $18.18 | $17.17 | 20.48 | 51.19% | 0.115 |
| **Pricing Only** | 66.40% | 56.46% | 6356.3 | $44485.82 | $1112.15 | $7.00 | $10.83 | 10.35 | 25.87% | 0.070 |
| **Rebalancing Only** | 70.89% | 42.72% | 4923.5 | $87557.98 | $2188.95 | $17.78 | $17.17 | 13.83 | 34.58% | 0.083 |
| **Interaction** | 70.55% | 44.61% | 6611.9 | $49467.33 | $1236.68 | $7.48 | $10.71 | 4.65 | 11.64% | 0.051 |

### Table 3b: Metrics under Moderate Capacity Constraint ($N=60$)

| Scenario | Service Rate | Overload Freq. | Completed Trips | Total Revenue | Revenue / Vehicle | Rev / Completed Trip | Average Price | Idle Vehicles | Idle Share | Mismatch |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Passive** | 57.90% | 68.71% | 4370.1 | $79425.84 | $1323.76 | $18.17 | $17.17 | 39.66 | 66.10% | 0.128 |
| **Pricing Only** | 70.80% | 44.54% | 6949.2 | $38456.35 | $640.94 | $5.53 | $9.34 | 27.60 | 46.00% | 0.093 |
| **Rebalancing Only** | 73.60% | 37.75% | 5023.3 | $89537.16 | $1492.29 | $17.82 | $17.17 | 33.96 | 56.60% | 0.110 |
| **Interaction** | 78.93% | 23.14% | 8299.9 | $31718.30 | $528.64 | $3.82 | $5.46 | 16.16 | 26.93% | 0.064 |

## 4. Methodological Interpretation

### 4.1 Why Revenue per Vehicle Alone is Insufficient
Evaluating platform performance solely using *Revenue per Vehicle* introduces a substantial mathematical bias. Because the metric has fleet size ($N$) as its denominator, reducing fleet size creates a dramatic, artificial inflator. For instance, under the Interaction scenario, reducing fleet size from $N = 80$ to $N = 40$ increases the Revenue per Vehicle from **$385.09** to **$1236.68**—a **$221.1\%$** increase. However, this surge is not driven by improved platform throughput. In fact, completed trips drop from **8380.9** to **6611.9** (a **$21.1\%$** decrease). Thus, looking only at vehicle-level averages incorrectly implies that a smaller fleet performs better, whereas it actually degrades matching capacity.

### 4.2 Total Revenue Tells a Different Story
Analyzing *Total Revenue* resolves this distortion and reveals the true system-level tradeoffs. Under Interaction, total revenue actually **increases** from **$30,806.95** at $N=80$ to **$49,467.33** at $N=40$, despite the **21.1%** throughput reduction (completed trips dropping from 8380.9 to 6611.9). 

This paradox occurs because under extreme scarcity, the dynamic pricing algorithm triggers aggressive, persistent fare increases (resulting in a **$10.71** average price per tick at $N=40$ compared to **$5.27** at $N=80$). This pricing inflation is so pronounced that total revenue at $N=40$ is **60.6% higher** than at $N=80$. 

However, this higher revenue comes at a massive cost to passenger service: the service rate drops from **79.38%** to **70.55%** and the overload frequency (unmet demand ratio $\ge 30\%$) spikes from **22.54%** to **44.61%**. This shows that total revenue under scarcity behaves as an **exploitation index** of demand inelasticity, rather than a metric of matching efficiency.

### 4.3 Fleet Size and the Economic Meaning of Pricing Coordination
Varying fleet capacity changes the fundamental role and economic benefit of dynamic pricing coordination:
1. **Under Abundance ($N \ge 80$)**: Pricing has minimal matching utility because physical vehicle supply is abundant. Rebalancing and normal fleet density are sufficient to handle spatial imbalances. As a result, adding dynamic pricing (*Interaction* scenario) only yields a marginal improvement in Service Rate over *Rebalancing Only* (**79.38%** vs. **74.52%**), while average prices remain low.
2. **Under Constraint and Scarcity ($N \le 60$)**: In Table 3a ($N=40$), comparing *Rebalancing Only* and *Interaction* shows that while the service rate changes slightly (from **70.89%** to **70.55%**), completed trips rise from **4923.5** to **6611.9** (a **34.3%** increase). This is because the pricing algorithm actively suppresses demand in supply-deficient zones and raises fares, coordinating matching and increasing active vehicle efficiency. Pricing is therefore highly meaningful under capacity scarcity, acting as a crucial demand-rationing and matching coordination mechanism, whereas under capacity abundance it acts primarily as a minor fine-tuning buffer.

### 4.4 Conditionality of Thesis Findings
The main thesis findings—such as the severity of the stability-efficiency trade-off and the selected governance configurations—are **conditional on the chosen structural capacity calibration ($N=80$)**.
If the platform operates in a tighter capacity regime (e.g. $N=40$), dynamic pricing becomes economically indispensable for trip throughput, and any governance mechanisms that damp pricing would carry a much higher operational throughput penalty. Therefore, the thesis should frame its results not as universal laws of platform design, but as **conditional on structural fleet capacity**: structural capacity planning acts as the primary determinant of system stability, and algorithmic governance serves as a secondary fine-tuning overlay whose parameters must be calibrated in tandem with the physical scale of the system.

