# analysis_h1_h2.R
# This script performs statistical analysis and generates plots for Hypotheses 1 and 2 of the thesis.

# -------------------------------------------------------------------------
# 1. Setup & Package Loading
# -------------------------------------------------------------------------
cat("Setting up environment...\n")
required_packages <- c("tidyverse")
new_packages <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]
if(length(new_packages)) {
  cat("Installing required packages (this may take a few minutes)...\n")
  install.packages(new_packages, repos="https://cloud.r-project.org")
}

library(tidyverse)

# Create output directories
dir.create("outputs/h1", recursive = TRUE, showWarnings = FALSE)
dir.create("outputs/h2", recursive = TRUE, showWarnings = FALSE)

# -------------------------------------------------------------------------
# 2. Data Loading
# -------------------------------------------------------------------------
cat("Loading data...\n")
data_file <- "outputs/monte_carlo_run_summary.csv"
if (!file.exists(data_file)) {
  stop(paste("Data file not found at:", data_file, ". Please run the simulation campaign first."))
}

df_full <- read_csv(data_file)

# -------------------------------------------------------------------------
# 3. Helper Functions & Config
# -------------------------------------------------------------------------

# Consistent color palette as requested
scenario_colors <- c(
  "passive" = "#1F4E79",
  "pricing_only" = "#D95F8D",
  "rebalancing_only" = "#56B4E9",
  "interaction" = "#8E44AD",
  "governance" = "#4C956C"
)

# Custom function to calculate 95% CI without Hmisc dependency
mean_ci_95 <- function(x) {
  x <- na.omit(x)
  n <- length(x)
  if (n < 2) return(data.frame(y = mean(x), ymin = mean(x), ymax = mean(x)))
  m <- mean(x)
  se <- sd(x) / sqrt(n)
  ci <- 1.96 * se
  data.frame(y = m, ymin = m - ci, ymax = m + ci)
}

# Function to run ANOVA and return F, p, and eta-squared
run_anova <- function(df, metric, scenario_col = "scenario") {
  formula_str <- paste(metric, "~", scenario_col)
  fit <- aov(as.formula(formula_str), data = df)
  sum_fit <- summary(fit)[[1]]
  
  ss_treatment <- sum_fit$`Sum Sq`[1]
  ss_residuals <- sum_fit$`Sum Sq`[2]
  ss_total <- ss_treatment + ss_residuals
  
  f_stat <- sum_fit$`F value`[1]
  p_val <- sum_fit$`Pr(>F)`[1]
  eta_sq <- ss_treatment / ss_total
  
  return(data.frame(
    Metric = metric,
    F_statistic = f_stat,
    p_value = p_val,
    eta_squared = eta_sq,
    stringsAsFactors = FALSE
  ))
}

# Function to run Tukey HSD and return a clean data frame
run_tukey <- function(df, metric, scenario_col = "scenario") {
  formula_str <- paste(metric, "~", scenario_col)
  fit <- aov(as.formula(formula_str), data = df)
  tukey_res <- TukeyHSD(fit)
  
  tukey_df <- as.data.frame(tukey_res[[scenario_col]])
  tukey_df$Comparison <- rownames(tukey_df)
  tukey_df$Metric <- metric
  
  # Rename columns to match requested format
  tukey_df <- tukey_df %>%
    rename(
      Mean_Difference = diff,
      Adjusted_p_value = `p adj`
    ) %>%
    select(Metric, Comparison, Mean_Difference, Adjusted_p_value)
  
  return(tukey_df)
}

# Function to calculate scenario summary statistics (Mean, SD, N, and CI bounds)
get_summary_stats <- function(df, metric, scenario_col = "scenario") {
  df %>%
    group_by(!!sym(scenario_col)) %>%
    summarize(
      Mean = mean(!!sym(metric), na.rm = TRUE),
      SD = sd(!!sym(metric), na.rm = TRUE),
      N = n(),
      .groups = "drop"
    ) %>%
    mutate(
      SE = SD / sqrt(N),
      CI_Lower = Mean - 1.96 * SE,
      CI_Upper = Mean + 1.96 * SE
    ) %>%
    select(Scenario = !!sym(scenario_col), Mean, SD, CI_Lower, CI_Upper, N)
}

# Function to generate and export academic boxplot + mean + 95% CI
generate_plot <- function(df, metric, metric_label, output_path, colors) {
  # Calculate summary stats for mean and 95% CI of the mean
  summary_df <- df %>%
    group_by(scenario) %>%
    summarize(
      Mean = mean(!!sym(metric), na.rm = TRUE),
      SD = sd(!!sym(metric), na.rm = TRUE),
      N = n(),
      SE = SD / sqrt(N),
      ci_lwr = Mean - 1.96 * SE,
      ci_upr = Mean + 1.96 * SE,
      .groups = "drop"
    )
  
  p <- ggplot(df, aes(x = scenario, y = !!sym(metric), fill = scenario)) +
    # Boxplot
    geom_boxplot(alpha = 0.5, outlier.shape = NA, width = 0.4, color = "black", linewidth = 0.6) +
    # Individual jitter points
    geom_jitter(width = 0.15, height = 0, alpha = 0.4, size = 1.2, aes(color = scenario)) +
    # Mean points as black diamonds (shape 18)
    geom_point(data = summary_df, aes(x = scenario, y = Mean), shape = 18, size = 4, color = "black") +
    # 95% CI error bars
    geom_errorbar(data = summary_df, aes(x = scenario, y = Mean, ymin = ci_lwr, ymax = ci_upr), width = 0.12, color = "black", linewidth = 0.8) +
    # Colors and theme
    scale_fill_manual(values = colors) +
    scale_color_manual(values = colors) +
    theme_minimal(base_family = "sans") +
    labs(
      x = "Scenario",
      y = metric_label
    ) +
    theme(
      legend.position = "none",
      plot.title = element_blank(), # Keep title blank for journal-style insertion in LaTeX
      axis.title = element_text(face = "bold", size = 11),
      axis.text = element_text(size = 10, color = "black"),
      panel.grid.major = element_line(color = "grey93", linewidth = 0.5),
      panel.grid.minor = element_blank()
    )
  
  # Save the plot
  ggsave(
    filename = output_path,
    plot = p,
    width = 8,
    height = 5,
    dpi = 300
  )
}

