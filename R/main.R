###############################################################################
# main.R
# Master script: runs the full bike-lane accessibility analysis.
#
# Usage:
#   Rscript main.R
#
# Output:
#   R/figures/  - PDF figures for the paper
#   R/tables/   - LaTeX table files
#
# Required packages:
#   sf, igraph, dplyr
#
# Install with:
#   install.packages(c("sf", "igraph", "dplyr"))
###############################################################################

# ---- Setup ------------------------------------------------------------------

script_dir <- "/Users/shmuelsan/Dropbox/Apps/GitHub/bike/R"

# Source all module files
source(file.path(script_dir, "01_load_data.R"))
source(file.path(script_dir, "02_build_network.R"))
source(file.path(script_dir, "03_accessibility.R"))
source(file.path(script_dir, "04_lane_rankings.R"))
source(file.path(script_dir, "05_figures.R"))
source(file.path(script_dir, "06_tables.R"))

# Paths
data_dir    <- "/Users/shmuelsan/Dropbox/Apps/GitHub/bike"
figures_dir <- file.path(script_dir, "figures")
tables_dir  <- file.path(script_dir, "tables")
dir.create(figures_dir, showWarnings = FALSE)
dir.create(tables_dir,  showWarnings = FALSE)

# Default parameters
DEFAULT_K     <- 5
DEFAULT_THETA <- -1.0
DEFAULT_YEAR  <- 2025

# Parameter ranges for sensitivity analysis
K_VALUES     <- c(2, 5, 10, 50, 100)
THETA_VALUES <- c(-0.5, -1.0, -1.5, -2.0, -3.0)
YEAR_VALUES  <- c(2020, 2025, 2030, 2035, 2040)


# =============================================================================
# Step 1: Load data
# =============================================================================

message(strrep("=", 60))
message("STEP 1: Loading data")
message(strrep("=", 60))

data <- load_all_data(data_dir)
areas        <- data$areas
roads        <- data$roads
completed    <- data$completed
construction <- data$construction
wishing      <- data$wishing

# Project to Israel TM for distance calculations
areas_proj <- st_transform(areas, TARGET_CRS)
roads_proj <- st_transform(roads, TARGET_CRS)

# Build Hebrew -> English name lookup for wishing-list lanes
build_name_map(wishing)


# =============================================================================
# Step 2: Build road network graph
# =============================================================================

message("\n", strrep("=", 60))
message("STEP 2: Building road network")
message(strrep("=", 60))

network <- build_road_network(roads_proj, areas_proj)
message(sprintf("  Network: %d nodes, %d edges",
                vcount(network$graph), ecount(network$graph)))


# =============================================================================
# Step 3: Mark baseline bike lanes (completed + under construction)
# =============================================================================

message("\n", strrep("=", 60))
message("STEP 3: Marking baseline bike lanes")
message(strrep("=", 60))

baseline_marked <- mark_bike_lane_edges(network, list(completed, construction))
message(sprintf("  Edges with bike lanes: %d / %d", sum(baseline_marked), length(baseline_marked)))


# =============================================================================
# Step 4: Compute baseline accessibility
# =============================================================================

message("\n", strrep("=", 60))
message("STEP 4: Computing baseline accessibility")
message(strrep("=", 60))

G_base <- network$graph
E(G_base)$has_bike_lane <- baseline_marked

baseline <- compute_accessibility(G_base, network$registry, areas_proj,
                                  theta = DEFAULT_THETA, k = DEFAULT_K,
                                  year = DEFAULT_YEAR)
message(sprintf("  Baseline N = %.4e", baseline$total_N))


# =============================================================================
# Step 5: Rank wishing-list lanes
# =============================================================================

message("\n", strrep("=", 60))
message("STEP 5: Ranking wishing-list lanes")
message(strrep("=", 60))

rank_result <- compute_lane_rankings(network, areas_proj, wishing,
                                     baseline_marked, DEFAULT_THETA,
                                     DEFAULT_K, DEFAULT_YEAR)
rankings <- rank_result$rankings

message("\nTop 10 lanes:")
for (i in 1:min(10, nrow(rankings))) {
  message(sprintf("  %2d. %-35s  %+.3f%%", i, rankings$name[i],
                  rankings$improvement_pct[i]))
}


