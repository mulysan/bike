###############################################################################
# 05_figures.R
# Generate PDF figures for the academic paper:
#   Figure 1: Baseline accessibility (origin + destination)
#   Figure 2: Improvement with top 5 lanes
#   Figure 3: Individual lane impacts (top 3 lanes)
#   Figure 4: Side-by-side comparison of top 3 lanes
#   Figure 5: Cumulative impact progression
###############################################################################

library(sf)
library(grDevices)

# --- Color scheme (matches the interactive HTML map) ------------------------

spectral_color <- function(t) {
  # Map a normalized value t in [0,1] to an RGB color on the spectral scale:
  # dark blue -> cyan -> yellow -> orange -> crimson
  stops <- list(
    list(pos = 0.00, r = 0,   g = 0,   b = 205),
    list(pos = 0.25, r = 0,   g = 206, b = 209),
    list(pos = 0.50, r = 255, g = 255, b = 0),
    list(pos = 0.75, r = 255, g = 165, b = 0),
    list(pos = 1.00, r = 220, g = 20,  b = 60)
  )
  t <- max(0, min(1, t))

  # Find the bracketing stops
  i <- 1
  while (i < length(stops) && stops[[i + 1]]$pos < t) i <- i + 1
  if (i >= length(stops)) i <- length(stops) - 1

  s0 <- stops[[i]]
  s1 <- stops[[i + 1]]
  f  <- if (s1$pos != s0$pos) (t - s0$pos) / (s1$pos - s0$pos) else 0

  r <- round(s0$r + (s1$r - s0$r) * f)
  g <- round(s0$g + (s1$g - s0$g) * f)
  b <- round(s0$b + (s1$b - s0$b) * f)

  rgb(r, g, b, maxColorValue = 255)
}

GRAY_COLOR   <- "#BEBEBE"
LANE_ORANGE  <- "#FF9800"
LANE_GREEN   <- "#1B5E20"
BORDER_COLOR <- "#2c3e50"


# --- Helper: color areas by values ------------------------------------------

color_areas <- function(values, mode = "accessibility") {
  # Return a vector of colors, one per area.
  # mode = "accessibility": log-scale normalization

  # mode = "change": log(v+1) normalization, zero = gray

  pos_idx <- which(values > 0)
  colors  <- rep(GRAY_COLOR, length(values))

  if (length(pos_idx) == 0) return(colors)

  if (mode == "accessibility") {
    log_vals <- log(values[pos_idx])
    mn <- min(log_vals)
    mx <- max(log_vals)
    for (k in seq_along(pos_idx)) {
      n <- if (mx > mn) (log_vals[k] - mn) / (mx - mn) else 0
      colors[pos_idx[k]] <- spectral_color(n)
    }
  } else {
    log_vals <- log(values[pos_idx] + 1)
    mx <- max(log_vals)
    for (k in seq_along(pos_idx)) {
      n <- if (mx > 0) log_vals[k] / mx else 0
      colors[pos_idx[k]] <- spectral_color(n)
    }
  }

  colors
}


# --- Helper: plot areas on a device -----------------------------------------

plot_areas <- function(areas_wgs84, values, mode = "accessibility",
                       title = "", alpha = 0.5) {
  colors <- color_areas(values, mode)
  # Add transparency
  colors_alpha <- adjustcolor(colors, alpha.f = alpha)

  plot(st_geometry(areas_wgs84), col = colors_alpha, border = BORDER_COLOR,
       lwd = 0.4, main = title, cex.main = 1.0)
}


# --- Helper: draw a lane geometry -------------------------------------------

plot_lane <- function(lane_geom, col = LANE_ORANGE, lwd = 3) {
  if (is.null(lane_geom) || st_is_empty(lane_geom)) return(invisible())
  plot(st_sfc(lane_geom), col = col, lwd = lwd, add = TRUE)
}


# --- Helper: add a spectral color bar ---------------------------------------

