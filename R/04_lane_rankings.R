###############################################################################
# 04_lane_rankings.R
# Rank wishing-list bike lanes by accessibility improvement.
# Also run sensitivity analyses over K, theta, and year.
###############################################################################

# Hebrew -> English transliteration for lane names
LANE_NAMES <- c(
  "\u05d4\u05d0\u05e8\u05f4\u05d9-\u05de\u05d8\u05d5\u05d3\u05dc\u05d4"                     = "HaAri-Metudela",
  "\u05d0\u05d2\u05e8\u05d5\u05df-\u05e8\u05de\u05d1\u05f4\u05df\u200e"                        = "Agron-Ramban",
  "\u05e7\u05e8\u05df \u05d4\u05d9\u05e1\u05d5\u05d3-\u05e7\u05d9\u05e0\u05d2 \u05d2\u05f3\u05d5\u05e8\u05d2\u05f3"  = "Keren HaYesod-King George",
  "\u05d3\u05e8\u05da \u05d7\u05d1\u05e8\u05d5\u05df"                                           = "Derech Hebron",
  "\u05d6\u05f3\u05d1\u05d5\u05d8\u05d9\u05e0\u05e1\u05e7\u05d9"                               = "Jabotinsky",
  "\u05d2\u05f3\u05d5\u05e8\u05d2\u05f3 \u05d0\u05d3\u05dd \u05e1\u05de\u05d9\u05ea\u05f3 - \u05dc\u05d7\u05f4\u05d9\u200e\u200e" = "George Adam Smith-Lehi",
  "\u05d4\u05e8\u05e6\u05dc\u200e"                                                               = "Herzl",
  "\u05d1\u05df \u05d6\u05db\u05d0\u05d9-\u05d9\u05d4\u05d5\u05d3\u05d4 \u05d4\u05e0\u05e9\u05d9\u05d0" = "Ben Zakai-Yehuda HaNasi",
  "\u05e8\u05d7\u05dc \u05d0\u05de\u05e0\u05d5-\u05d7\u05d6\u05e7\u05d9\u05d4\u05d5 \u05d4\u05de\u05dc\u05da-\u05d3\u05d5\u05e1\u05d8\u05d0\u05d9" = "Rachel Imenu-Hizkiyahu",
  "\u05d1\u05e8 \u05dc\u05d1"                                                                     = "Bar Lev",
  "\u05e6\u05d1\u05d9 \u05d9\u05d4\u05d5\u05d3\u05d4"                                           = "Tzvi Yehuda",
  "\u05d4\u05d1\u05e8\u05d5\u05df \u05d4\u05d9\u05e8\u05e9-\u05d0\u05dc\u05d9\u05e2\u05d6\u05e8 \u05d4\u05dc\u05d5\u05d9" = "Baron Hirsch-Eliezer HaLevi",
  "\u05d0\u05dc\u05e2\u05d6\u05e8 \u05d4\u05de\u05d5\u05d3\u05e2\u05d9-\u05db\u05d5\u05d1\u05e9\u05d9 \u05e7\u05d8\u05de\u05d5\u05df" = "Elazar HaModa'i-Katamon",
  "\u05d4\u05e4\u05dc\u05de\u05f4\u05d7"                                                         = "HaPalmach",
  "\u05d1\u05d6\u05e7-\u05d1\u05d9\u05d9\u05d8"                                                 = "Bezek-Beit",
  "\u05d9\u05e8\u05de\u05d9\u05d4\u05d5-\u05d1\u05e8 \u05d0\u05d9\u05dc\u05df-\u05dc\u05d5\u05d9 \u05d0\u05e9\u05db\u05d5\u05dc" = "Yirmiyahu-Bar Ilan-Eshkol",
  "\u05d2\u05d5\u05dc\u05d3\u05d4-\u05e9\u05de\u05d5\u05d0\u05dc \u05d4\u05e0\u05d1\u05d9\u05d0" = "Golda-Shmuel HaNavi",
  "\u05e9\u05d8\u05e8\u05d0\u05d5\u05e1-\u05d9\u05d7\u05d6\u05e7\u05d0\u05dc"                 = "Strauss-Yehezkel",
  "\u05d1\u05d2\u05d9\u05df (\u05d2\u05d1\u05e2\u05ea \u05e8\u05dd)"                           = "Begin (Givat Ram)",
  "\u05d2\u05d5\u05dc\u05d5\u05de\u05d1"                                                         = "Golomb",
  "\u05e7\u05d5\u05dc\u05d9\u05e5"                                                               = "Kolitz",
  "\u05e4\u05d9\u05d9\u05e8 \u05e7\u05e0\u05d9\u05d2"                                           = "Pierre Koenig",
  "\u05e9\u05de\u05d2\u05e8-\u05d0\u05d5\u05d4\u05dc \u05d9\u05d4\u05d5\u05e9\u05d5\u05e2-\u05e9\u05e4\u05e2 \u05d7\u05d9\u05d9\u05dd" = "Shamgar-Ohel Yehoshua",
  "\u05d1\u05e6\u05dc\u05d0\u05dc-\u05e8\u05d1\u05d9\u05df"                                     = "Bezalel-Rabin"
)