# -------------------------------------------------------------------------
# 4. Hypothesis 1: Individual Mechanism Hypothesis
# -------------------------------------------------------------------------
cat("\nAnalyzing Hypothesis 1...\n")

h1_scenarios <- c("passive", "pricing_only", "rebalancing_only")
df_h1 <- df_full %>% 
  filter(scenario %in% h1_scenarios) %>%
  mutate(scenario = factor(scenario, levels = h1_scenarios))

h1_metrics <- c(
  "revenue_per_vehicle" = "Revenue per Vehicle ($)",
  "fleet_utilization" = "Fleet Utilization",
  "service_rate" = "Service Rate",
  "demand_supply_mismatch" = "Demand-Supply Mismatch Index",
  "vehicle_concentration" = "Vehicle Concentration"
)

h1_anova_list <- list()
h1_tukey_list <- list()

for (metric in names(h1_metrics)) {
  if (!(metric %in% colnames(df_h1))) {
    warning(paste("Metric", metric, "is missing from the dataset. Skipping H1 analysis for it."))
    next
  }
  
  metric_label <- h1_metrics[[metric]]
  cat(paste("  Processing metric:", metric, "...\n"))
  
  # A. Summary stats
  sum_stats <- get_summary_stats(df_h1, metric)
  write_csv(sum_stats, paste0("outputs/h1/h1_", metric, "_summary.csv"))
  
  # B. ANOVA
  anova_res <- run_anova(df_h1, metric)
  h1_anova_list[[metric]] <- anova_res
  
  # C. Tukey HSD
  tukey_res <- run_tukey(df_h1, metric)
  h1_tukey_list[[metric]] <- tukey_res
  
  # D. Plot
  plot_path <- paste0("outputs/h1/h1_", metric, "_plot.png")
  generate_plot(df_h1, metric, metric_label, plot_path, scenario_colors)
}

# Combine and export summaries
if (length(h1_anova_list) > 0) {
  h1_anova_summary <- bind_rows(h1_anova_list)
  h1_tukey_summary <- bind_rows(h1_tukey_list)
  write_csv(h1_anova_summary, "outputs/h1/h1_anova_summary.csv")
  write_csv(h1_tukey_summary, "outputs/h1/h1_tukey_summary.csv")
}

# -------------------------------------------------------------------------
# 5. Hypothesis 2: Interaction Hypothesis
# -------------------------------------------------------------------------
cat("\nAnalyzing Hypothesis 2...\n")

h2_scenarios <- c("pricing_only", "rebalancing_only", "interaction")
df_h2 <- df_full %>% 
  filter(scenario %in% h2_scenarios) %>%
  mutate(scenario = factor(scenario, levels = h2_scenarios))

h2_metrics <- c(
  "price_volatility" = "Price Volatility (SD of Prices)",
  "oscillation_index" = "Price Oscillation Index",
  "overload_frequency" = "Overload Frequency (Service Rate <= 70%)",
  "persistence_demand_supply_mismatch" = "Persistence of Demand-Supply Mismatch (>0.15)",
  "demand_supply_mismatch" = "Demand-Supply Mismatch Index",
  "vehicle_concentration" = "Vehicle Concentration",
  "revenue_per_vehicle" = "Revenue per Vehicle ($)"
)

h2_anova_list <- list()
h2_tukey_list <- list()

for (metric in names(h2_metrics)) {
  if (!(metric %in% colnames(df_h2))) {
    warning(paste("Metric", metric, "is missing from the dataset. Skipping H2 analysis for it."))
    next
  }
  
  metric_label <- h2_metrics[[metric]]
  cat(paste("  Processing metric:", metric, "...\n"))
  
  # A. Summary stats
  sum_stats <- get_summary_stats(df_h2, metric)
  write_csv(sum_stats, paste0("outputs/h2/h2_", metric, "_summary.csv"))
  
  # B. ANOVA
  anova_res <- run_anova(df_h2, metric)
  h2_anova_list[[metric]] <- anova_res
  
  # C. Tukey HSD
  tukey_res <- run_tukey(df_h2, metric)
  h2_tukey_list[[metric]] <- tukey_res
  
  # D. Plot
  plot_path <- paste0("outputs/h2/h2_", metric, "_plot.png")
  generate_plot(df_h2, metric, metric_label, plot_path, scenario_colors)
}

# Combine and export summaries
if (length(h2_anova_list) > 0) {
  h2_anova_summary <- bind_rows(h2_anova_list)
  h2_tukey_summary <- bind_rows(h2_tukey_list)
  write_csv(h2_anova_summary, "outputs/h2/h2_anova_summary.csv")
  write_csv(h2_tukey_summary, "outputs/h2/h2_tukey_summary.csv")
}

cat("\nAnalysis for H1 and H2 completed successfully!\n")
cat("All CSV tables and PNG figures are exported to 'outputs/h1/' and 'outputs/h2/'.\n")
