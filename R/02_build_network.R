###############################################################################
# 02_build_network.R
# Build a road network graph, overlay bike lanes, connect area centroids
###############################################################################

library(sf)
library(igraph)

NODE_TOLERANCE <- 15   # meters: merge nodes within this distance
BUFFER_DIST    <- 25   # meters: bike lane must be within this of road

# --- Node management --------------------------------------------------------

make_node_registry <- function(tolerance = NODE_TOLERANCE) {
  # A simple environment that maps snapped coordinates -> node id
  env <- new.env(parent = emptyenv())
  env$coord_to_id <- list()
  env$id_to_coord <- list()
  env$counter     <- 0L
  env$tolerance   <- tolerance
  env
}

get_or_create_node <- function(registry, x, y) {
  tol <- registry$tolerance
  key <- paste(round(x / tol) * tol, round(y / tol) * tol, sep = ",")
  if (!is.null(registry$coord_to_id[[key]])) {
    return(registry$coord_to_id[[key]])
  }
  registry$counter <- registry$counter + 1L
  nid <- registry$counter
  registry$coord_to_id[[key]] <- nid
  registry$id_to_coord[[as.character(nid)]] <- c(x, y)
  nid
}

get_node_coords_matrix <- function(registry) {
  # Return an N x 2 matrix of all node coordinates, rows ordered by node id
  n <- registry$counter
  if (n == 0) return(matrix(numeric(0), ncol = 2))
  mat <- matrix(NA_real_, nrow = n, ncol = 2)
  for (i in seq_len(n)) {
    mat[i, ] <- registry$id_to_coord[[as.character(i)]]
  }
  mat
}

# --- Network construction ---------------------------------------------------

build_road_network <- function(roads_proj, areas_proj, tolerance = NODE_TOLERANCE) {
  # Build an igraph graph from projected road geometries.
  # Returns a list with: graph, registry (node coords), road_geoms, road_edges

  registry <- make_node_registry(tolerance)
  edges_from <- integer(0)
  edges_to   <- integer(0)
  edge_length <- numeric(0)

  road_geoms <- list()
  road_edge_keys <- list()   # list of c(min_id, max_id) per road

  message("  Adding road segments...")
  for (i in seq_len(nrow(roads_proj))) {
    geom <- st_geometry(roads_proj)[[i]]
    if (is.null(geom) || st_is_empty(geom)) next
    if (!inherits(geom, "LINESTRING")) next

    coords <- st_coordinates(geom)
    if (nrow(coords) < 2) next

    s <- get_or_create_node(registry, coords[1, 1], coords[1, 2])
    e <- get_or_create_node(registry, coords[nrow(coords), 1], coords[nrow(coords), 2])
    if (s == e) next

    len <- as.numeric(st_length(geom))
    edges_from  <- c(edges_from, s)
    edges_to    <- c(edges_to, e)
    edge_length <- c(edge_length, len)

    road_geoms[[length(road_geoms) + 1]] <- geom
    road_edge_keys[[length(road_edge_keys) + 1]] <- c(min(s, e), max(s, e))
  }

  # Build igraph (undirected)
  n_nodes <- registry$counter
  G <- make_empty_graph(n = n_nodes, directed = FALSE)
  if (length(edges_from) > 0) {
    edge_list <- as.vector(rbind(edges_from, edges_to))
    G <- add_edges(G, edge_list,
                   length = edge_length,
                   has_bike_lane = rep(FALSE, length(edges_from)))
  }

  # Connect area centroids to nearest road node
  message("  Connecting area centroids...")
  node_mat <- get_node_coords_matrix(registry)
  if (nrow(node_mat) > 0 && nrow(areas_proj) > 0) {
    centroids <- st_centroid(st_geometry(areas_proj))
    for (j in seq_along(centroids)) {
      cx <- st_coordinates(centroids[[j]])[1]
      cy <- st_coordinates(centroids[[j]])[2]

      # Find nearest existing node
      dists_to_nodes <- sqrt((node_mat[, 1] - cx)^2 + (node_mat[, 2] - cy)^2)
      nearest_id <- which.min(dists_to_nodes)
      min_dist   <- dists_to_nodes[nearest_id]

      if (min_dist > tolerance) {
        centroid_id <- get_or_create_node(registry, cx, cy)
        if (centroid_id != nearest_id) {
          # Need to grow the graph if new node was created
          if (centroid_id > vcount(G)) {
            G <- add_vertices(G, centroid_id - vcount(G))
          }
          G <- add_edges(G, c(centroid_id, nearest_id),
                         length = min_dist,
                         has_bike_lane = FALSE)
        }
      }
    }
  }

  list(
    graph          = G,
    registry       = registry,
    road_geoms     = road_geoms,
    road_edge_keys = road_edge_keys
  )
}