# =============================================================================
# Step 6: Sensitivity analyses
# =============================================================================

message("\n", strrep("=", 60))
message("STEP 6: Sensitivity analyses")
message(strrep("=", 60))

rankings_by_k     <- run_sensitivity_k(network, areas_proj, wishing,
                                        baseline_marked, DEFAULT_THETA, DEFAULT_YEAR,
                                        K_VALUES)

rankings_by_theta <- run_sensitivity_theta(network, areas_proj, wishing,
                                            baseline_marked, DEFAULT_K, DEFAULT_YEAR,
                                            THETA_VALUES)

rankings_by_year  <- run_sensitivity_year(network, areas_proj, wishing,
                                           baseline_marked, DEFAULT_THETA, DEFAULT_K,
                                           YEAR_VALUES)


# =============================================================================
# Step 7: Compute per-lane and cumulative impacts for figures
# =============================================================================

message("\n", strrep("=", 60))
message("STEP 7: Computing lane impacts for figures")
message(strrep("=", 60))

wishing_proj  <- st_transform(wishing, TARGET_CRS)
wishing_wgs84 <- st_transform(wishing, WGS84)

lane_impacts       <- list()   # per-lane impact data for figures
cumulative_impacts <- list()   # cumulative impact data for figure 5
cumulative_marked  <- baseline_marked

for (rank_idx in seq_len(min(5, nrow(rankings)))) {
  target_name <- rankings$name[rank_idx]
  target_raw  <- rankings$name_raw[rank_idx]

  # Find matching lane in wishing list
  match_idx <- NA
  for (wi in seq_len(nrow(wishing_proj))) {
    if (wishing_proj$Name[wi] == target_raw ||
        transliterate(wishing_proj$Name[wi]) == target_name) {
      match_idx <- wi
      break
    }
  }
  if (is.na(match_idx)) next

  message(sprintf("  Computing impact for #%d: %s", rank_idx, target_name))

  # --- Single-lane impact ---
  single_marked <- mark_bike_lane_edges(network, list(wishing_proj[match_idx, ]))
  combined <- baseline_marked | single_marked

  G_with <- network$graph
  E(G_with)$has_bike_lane <- combined
  acc_with <- compute_accessibility(G_with, network$registry, areas_proj,
                                    theta = DEFAULT_THETA, k = DEFAULT_K,
                                    year = DEFAULT_YEAR)

  n_areas <- nrow(areas_proj)
  imp_orig <- numeric(n_areas)
  imp_dest <- numeric(n_areas)
  for (i in seq_len(n_areas)) {
    if (baseline$acc_origin[i] > 0)
      imp_orig[i] <- (acc_with$acc_origin[i] - baseline$acc_origin[i]) /
                      baseline$acc_origin[i] * 100
    if (baseline$acc_dest[i] > 0)
      imp_dest[i] <- (acc_with$acc_dest[i] - baseline$acc_dest[i]) /
                      baseline$acc_dest[i] * 100
  }

  lane_impacts[[rank_idx]] <- list(
    name       = target_name,
    name_raw   = target_raw,
    rank       = rank_idx,
    imp_orig   = imp_orig,
    imp_dest   = imp_dest,
    geom_wgs84 = st_geometry(wishing_wgs84)[[match_idx]]
  )

  # --- Cumulative impact ---
  cumulative_marked <- cumulative_marked | single_marked
  G_cumul <- network$graph
  E(G_cumul)$has_bike_lane <- cumulative_marked
  acc_cumul <- compute_accessibility(G_cumul, network$registry, areas_proj,
                                     theta = DEFAULT_THETA, k = DEFAULT_K,
                                     year = DEFAULT_YEAR)

  cumul_orig <- numeric(n_areas)
  cumul_dest <- numeric(n_areas)
  for (i in seq_len(n_areas)) {
    if (baseline$acc_origin[i] > 0)
      cumul_orig[i] <- (acc_cumul$acc_origin[i] - baseline$acc_origin[i]) /
                        baseline$acc_origin[i] * 100
    if (baseline$acc_dest[i] > 0)
      cumul_dest[i] <- (acc_cumul$acc_dest[i] - baseline$acc_dest[i]) /
                        baseline$acc_dest[i] * 100
  }

  lane_names_so_far <- paste(sapply(lane_impacts, `[[`, "name"), collapse = ", ")

  cumulative_impacts[[rank_idx]] <- list(
    imp_orig   = cumul_orig,
    imp_dest   = cumul_dest,
    lane_names = lane_names_so_far,
    geom_wgs84 = st_geometry(wishing_wgs84)[[match_idx]]
  )
}