add_colorbar <- function(values, mode = "accessibility") {
  # Draw a vertical color bar in the right margin
  n_steps <- 100
  usr <- par("usr")
  x_right <- usr[2]
  x_left  <- x_right - (usr[2] - usr[1]) * 0.03
  y_bot   <- usr[3] + (usr[4] - usr[3]) * 0.15
  y_top   <- usr[4] - (usr[4] - usr[3]) * 0.15

  for (i in seq_len(n_steps)) {
    frac <- (i - 1) / (n_steps - 1)
    y0 <- y_bot + frac * (y_top - y_bot)
    y1 <- y_bot + (frac + 1 / n_steps) * (y_top - y_bot)
    rect(x_left, y0, x_right, y1, col = spectral_color(frac), border = NA)
  }
  rect(x_left, y_bot, x_right, y_top, border = "black", lwd = 0.5)

  # Labels
  pos_vals <- values[values > 0]
  if (length(pos_vals) == 0) return(invisible())

  if (mode == "accessibility") {
    mn <- min(log(pos_vals))
    mx <- max(log(pos_vals))
    labels <- round(exp(c(mn, (mn + mx) / 2, mx)))
  } else {
    mx <- max(log(pos_vals + 1))
    max_pct <- exp(mx) - 1
    labels <- c("0%", sprintf("%.1f%%", max_pct / 2), sprintf("%.1f%%", max_pct))
  }
  text(x_right + (usr[2] - usr[1]) * 0.01,
       c(y_bot, (y_bot + y_top) / 2, y_top),
       labels = labels, adj = 0, cex = 0.6)

  # Add "Low" and "High" labels at bottom and top of colour bar
  text((x_left + x_right) / 2, y_bot - (usr[4] - usr[3]) * 0.03,
       labels = "Low", cex = 0.7, font = 2)
  text((x_left + x_right) / 2, y_top + (usr[4] - usr[3]) * 0.03,
       labels = "High", cex = 0.7, font = 2)
}


# =============================================================================
# Figure generation functions
# =============================================================================

generate_figure1 <- function(areas, acc_orig, acc_dest, output_path) {
  # Figure 1: Baseline Accessibility (origin and destination side by side)
  areas_wgs <- st_transform(areas, WGS84)

  pdf(output_path, width = 14, height = 7)
  par(mfrow = c(1, 2), mar = c(2, 2, 3, 4))

  plot_areas(areas_wgs, acc_orig, "accessibility", "Origin Accessibility")
  add_colorbar(acc_orig, "accessibility")

  plot_areas(areas_wgs, acc_dest, "accessibility", "Destination Accessibility")
  add_colorbar(acc_dest, "accessibility")

  title("Baseline Accessibility by Statistical Area", outer = TRUE, line = -1,
        cex.main = 1.3, font.main = 2)

  dev.off()
  message("  Saved ", output_path)
}


generate_figure2 <- function(areas, imp_orig, imp_dest, top_names, output_path) {
  # Figure 2: Improvement with top 5 lanes (origin + destination)
  areas_wgs <- st_transform(areas, WGS84)
  subtitle <- paste0("Top lanes: ", paste(top_names[1:min(3, length(top_names))],
                                          collapse = ", "))

  pdf(output_path, width = 14, height = 7)
  par(mfrow = c(1, 2), mar = c(2, 2, 3, 4))

  plot_areas(areas_wgs, imp_orig, "change", "Origin Improvement (%)", alpha = 0.6)
  add_colorbar(imp_orig, "change")

  plot_areas(areas_wgs, imp_dest, "change", "Destination Improvement (%)", alpha = 0.6)
  add_colorbar(imp_dest, "change")

  title(paste0("Accessibility Improvement with Top ", length(top_names), " Lanes"),
        outer = TRUE, line = -1, cex.main = 1.3, font.main = 2)
  mtext(subtitle, side = 1, outer = TRUE, line = -1, cex = 0.8)

  dev.off()
  message("  Saved ", output_path)
}


