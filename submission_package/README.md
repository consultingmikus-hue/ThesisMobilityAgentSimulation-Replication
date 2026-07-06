# Submission Package

This directory provides a convenient collection of the key supplementary materials accompanying the thesis.
> **Governing Interacting Autonomous Algorithmic Decision Mechanisms in Digital Platforms: A Simulation Study of System Stability**

Contents:

- Data_and_Reports/
  - Final aggregated datasets
  - Zipped results package
  - Rendered analysis reports
  - Corresponding Quarto source files
    
This package contains the datasets, analysis reports, and supporting scripts required to reproduce the quantitative results presented in the thesis.
The complete replication repository, including the simulation source code, experiment scripts, datasets, dashboard, documentation, and supporting files, is available throughout the repository.

## Contents

### Main Simulation Results

- `monte_carlo_run_summary.csv`
- `monte_carlo_scenario_config.json`

### Calibration

- `alpha_fleet_calibration_summary.csv`

### Pricing Diagnostics

- `revenue_decomposition_fleet_size.csv`
- `revenue_decomposition_main_scenarios.csv`
- `pricing_gaps_by_zone.csv`
- `spatial_flow_decomposed.csv`
- `calibration_alpha_robustness.csv`
- `capacity_regime_scenario_comparison.csv`

### Adaptive Governance

- `adaptive_stress_test_results.csv`
- `adaptive_governance_parameter_robustness.csv`
- `final_thresholds.json`

### Analysis Reports

- `analysis_report.qmd` / `.html`
- `pricing_calibration_diagnostics.qmd` / `.html`
- `adaptive_governance_extension.qmd` / `.html`

## Figure Generation

Most statistical analyses, summary tables, and supporting outputs are reproduced from the aggregated Monte Carlo dataset (`monte_carlo_run_summary.csv`) using `analysis_report.qmd`.

Several publication-quality figures are generated separately using dedicated R scripts:

| Figure | Script | Data Source |
|--------|--------|-------------|
| Figure 6.1 | `create_main_results_figures.R` | Monte Carlo summary results |
| Figure 6.2 | `create_main_results_figures.R` | Monte Carlo summary results |
| Figure 6.3 | `refine_figure3.R` | Monte Carlo summary results |
| Figure 6.4 | `refine_figure4.R` | Deterministic simulation run |
| Figure 8.1 | `refine_adaptive_governance_timeseries.R` | Deterministic simulation run |

Figures 6.4 and 8.1 are generated from deterministic single simulation runs executed directly through the simulation model rather than from aggregated Monte Carlo outputs. The corresponding R scripts are included in the repository to ensure full reproducibility of all figures presented in the thesis.

## Notes

The HTML reports contain the rendered statistical analyses. The corresponding Quarto (`.qmd`) files contain the analysis code used to generate these reports.

This package includes the final datasets and analysis materials supporting the thesis results. Development utilities, intermediate files, exploratory analyses, and experimental outputs are intentionally excluded.

**Interactive Dashboard**

https://thesismobilityagentsimulation-rbnnmpend6ksbtpczfkxjp.streamlit.app/

The interactive Streamlit dashboard allows readers to explore the simulation model, compare scenarios, modify simulation parameters, and visualize the resulting platform dynamics directly in a web browser without local installation.