# =============================================================================
# Step 8: Generate figures
# =============================================================================

message("\n", strrep("=", 60))
message("STEP 8: Generating figures")
message(strrep("=", 60))

# Figure 1: Baseline accessibility
message("  Figure 1: Baseline accessibility")
generate_figure1(areas, baseline$acc_origin, baseline$acc_dest,
                 file.path(figures_dir, "figure1_baseline_accessibility.pdf"))

# Figure 2: Improvement with top 5 lanes
message("  Figure 2: Top 5 improvement")
top_names <- sapply(lane_impacts, `[[`, "name")
n_ci <- length(cumulative_impacts)
generate_figure2(areas,
                 cumulative_impacts[[n_ci]]$imp_orig,
                 cumulative_impacts[[n_ci]]$imp_dest,
                 top_names,
                 file.path(figures_dir, "figure2_improvement_top5.pdf"))

# Figure 3: Individual lane impacts for top 3
message("  Figure 3: Individual lane impacts")
for (i in seq_len(min(3, length(lane_impacts)))) {
  li <- lane_impacts[[i]]
  fname <- sprintf("figure3_%d_lane_impact_%s.pdf", i,
                   gsub("[^A-Za-z0-9_-]", "_", substr(li$name, 1, 20)))
  generate_figure3(areas, li$name, li$imp_orig, li$imp_dest,
                   li$geom_wgs84,
                   file.path(figures_dir, fname))
}

# Figure 4: Comparison of top 3 lanes
message("  Figure 4: Top lanes comparison")
generate_figure4(areas, lane_impacts[1:min(3, length(lane_impacts))],
                 file.path(figures_dir, "figure4_top_lanes_comparison.pdf"))

# Figure 5: Cumulative impact
message("  Figure 5: Cumulative impact")
generate_figure5(areas, cumulative_impacts,
                 file.path(figures_dir, "figure5_cumulative_impact.pdf"))


# =============================================================================
# Step 9: Generate tables
# =============================================================================

message("\n", strrep("=", 60))
message("STEP 9: Generating LaTeX tables")
message(strrep("=", 60))

write_table(generate_table1_theta(),
            file.path(tables_dir, "table1_theta.tex"))

write_table(generate_table2_k(),
            file.path(tables_dir, "table2_k.tex"))

write_table(generate_table3_data_sources(),
            file.path(tables_dir, "table3_data_sources.tex"))

write_table(generate_table4_wishing_list(wishing),
            file.path(tables_dir, "table4_wishing_list.tex"))

write_table(generate_table5_rankings(rankings),
            file.path(tables_dir, "table5_rankings.tex"))

write_table(generate_table6_sensitivity_k(rankings_by_k, K_VALUES),
            file.path(tables_dir, "table6_sensitivity_k.tex"))

write_table(generate_table7_sensitivity_theta(rankings_by_theta, THETA_VALUES),
            file.path(tables_dir, "table7_sensitivity_theta.tex"))

write_table(generate_table8_temporal(rankings_by_year, YEAR_VALUES),
            file.path(tables_dir, "table8_temporal.tex"))

write_table(generate_table9_phases(rankings),
            file.path(tables_dir, "table9_phases.tex"))

write_table(generate_table10_performance(),
            file.path(tables_dir, "table10_performance.tex"))

write_table(generate_table11_network_stats(network$graph, nrow(areas)),
            file.path(tables_dir, "table11_network_stats.tex"))


# =============================================================================
# Done
# =============================================================================

message("\n", strrep("=", 60))
message("DONE")
message(strrep("=", 60))
message("Figures: ", figures_dir)
message("Tables:  ", tables_dir)
