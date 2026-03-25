#!/usr/bin/env python3
"""
density_profile.py
Radial population density profile for Jerusalem, centered on Kikar Zion.
Replicates the style of "European Density Profiles" (radial 2 km rings).

Output: jerusalem_density_profile.png
"""

import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from shapely.geometry import Point
import os

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE     = os.path.dirname(os.path.abspath(__file__))
SHP_PATH = os.path.join(HERE, "..", "jer_areas.shp")
OUT_PATH = os.path.join(HERE, "jerusalem_density_profile.png")

# ── Parameters ────────────────────────────────────────────────────────────────
# Kikar Zion (Zion Square), Jerusalem city centre – WGS84
KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785

POP_YEAR   = 2025
POP_COL    = f"pop_{POP_YEAR}"
RING_WIDTH = 2_000   # metres (2 km)
N_RINGS    = 8       # bands 0-2, 2-4, …, 14-16 km
MAX_DIST   = RING_WIDTH * N_RINGS   # 16 km

# ── Style ─────────────────────────────────────────────────────────────────────
CITY_COLOR = "#FF6EC7"    # hot pink  (matches the palette in the reference figure)
BG_COLOR   = "#0d0d0d"
GRID_COLOR = "#2a2a2a"
TEXT_COLOR = "#FFFFFF"
FILL_ALPHA = 0.15

# ── Load and prepare data ─────────────────────────────────────────────────────
print("Loading jer_areas …")
areas = gpd.read_file(SHP_PATH)
areas = areas[areas["in_jeru"] == 1].copy()
areas[POP_COL] = areas[POP_COL].fillna(0)

# Already in EPSG:2039 (Israel TM, metres)
areas_proj = areas.copy()
areas_proj["area_m2"] = areas_proj.geometry.area

# Convert Kikar Zion to EPSG:2039
centre_wgs = gpd.GeoDataFrame(
    geometry=[Point(KIKAR_ZION_LON, KIKAR_ZION_LAT)], crs="EPSG:4326"
)
centre = centre_wgs.to_crs(areas_proj.crs).geometry.iloc[0]
print(f"  Kikar Zion (EPSG:2039): {centre.x:.0f}, {centre.y:.0f}")

# ── Compute density per ring ──────────────────────────────────────────────────
print("Computing radial density …")
ring_densities = []

for r in range(N_RINGS):
    r_inner = r * RING_WIDTH
    r_outer = (r + 1) * RING_WIDTH

    outer_buf = centre.buffer(r_outer)
    ring_geom = outer_buf if r == 0 else outer_buf.difference(centre.buffer(r_inner))
    ring_area_km2 = ring_geom.area / 1e6

    # Intersect each statistical area with the ring
    inter_areas = areas_proj.geometry.intersection(ring_geom)
    inter_frac   = inter_areas.area / areas_proj["area_m2"].replace(0, np.nan)
    pop_in_ring  = (inter_frac * areas_proj[POP_COL]).fillna(0).sum()

    density = pop_in_ring / ring_area_km2
    ring_densities.append(density)
    print(f"  Ring {r_inner/1000:.0f}-{r_outer/1000:.0f} km: "
          f"pop={pop_in_ring:,.0f}, density={density:,.0f} p/km²")

# ── Symmetric x / y for the profile chart ────────────────────────────────────
# Midpoint of each ring in km: 1, 3, 5, …, 15
midpoints = np.array([(r + 0.5) * (RING_WIDTH / 1000) for r in range(N_RINGS)])

x = np.concatenate([-midpoints[::-1], midpoints])          # -15…-1, 1…15
y = np.concatenate([ring_densities[::-1], ring_densities])  # mirror

# Smooth with cubic spline
x_smooth = np.linspace(x[0], x[-1], 500)
spl       = make_interp_spline(x, y, k=3)
y_smooth  = np.clip(spl(x_smooth), 0, None)

# ── Total population within 16 km (for the label) ────────────────────────────
buf16 = centre.buffer(MAX_DIST)
inter_frac_all = areas_proj.geometry.intersection(buf16).area / areas_proj["area_m2"].replace(0, np.nan)
total_pop_16km = (inter_frac_all * areas_proj[POP_COL]).fillna(0).sum()
pop_label = f"{total_pop_16km / 1e6:.2f}m"
print(f"\nTotal population within 16 km: {total_pop_16km:,.0f}  → {pop_label}")

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

ax.plot(x_smooth, y_smooth, color=CITY_COLOR, linewidth=2.5, zorder=3)
ax.fill_between(x_smooth, y_smooth, alpha=FILL_ALPHA, color=CITY_COLOR, zorder=2)

# City label at peak
peak_i = int(np.argmax(y_smooth))
ax.text(
    x_smooth[peak_i],
    y_smooth[peak_i] * 1.06,
    f"Jerusalem {pop_label}",
    color=CITY_COLOR, fontsize=14, fontweight="bold",
    ha="center", va="bottom",
)

# Grid
ax.grid(color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
ax.set_axisbelow(True)

# Axes
ax.set_xlim(-16, 16)
ax.set_ylim(0, y_smooth.max() * 1.25)
x_ticks = list(range(-16, 0, 2)) + list(range(0, 17, 2))
ax.set_xticks(x_ticks)
ax.set_xticklabels([str(abs(v)) for v in x_ticks], color=TEXT_COLOR, fontsize=10)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
plt.setp(ax.get_yticklabels(), color=TEXT_COLOR, fontsize=10)
ax.tick_params(colors=TEXT_COLOR, which="both")
for spine in ax.spines.values():
    spine.set_edgecolor(GRID_COLOR)

ax.set_xlabel("Distance from centre (km)", color=TEXT_COLOR, fontsize=12, labelpad=10)
ax.set_ylabel("Density (People per km²)",  color=TEXT_COLOR, fontsize=12, labelpad=10)

# Title
fig.text(
    0.45, 0.97,
    "Jerusalem Density Profile",
    color=TEXT_COLOR, fontsize=18, fontweight="bold",
    ha="center", va="top",
)
fig.text(
    0.45, 0.91,
    "Radial Population Structure (0–16 km, 2 km bands)",
    color="#AAAAAA", fontsize=11,
    ha="center", va="top",
)

# Methodology box (top-right, matching the reference figure)
methodology = (
    "Methodology\n"
    "Population measured in 2 km radial rings\n"
    "from Kikar Zion (city centre), showing\n"
    "average density (people per km²) within\n"
    "each ring, not cumulative totals.\n\n"
    f"Source: jer_areas shapefile,\n"
    f"{POP_YEAR} population projections.\n\n"
    f"All figures represent population within\n"
    f"16 km of Kikar Zion."
)
fig.text(
    0.87, 0.93, methodology,
    color="#BBBBBB", fontsize=8, va="top", ha="left",
    linespacing=1.55,
    bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a1a", edgecolor="#444444", linewidth=0.8),
)

plt.tight_layout(rect=[0, 0, 0.85, 0.88])
fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
print(f"\nSaved → {OUT_PATH}")
