# Governing Interacting Autonomous Algorithmic Decision Mechanisms in Digital Platforms: A Simulation Study of System Stability

This repository accompanies the master's thesis:

**Governing Interacting Autonomous Algorithmic Decision Mechanisms in Digital Platforms: A Simulation Study of System Stability**

**Author:** Christian Mikus  
**Programme:** Master in Data Analytics for Economics and Management  
**Faculty:** Faculty of Economics and Management, Free University of Bozen-Bolzano  
**Supervisor:** Prof. Roberto Gabriele  
**Year:** 2026

---

# Overview

This repository contains the complete simulation framework, experimental scripts, analysis reports, and supporting material used throughout the thesis.

The project implements an agent-based simulation (ABM) of a ride-hailing platform to investigate how interacting autonomous decision mechanisms—including pricing, forecasting, rebalancing, and governance—influence system stability, operational performance, and spatial dynamics.

The repository enables full reproduction of the reported simulation results and provides an interactive dashboard for exploring the model under different scenarios.

---

# Repository Structure

```text
src/                           Core simulation model and Streamlit dashboard
experiments/                   Final experiment scripts
experiments/exploratory/       Exploratory development experiments
plots/                         R scripts for thesis figures
outputs/                       Simulation outputs
outputs/exploratory/           Exploratory outputs

analysis_report.qmd
pricing_calibration_diagnostics.qmd
adaptive_governance_extension.qmd
appendix.qmd

ASSUMPTIONS.md
MODEL_SPEC.md
requirements.txt
README.md
```

---

# Interactive Dashboard

An interactive Streamlit dashboard accompanies the thesis, allowing readers to explore the simulation model, compare scenarios, and visualize the resulting system dynamics.

**Hosted dashboard**

https://thesismobilityagentsimulation-rbnnmpend6ksbtpczfkxjp.streamlit.app/

The hosted version can be accessed directly through a web browser without any local installation.

**Run locally**

```bash
cd ThesisMobilityAgentSimulation-Replication
source .venv/bin/activate
python -m streamlit run src/ui/dashboard.py
```

---

# Requirements

- Python 3.10 or later (developed and tested under Python 3.14.5)
- R 4.0 or later
- Quarto 1.4 or later

Python dependencies are listed in `requirements.txt`.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/consultingmikus-hue/ThesisMobilityAgentSimulation-Replication.git
cd ThesisMobilityAgentSimulation-Replication
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Run a quick simulation:

```bash
python -m src.run

```

Run the unit tests:

```bash
python -m unittest src.test_simulation

```

Launch the interactive dashboard:

```bash
python -m streamlit run src/ui/dashboard.py

```
---

# Reproducing the Results
## Main Monte Carlo experiments
```bash
python -m experiments.run_monte_carlo

```
## Calibration analyses
```bash
python -m experiments.run_calibration_robustness

```
## Revenue and pricing diagnostics
```bash
python -m experiments.run_revenue_decomposition

```
## Adaptive governance stress tests
```bash
python -m experiments.run_adaptive_stress_test

```

---

# Generating Thesis Figures
```bash
Rscript plots/create_main_results_figures.R
Rscript plots/refine_figure3.R
Rscript plots/refine_figure4.R
Rscript plots/refine_adaptive_governance_timeseries.R
```
---

# Rendering the Analysis Reports
```bash
quarto render analysis_report.qmd
quarto render pricing_calibration_diagnostics.qmd
quarto render adaptive_governance_extension.qmd
```
---

# Reproducibility

The simulation framework uses Python multiprocessing to execute simulations in parallel. On a modern multi-core computer, the complete simulation suite can typically be regenerated within a few minutes. Precomputed datasets are included for immediate reproduction of the reported results.

All experiments use fixed random seeds and predefined scenario configurations to ensure reproducibility.

---

# Exploratory Material

The following folders contain exploratory analyses and intermediate experiments performed during model development:

- `experiments/exploratory/`
- `outputs/exploratory/`

These materials are included for completeness but are **not required** to reproduce the final results reported in the thesis.

---

# Citation

If you use this repository for academic purposes, please cite:

> Mikus, C. (2026). *Governing Interacting Autonomous Algorithmic Decision Mechanisms in Digital Platforms: A Simulation Study of System Stability*. Master's Thesis, Free University of Bozen-Bolzano.

---

# License

This repository accompanies a master's thesis and is provided for academic review, research, and reproducibility purposes. Unless otherwise stated, all rights remain with the author.

---

# Contact

**Christian Mikus**

GitHub Repository: https://github.com/consultingmikus-hue/ThesisMobilityAgentSimulation-Replication

Email: christian.mikus@gmail.com
