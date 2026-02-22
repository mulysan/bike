###############################################################################
# 01_load_data.R
# Load all spatial data: statistical areas, road network, bike lanes
###############################################################################

library(sf)
library(dplyr)

# Coordinate reference systems
TARGET_CRS <- 2039   # Israel TM (meters)
WGS84      <- 4326

# Data years available in shapefile
DATA_YEARS  <- c(2020, 2025, 2030, 2035, 2040)
DEFAULT_YEAR <- 2025

load_areas <- function(data_dir) {
  # Read statistical areas shapefile, keep only Jerusalem areas
  areas <- st_read(file.path(data_dir, "jer_areas.shp"), quiet = TRUE)
  areas <- areas[areas$in_jeru == 1, ]

  # Replace NA with 0 in population and employment columns
  for (yr in DATA_YEARS) {
    pop_col <- paste0("pop_", yr)
    emp_col <- paste0("emp_", yr)
    areas[[pop_col]][is.na(areas[[pop_col]])] <- 0
    areas[[emp_col]][is.na(areas[[emp_col]])] <- 0
  }

  # Default year columns for convenience
  areas$pop <- areas[[paste0("pop_", DEFAULT_YEAR)]]
  areas$emp <- areas[[paste0("emp_", DEFAULT_YEAR)]]

  areas
}

load_kml <- function(filepath) {
  # Load a KML file; return empty sf if file is missing or unreadable.
  # KML files often have 3D coords (Z), which we drop to avoid WKB errors.
  if (!file.exists(filepath)) {
    message("  File not found: ", filepath, " - using empty layer")
    return(st_sf(Name = character(0), geometry = st_sfc(), crs = WGS84))
  }
  result <- tryCatch(
    st_read(filepath, quiet = TRUE),
    error = function(e) {
      message("  Could not read ", filepath, ": ", e$message)
      st_sf(Name = character(0), geometry = st_sfc(), crs = WGS84)
    }
  )
  # Drop Z dimension (KML geometries are often 3D)
  if (nrow(result) > 0) {
    result <- st_zm(result, drop = TRUE, what = "ZM")
  }
  result
}

load_all_data <- function(data_dir) {
  # Load all input files and return as a named list
  message("Loading data from: ", data_dir)

  areas        <- load_areas(data_dir)
  roads        <- load_kml(file.path(data_dir, "jerusalem_roads.kml"))
  completed    <- load_kml(file.path(data_dir, "bike_lanes_completed.kml"))
  construction <- load_kml(file.path(data_dir, "bike_lanes_construction.kml"))
  wishing      <- load_kml(file.path(data_dir, "bike_lanes_wishing_list.kml"))

  message("  Areas: ", nrow(areas),
          " | Roads: ", nrow(roads),
          " | Completed lanes: ", nrow(completed),
          " | Construction: ", nrow(construction),
          " | Wishing list: ", nrow(wishing))

  list(
    areas        = areas,
    roads        = roads,
    completed    = completed,
    construction = construction,
    wishing      = wishing
  )
}