transliterate <- function(name) {
  if (name %in% names(LANE_NAMES)) return(LANE_NAMES[[name]])
  name
}


compute_lane_rankings <- function(network, areas_proj, wishing,
                                  baseline_marked, theta, k, year = 2025) {
  # For each wishing-list lane, compute the accessibility improvement
  # when that lane is added to the baseline network.
  #
  # Args:
  #   network         : list from build_road_network()
  #   areas_proj      : sf data frame in projected CRS

  #   wishing         : sf data frame of wishing-list lanes (WGS84)
  #   baseline_marked : logical vector of edge indices with bike lanes
  #   theta, k, year  : model parameters
  #
  # Returns: data.frame sorted by improvement (descending)

  message(sprintf("  Rankings for K=%g, theta=%g, year=%d...", k, theta, year))

  G_base <- network$graph
  E(G_base)$has_bike_lane <- baseline_marked

  # Baseline N
  base <- compute_accessibility(G_base, network$registry, areas_proj,
                                theta = theta, k = k, year = year)
  baseline_N <- base$total_N

  # Evaluate each wishing-list lane
  wishing_proj <- st_transform(wishing, TARGET_CRS)
  n_lanes <- nrow(wishing_proj)

  results <- data.frame(
    name           = character(n_lanes),
    name_raw       = character(n_lanes),
    length_m       = numeric(n_lanes),
    improvement_pct = numeric(n_lanes),
    stringsAsFactors = FALSE
  )

  for (idx in seq_len(n_lanes)) {
    name_raw <- wishing_proj$Name[idx]
    name_en  <- transliterate(name_raw)
    geom     <- st_geometry(wishing_proj)[[idx]]
    lane_len <- as.numeric(st_length(st_sfc(geom, crs = TARGET_CRS)))

    # Mark edges for this single lane
    single_layer <- wishing_proj[idx, ]
    lane_marked <- mark_bike_lane_edges(network, list(single_layer))

    # Combine baseline + this lane
    combined <- baseline_marked | lane_marked
    G_with <- network$graph
    E(G_with)$has_bike_lane <- combined

    acc <- compute_accessibility(G_with, network$registry, areas_proj,
                                 theta = theta, k = k, year = year)
    improvement <- acc$total_N - baseline_N
    improvement_pct <- if (baseline_N > 0) improvement / baseline_N * 100 else 0

    results$name[idx]            <- name_en
    results$name_raw[idx]        <- name_raw
    results$length_m[idx]        <- lane_len
    results$improvement_pct[idx] <- improvement_pct

    message(sprintf("    %2d/%d  %-35s  %+.3f%%", idx, n_lanes, name_en, improvement_pct))
  }

  # Sort by improvement (descending)
  results <- results[order(-results$improvement_pct), ]
  results$rank <- seq_len(nrow(results))
  results$cumulative_pct <- cumsum(results$improvement_pct)
  rownames(results) <- NULL

  list(rankings = results, baseline_N = baseline_N)
}


run_sensitivity_k <- function(network, areas_proj, wishing,
                              baseline_marked, theta, year,
                              k_values = c(2, 5, 10, 50, 100)) {
  # Run rankings for multiple K values. Returns named list of data frames.
  message("Sensitivity analysis: K values")
  result <- list()
  for (k in k_values) {
    out <- compute_lane_rankings(network, areas_proj, wishing,
                                 baseline_marked, theta, k, year)
    result[[as.character(k)]] <- out$rankings
  }
  result
}


run_sensitivity_theta <- function(network, areas_proj, wishing,
                                  baseline_marked, k, year,
                                  theta_values = c(-0.5, -1.0, -1.5, -2.0, -3.0)) {
  # Run rankings for multiple theta values.
  message("Sensitivity analysis: theta values")
  result <- list()
  for (theta in theta_values) {
    out <- compute_lane_rankings(network, areas_proj, wishing,
                                 baseline_marked, theta, k, year)
    result[[as.character(theta)]] <- out$rankings
  }
  result
}


run_sensitivity_year <- function(network, areas_proj, wishing,
                                 baseline_marked, theta, k,
                                 years = c(2020, 2025, 2030, 2035, 2040)) {
  # Run rankings for multiple projection years.
  message("Temporal analysis: projection years")
  result <- list()
  for (yr in years) {
    out <- compute_lane_rankings(network, areas_proj, wishing,
                                 baseline_marked, theta, k, yr)
    result[[as.character(yr)]] <- out$rankings
  }
  result
}
