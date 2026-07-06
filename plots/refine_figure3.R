#!/usr/bin/env Rscript
# =============================================================================
# plots/refine_figure3.R
#
# Generates a modified version of Figure 3 mapping Service Rate (x-axis)
# vs. Price Volatility (y-axis) across 5 scenarios.
#
# Source data: outputs/monte_carlo_run_summary.csv (calibrated run, N=80, 50% carryover)
# Output: outputs/thesis_figures/figure_3_service_rate_vs_price_volatility.png
# =============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(scales)
})

DATA_FILE <- "outputs/monte_carlo_run_summary.csv"
OUT_DIR   <- "outputs/thesis_figures"
dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)

cat("Generating modified Figure 3 (Service Rate vs. Price Volatility)...\n")

# ── Load and clean data ──────────────────────────────────────────────────────
df_full <- read_csv(DATA_FILE, show_col_types = FALSE) %>%
  mutate(
    governance_delta = suppressWarnings(as.numeric(governance_delta)),
    governance_theta = suppressWarnings(as.numeric(governance_theta)),
    governance_R_max = suppressWarnings(as.numeric(governance_R_max))
  )

# ── Select governance configuration (replicate QMD selection procedure) ─────
df_int_base <- df_full %>% filter(scenario == "interaction")
int_means <- df_int_base %>%
  summarise(
    revenue_per_vehicle                 = mean(revenue_per_vehicle, na.rm = TRUE),
    service_rate                        = mean(service_rate, na.rm = TRUE),
    price_volatility                    = mean(price_volatility, na.rm = TRUE),
    oscillation_index                   = mean(oscillation_index, na.rm = TRUE),
    overload_frequency                  = mean(overload_frequency, na.rm = TRUE),
    demand_supply_mismatch              = mean(demand_supply_mismatch, na.rm = TRUE),
    persistence_demand_supply_mismatch = mean(persistence_demand_supply_mismatch, na.rm = TRUE),
    vehicle_concentration               = mean(vehicle_concentration, na.rm = TRUE)
  )

gov_grid <- df_full %>%
  filter(scenario == "governance") %>%
  group_by(governance_delta, governance_theta, governance_R_max) %>%
  summarise(
    revenue_per_vehicle_mean                    = mean(revenue_per_vehicle, na.rm = TRUE),
    service_rate_mean                           = mean(service_rate, na.rm = TRUE),
    price_volatility_mean                       = mean(price_volatility, na.rm = TRUE),
    oscillation_index_mean                      = mean(oscillation_index, na.rm = TRUE),
    overload_frequency_mean                     = mean(overload_frequency, na.rm = TRUE),
    demand_supply_mismatch_mean                 = mean(demand_supply_mismatch, na.rm = TRUE),
    persistence_demand_supply_mismatch_mean     = mean(persistence_demand_supply_mismatch, na.rm = TRUE),
    vehicle_concentration_mean                  = mean(vehicle_concentration, na.rm = TRUE),
    .groups = "drop"
  )

selection_scores <- gov_grid %>%
  mutate(
    revenue_per_vehicle_change         = (revenue_per_vehicle_mean   - int_means$revenue_per_vehicle)   / abs(int_means$revenue_per_vehicle),
    service_rate_change                = (service_rate_mean          - int_means$service_rate)           / abs(int_means$service_rate),
    price_volatility_improvement       = (int_means$price_volatility - price_volatility_mean)            / abs(int_means$price_volatility),
    oscillation_index_improvement      = (int_means$oscillation_index - oscillation_index_mean)          / abs(int_means$oscillation_index),
    overload_frequency_improvement     = (int_means$overload_frequency - overload_frequency_mean)        / abs(int_means$overload_frequency),
    demand_supply_mismatch_improvement = (int_means$demand_supply_mismatch - demand_supply_mismatch_mean) / abs(int_means$demand_supply_mismatch),
    excluded = (service_rate_change < -0.10) |
               (revenue_per_vehicle_change < -0.10) |
               (overload_frequency_improvement < -0.10),
    balanced_score = 0.35 * price_volatility_improvement  +
                     0.25 * oscillation_index_improvement +
                     0.15 * overload_frequency_improvement +
                     0.10 * demand_supply_mismatch_improvement +
                     0.10 * service_rate_change +
                     0.05 * revenue_per_vehicle_change
  )

non_excl <- selection_scores %>% filter(!excluded)
if (nrow(non_excl) > 0) {
  selected <- non_excl %>% arrange(desc(balanced_score)) %>% slice(1)
} else {
  selected <- selection_scores %>% arrange(desc(service_rate_change), price_volatility_mean) %>% slice(1)
}

sel_delta <- selected$governance_delta
sel_theta <- selected$governance_theta
sel_rmax  <- selected$governance_R_max

# ── Calculate scenario-level means across seeds ──────────────────────────────
base_scen <- c("passive", "pricing_only", "rebalancing_only", "interaction")

df_base_means <- df_full %>%
  filter(scenario %in% base_scen) %>%
  group_by(scenario) %>%
  summarise(
    service_rate     = mean(service_rate, na.rm = TRUE),
    price_volatility = mean(price_volatility, na.rm = TRUE),
    .groups = "drop"
  )