generate_figure3 <- function(areas, lane_name, imp_orig, imp_dest,
                             lane_geom_wgs, output_path) {
  # Figure 3: Impact of a single lane (origin + destination)
  areas_wgs <- st_transform(areas, WGS84)

  pdf(output_path, width = 14, height = 7)
  par(mfrow = c(1, 2), mar = c(2, 2, 3, 4))

  plot_areas(areas_wgs, imp_orig, "change", "Origin Impact", alpha = 0.6)
  plot_lane(lane_geom_wgs, col = LANE_ORANGE, lwd = 4)
  add_colorbar(imp_orig, "change")
  legend("bottomleft", legend = "Proposed Lane", col = LANE_ORANGE, lwd = 4,
         cex = 0.8, bg = "white")

  plot_areas(areas_wgs, imp_dest, "change", "Destination Impact", alpha = 0.6)
  plot_lane(lane_geom_wgs, col = LANE_ORANGE, lwd = 4)
  add_colorbar(imp_dest, "change")

  title(paste("Impact of", lane_name), outer = TRUE, line = -1,
        cex.main = 1.3, font.main = 2)

  dev.off()
  message("  Saved ", output_path)
}


generate_figure4 <- function(areas, lane_impacts, output_path) {
  # Figure 4: Side-by-side comparison of top 3 lanes
  # lane_impacts: list of lists, each with $name, $imp_orig, $imp_dest, $geom_wgs84
  areas_wgs <- st_transform(areas, WGS84)
  n_lanes <- min(3, length(lane_impacts))

  pdf(output_path, width = 14, height = 5 * n_lanes)
  par(mfrow = c(n_lanes, 2), mar = c(1, 1, 3, 4))

  for (i in seq_len(n_lanes)) {
    li <- lane_impacts[[i]]

    plot_areas(areas_wgs, li$imp_orig, "change",
               paste(li$name, "- Origin"), alpha = 0.6)
    plot_lane(li$geom_wgs84, col = LANE_ORANGE, lwd = 3)

    plot_areas(areas_wgs, li$imp_dest, "change",
               paste(li$name, "- Destination"), alpha = 0.6)
    plot_lane(li$geom_wgs84, col = LANE_ORANGE, lwd = 3)
  }

  title("Comparison of Top Ranked Lanes", outer = TRUE, line = -1,
        cex.main = 1.3, font.main = 2)

  dev.off()
  message("  Saved ", output_path)
}


generate_figure5 <- function(areas, cumulative_impacts, output_path) {
  # Figure 5: Cumulative impact progression (4 panels)
  # cumulative_impacts: list of lists, each with $imp_orig, $lane_names, $geom_wgs84
  areas_wgs <- st_transform(areas, WGS84)

  stages <- c(1, 2, 3, 5)
  stage_labels <- c("After Top 1 Lane", "After Top 2 Lanes",
                    "After Top 3 Lanes", "After Top 5 Lanes")

  pdf(output_path, width = 14, height = 12)
  par(mfrow = c(2, 2), mar = c(1, 1, 3, 4))

  for (panel in seq_along(stages)) {
    si <- stages[panel]
    if (si > length(cumulative_impacts)) next

    ci <- cumulative_impacts[[si]]
    plot_areas(areas_wgs, ci$imp_orig, "change",
               paste0(stage_labels[panel], "\n(", ci$lane_names, ")"), alpha = 0.6)

    # Plot all lanes up to this stage
    for (j in seq_len(si)) {
      col <- if (j == si) LANE_ORANGE else LANE_GREEN
      plot_lane(cumulative_impacts[[j]]$geom_wgs84, col = col, lwd = 2.5)
    }
    add_colorbar(ci$imp_orig, "change")
  }

  title("Cumulative Origin Accessibility Improvement", outer = TRUE, line = -1,
        cex.main = 1.3, font.main = 2)

  dev.off()
  message("  Saved ", output_path)
}
