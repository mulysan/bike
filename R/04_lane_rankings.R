###############################################################################
# 04_lane_rankings.R
# Rank wishing-list bike lanes by accessibility improvement.
# Also run sensitivity analyses over K, theta, and year.
###############################################################################

# English lane names, indexed by position in the wishing list KML (1-28)
# This avoids encoding issues with Hebrew characters
LANE_NAMES_BY_INDEX <- c(
   "HaAri-Metudela",               #  1
   "Agron-Ramban",                  #  2
   "Keren HaYesod-King George",    #  3
   "Derech Hebron",                 #  4
   "Jabotinsky",                    #  5
   "George Adam Smith-Lehi",        #  6
   "Herzl",                         #  7
   "Ben Zakai-Yehuda HaNasi",      #  8
   "Rachel Imenu-Hizkiyahu",       #  9
   "Bar Lev",                       # 10
   "Tzvi Yehuda",                   # 11
   "Baron Hirsch-Eliezer HaLevi",  # 12
   "Elazar HaModa'i-Katamon",      # 13
   "HaPalmach",                     # 14
   "Bezek-Beit",                    # 15
   "Yirmiyahu-Bar Ilan-Eshkol",    # 16
   "Golda-Shmuel HaNavi",          # 17
   "Strauss-Yehezkel",             # 18
   "Begin (Givat Ram)",             # 19
   "Golomb",                        # 20
   "Kolitz",                        # 21
   "Pierre Koenig",                 # 22
   "Shamgar-Ohel Yehoshua",        # 23
   "Bezalel-Rabin",                 # 24
   "Yehuda-Yanovsky",              # 25
   "David HaMelech",               # 26
   "Pat",                           # 27
   "Ussishkin-Radak-Molcho"         # 28
)

# Build name lookup: populated when wishing list is first loaded
.lane_name_map <- new.env(parent = emptyenv())

build_name_map <- function(wishing) {
  # Create a mapping from raw KML name -> English name
  for (i in seq_len(nrow(wishing))) {
    raw <- wishing$Name[i]
    if (i <= length(LANE_NAMES_BY_INDEX)) {
      .lane_name_map[[raw]] <- LANE_NAMES_BY_INDEX[i]
    }
  }
}

transliterate <- function(name) {
  en <- .lane_name_map[[name]]
  if (!is.null(en)) return(en)
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

  # Ensure name map is built
  if (length(ls(.lane_name_map)) == 0) build_name_map(wishing)

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