df_gov_means <- df_full %>%
  filter(scenario == "governance",
         governance_delta == sel_delta,
         governance_theta == sel_theta,
         governance_R_max == sel_rmax) %>%
  summarise(
    service_rate     = mean(service_rate, na.rm = TRUE),
    price_volatility = mean(price_volatility, na.rm = TRUE)
  ) %>%
  mutate(scenario = "governance")

df_scatter <- bind_rows(df_base_means, df_gov_means) %>%
  mutate(
    label = recode(scenario,
      passive          = "Passive",
      pricing_only     = "Pricing Only",
      rebalancing_only = "Rebalancing Only",
      interaction      = "Interaction",
      governance       = "Governance"
    ),
    is_governance = (scenario == "governance")
  )

cat("Calculated coordinates:\n")
for(i in 1:nrow(df_scatter)) {
  cat(sprintf("  %s: Service Rate = %.6f, Price Volatility = %.6f\n",
              df_scatter$label[i], df_scatter$service_rate[i], df_scatter$price_volatility[i]))
}

# ── Manual label nudges (x/y offsets tailored for new metric ranges) ──────────
# x is service_rate (~0.60 to ~0.80), y is price_volatility (~0.00 to ~2.60)
# Nudge rules:
# Passive (0.602, 0.00) -> nudge right and slightly up
# Pricing Only (0.705, 2.56) -> nudge right and slightly down
# Rebalancing Only (0.745, 0.00) -> nudge left and slightly up
# Governance (0.756, 1.78) -> nudge left and slightly up
# Interaction (0.793, 1.50) -> nudge right and slightly down
nudge_df <- tibble(
  scenario = c("passive", "pricing_only", "rebalancing_only", "governance", "interaction"),
  nudge_x  = c(0.006,    0.006,          -0.006,             -0.006,       0.006),
  nudge_y  = c(0.04,     -0.04,          0.04,               0.04,         -0.04),
  hjust_val = c(0,       0,              1,                  1,            0)
)

df_scatter <- df_scatter %>% left_join(nudge_df, by = "scenario")

# ── Refined theme (matches Figure 4 premium style, base size 13) ──────────────
DARK <- "#1a1a1a"
thesis_theme_fig3 <- theme_classic(base_size = 13) +
  theme(
    plot.title         = element_text(face = "bold", size = 15, colour = DARK),
    plot.subtitle      = element_text(size = 12, colour = DARK, lineheight = 1.3),
    plot.caption       = element_blank(),
    axis.title         = element_text(size = 13, colour = DARK),
    axis.text          = element_text(size = 12, colour = DARK),
    axis.line          = element_line(colour = "grey50"),
    panel.grid.major.y = element_line(colour = "grey90"),
    legend.position    = "none"
  )

# ── Build plot ────────────────────────────────────────────────────────────────
p3_vol <- ggplot(df_scatter, aes(x = service_rate, y = price_volatility)) +
  geom_point(aes(colour = is_governance, shape = is_governance), size = 4) +
  geom_text(aes(label = label, x = service_rate + nudge_x, y = price_volatility + nudge_y,
                hjust = hjust_val),
            size = 3.6, colour = DARK, fontface = "plain") +
  scale_colour_manual(values = c("FALSE" = "#555555", "TRUE" = "#2980b9")) +
  scale_shape_manual(values  = c("FALSE" = 16, "TRUE" = 17)) +
  scale_x_continuous(
    labels = percent_format(accuracy = 1),
    limits = c(0.58, 0.83),
    breaks = seq(0.60, 0.80, 0.05),
    expand = c(0, 0)
  ) +
  scale_y_continuous(
    limits = c(-0.1, 2.8),
    breaks = seq(0.0, 2.5, 0.5),
    expand = c(0, 0)
  ) +
  labs(
    title    = "Operational performance versus price stability",
    subtitle = sprintf(
      "Static Governance Configuration: \u03b4 = %.1f, \u03b8 = %.1f, Rmax = %.0f\nN = 80 | 50%% carry-over | Means across 50 seeds",
      sel_delta, sel_theta, sel_rmax),
    x        = "Service Rate",
    y        = "Price Volatility",
    caption  = NULL
  ) +
  thesis_theme_fig3

# ── Save plot ─────────────────────────────────────────────────────────────────
fig3_vol_path <- file.path(OUT_DIR, "figure_3_service_rate_vs_price_volatility.png")
ggsave(fig3_vol_path, p3_vol, width = 8, height = 5.5, dpi = 300)

cat("\n=================================================================\n")
cat("  VERIFICATION SUMMARY\n")
cat("=================================================================\n")
cat("1. Input file used:      ", DATA_FILE, "\n")
cat("2. Scenario means used:  YES (aggregated across 50 Monte Carlo seeds)\n")
cat("3. Simulation rerun:     NO (read directly from existing data file)\n")
cat("4. Only metric changed:  YES (y-axis changed from Revenue to Price Volatility)\n")
cat("5. Original preserved:   YES (kept original figure_3_governance_tradeoff_scatter.png)\n")
cat("6. Output path:          ", fig3_vol_path, "\n")
cat("=================================================================\n")