# --- Bike lane overlay ------------------------------------------------------

mark_bike_lane_edges <- function(network, bike_lane_layers) {
  # Identify road edges that are covered by bike lanes.
  # Uses a fully vectorized approach: union all bike lanes into one polygon,
  # then intersect all roads at once.
  # Returns a logical vector of edge indices that have bike lanes.

  G          <- network$graph
  road_geoms <- network$road_geoms
  road_keys  <- network$road_edge_keys
  n_edges    <- ecount(G)
  n_roads    <- length(road_geoms)

  if (n_roads == 0) return(logical(n_edges))

  # Build a lookup: "min_id,max_id" -> road index
  road_key_to_idx <- new.env(parent = emptyenv())
  for (ri in seq_len(n_roads)) {
    key <- paste(road_keys[[ri]][1], road_keys[[ri]][2], sep = ",")
    road_key_to_idx[[key]] <- ri
  }

  # Build a lookup: road index -> edge index in graph
  from_vec <- ends(G, E(G))[, 1]
  to_vec   <- ends(G, E(G))[, 2]
  edge_key_lookup <- new.env(parent = emptyenv())
  for (ei in seq_len(n_edges)) {
    key <- paste(min(from_vec[ei], to_vec[ei]), max(from_vec[ei], to_vec[ei]), sep = ",")
    edge_key_lookup[[key]] <- ei
  }

  # Collect all bike lane geometries into one sfc, project to TARGET_CRS
  all_lane_geoms <- list()
  for (layer in bike_lane_layers) {
    if (is.null(layer) || nrow(layer) == 0) next
    layer_proj <- st_transform(layer, TARGET_CRS)
    layer_lines <- st_cast(layer_proj, "LINESTRING", warn = FALSE)
    valid <- !st_is_empty(st_geometry(layer_lines))
    if (any(valid)) {
      all_lane_geoms <- c(all_lane_geoms, st_geometry(layer_lines[valid, ]))
    }
  }

  if (length(all_lane_geoms) == 0) return(logical(n_edges))

  # Buffer all lanes and union into one polygon
  message("    Buffering ", length(all_lane_geoms), " lane segments...")
  lanes_sfc <- st_sfc(all_lane_geoms, crs = TARGET_CRS)
  lanes_buffered <- st_buffer(lanes_sfc, BUFFER_DIST)
  lanes_union <- st_union(lanes_buffered)

  # Build road sfc and compute lengths
  roads_sfc <- st_sfc(road_geoms, crs = TARGET_CRS)
  road_lengths <- as.numeric(st_length(roads_sfc))

  # Find all roads that intersect the buffered lanes (fast R-tree)
  message("    Finding candidate roads...")
  candidates <- st_intersects(roads_sfc, lanes_union)
  candidate_ids <- which(sapply(candidates, length) > 0)
  message("    ", length(candidate_ids), " / ", n_roads, " roads near bike lanes")

  # Clip candidate roads by the lane buffer and check overlap
  message("    Computing overlaps...")
  marked_roads <- logical(n_roads)

  if (length(candidate_ids) > 0) {
    candidate_roads <- roads_sfc[candidate_ids]
    clipped <- st_intersection(candidate_roads, lanes_union)
    clipped_lengths <- as.numeric(st_length(clipped))

    for (k in seq_along(candidate_ids)) {
      ri <- candidate_ids[k]
      inter_len <- clipped_lengths[k]
      road_len  <- road_lengths[ri]
      overlap   <- if (road_len > 0) inter_len / road_len else 0

      should_mark <- (
        overlap > 0.5 ||
        (road_len < 50 && overlap > 0.3) ||
        inter_len > 20
      )
      if (should_mark) marked_roads[ri] <- TRUE
    }
  }

  # Map marked roads back to graph edge indices
  marked <- logical(n_edges)
  for (ri in which(marked_roads)) {
    key <- paste(road_keys[[ri]][1], road_keys[[ri]][2], sep = ",")
    ei  <- edge_key_lookup[[key]]
    if (!is.null(ei)) marked[ei] <- TRUE
  }

  message("    Marked ", sum(marked), " edges with bike lanes")
  marked
}

apply_bike_lanes_to_graph <- function(G, marked_edges) {
  # Set has_bike_lane = TRUE for marked edge indices
  E(G)$has_bike_lane[marked_edges] <- TRUE
  G
}
