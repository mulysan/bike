###############################################################################
# 03_accessibility.R
# Gravity-based accessibility model:
#   N = sum_i sum_j  P_i * E_j * tau_ij^theta
#
# Where:
#   P_i   = population of origin area i
#   E_j   = employment of destination area j
#   tau_ij = shortest-path distance (km) from i to j
#   theta  = distance decay exponent (negative)
#
# Roads without bike lanes are penalized by factor K.
###############################################################################

library(igraph)
library(sf)

compute_accessibility <- function(G, registry, areas_proj,
                                  theta = -1.0, k = 5, year = 2025) {
  # Compute accessibility metrics for all areas.
  #
  # Args:
  #   G          : igraph graph with edge attributes 'length' and 'has_bike_lane'
  #   registry   : node registry from build_road_network()
  #   areas_proj : sf data frame of areas in projected CRS
  #   theta      : distance decay parameter (negative)
  #   k          : penalty multiplier for roads without bike lanes
  #   year       : which year's pop/emp data to use
  #

  # Returns list(acc_origin, acc_dest, total_N):
  #   acc_origin[i] = sum_j E_j * tau_ij^theta   (jobs reachable from area i)
  #   acc_dest[j]   = sum_i P_i * tau_ij^theta   (people who can reach area j)
  #   total_N       = sum_i sum_j P_i * E_j * tau_ij^theta

  n_areas <- nrow(areas_proj)

  # --- Assign edge weights: length for bike lanes, length*K otherwise --------
  edge_lengths   <- E(G)$length
  has_bike_lane  <- E(G)$has_bike_lane
  E(G)$weight    <- ifelse(has_bike_lane, edge_lengths, edge_lengths * k)

  # --- Map each area centroid to nearest graph node --------------------------
  node_mat  <- get_node_coords_matrix(registry)
  centroids <- st_centroid(st_geometry(areas_proj))
  center_nodes <- integer(n_areas)

  for (i in seq_len(n_areas)) {
    cx <- st_coordinates(centroids[[i]])[1]
    cy <- st_coordinates(centroids[[i]])[2]
    dists <- sqrt((node_mat[, 1] - cx)^2 + (node_mat[, 2] - cy)^2)
    center_nodes[i] <- which.min(dists)
  }

  # --- Population and employment vectors ------------------------------------
  pop_col <- paste0("pop_", year)
  emp_col <- paste0("emp_", year)
  pop <- areas_proj[[pop_col]]
  emp <- areas_proj[[emp_col]]

  # --- Find largest connected component -------------------------------------
  comp <- components(G)
  largest_comp_id <- which.max(comp$csize)
  in_largest <- (comp$membership == largest_comp_id)

  # --- Compute shortest paths from each area centroid -----------------------
  acc_origin <- numeric(n_areas)
  acc_dest   <- numeric(n_areas)
  total_N    <- 0

  for (i in seq_len(n_areas)) {
    node_i <- center_nodes[i]
    if (!in_largest[node_i]) next

    # Dijkstra from node_i to all other nodes
    sp <- distances(G, v = node_i, weights = E(G)$weight, algorithm = "dijkstra")

    for (j in seq_len(n_areas)) {
      if (i == j) next
      node_j <- center_nodes[j]
      if (!in_largest[node_j]) next

      dist_m <- sp[1, node_j]
      if (is.infinite(dist_m)) next

      tau   <- max(dist_m / 1000, 0.1)   # convert to km, floor at 0.1
      decay <- tau ^ theta

      contribution <- pop[i] * emp[j] * decay
      total_N      <- total_N + contribution
      acc_origin[i] <- acc_origin[i] + emp[j] * decay
      acc_dest[j]   <- acc_dest[j]   + pop[i] * decay
    }
  }

  list(
    acc_origin = acc_origin,
    acc_dest   = acc_dest,
    total_N    = total_N
  )
}
