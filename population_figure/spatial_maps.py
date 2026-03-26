#!/usr/bin/env python3
"""
spatial_maps.py
Two choropleth maps of Jerusalem statistical areas:
  Map 1 – Distance of each area's centroid from Kikar Zion (km)
  Map 2 – Population density per area (people per km², 2025)
"""

import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from shapely.geometry import Point
import os

HERE     = os.path.dirname(os.path.abspath(__file__))
SHP_PATH = os.path.join(HERE, "..", "jer_areas.shp")

KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785
POP_YEAR = 2025
POP_COL  = f"pop_{POP_YEAR}"
EMP_COL  = f"emp_{POP_YEAR}"

BG_COLOR     = "#0d0d0d"
TEXT_COLOR   = "#FFFFFF"
BORDER_COLOR = "#333333"
STAR_COLOR   = "#FFD700"   # gold star for Kikar Zion

# Spectral colormap matching the paper's style (dark-blue → cyan → yellow → orange → crimson)
SPECTRAL_COLORS = [
    (0.00, "#0000CD"),
    (0.25, "#00CED1"),
    (0.50, "#FFFF00"),
    (0.75, "#FFA500"),
    (1.00, "#DC143C"),
]
SPECTRAL_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "spectral_custom",
    [(p, c) for p, c in SPECTRAL_COLORS],
)

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading jer_areas …")
areas = gpd.read_file(SHP_PATH)
areas = areas[areas["in_jeru"] == 1].copy()
areas[POP_COL] = areas[POP_COL].fillna(0)
areas[EMP_COL] = areas[EMP_COL].fillna(0)
areas["area_km2"] = areas.geometry.area / 1e6

centre_proj = (
    gpd.GeoDataFrame(geometry=[Point(KIKAR_ZION_LON, KIKAR_ZION_LAT)], crs="EPSG:4326")
    .to_crs(areas.crs).geometry.iloc[0]
)

# Distance of each centroid from Kikar Zion (km)
areas["dist_km"] = areas.geometry.centroid.distance(centre_proj) / 1000

# Population and employment density
areas["density"]     = (areas[POP_COL] / areas["area_km2"].replace(0, np.nan)).fillna(0)
areas["emp_density"] = (areas[EMP_COL] / areas["area_km2"].replace(0, np.nan)).fillna(0)

# For plotting, convert to WGS84
areas_wgs = areas.to_crs("EPSG:4326")
centre_wgs = gpd.GeoDataFrame(
    geometry=[Point(KIKAR_ZION_LON, KIKAR_ZION_LAT)], crs="EPSG:4326"
).geometry.iloc[0]


def add_colorbar(fig, ax, cmap, vmin, vmax, label, fmt="{:.0f}"):
    """Draw a vertical colorbar to the right of ax."""
    sm = cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, aspect=25)
    cb.set_label(label, color=TEXT_COLOR, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=TEXT_COLOR)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=TEXT_COLOR, fontsize=8)
    cb.outline.set_edgecolor("#444444")


def plot_star(ax, point, size=120):
    ax.scatter(point.x, point.y, marker="*", s=size, color=STAR_COLOR,
               zorder=10, linewidths=0.4, edgecolors="#333")
    ax.annotate(
        "Kikar Zion", xy=(point.x, point.y),
        xytext=(0.006, 0.004), textcoords="offset points",
        color=STAR_COLOR, fontsize=7, ha="left",
        xycoords="data",
    )


# ── Map 1: Distance from Kikar Zion ──────────────────────────────────────────
print("Rendering Map 1 – distance …")
fig1, ax1 = plt.subplots(figsize=(10, 9), facecolor=BG_COLOR)
ax1.set_facecolor(BG_COLOR)

vmin_d, vmax_d = 0, areas["dist_km"].max()
norm_d = mcolors.Normalize(vmin=vmin_d, vmax=vmax_d)
colors_d = [SPECTRAL_CMAP(norm_d(v)) for v in areas["dist_km"]]

areas_wgs.plot(ax=ax1, color=colors_d, edgecolor=BORDER_COLOR, linewidth=0.3)
plot_star(ax1, centre_wgs)

# Ring circles at 2, 4, 6, 8 km for reference
for ring_km in [2, 4, 6, 8]:
    ring_buf = centre_proj.buffer(ring_km * 1000)
    ring_gdf = gpd.GeoDataFrame(geometry=[ring_buf], crs=areas.crs).to_crs("EPSG:4326")
    ring_gdf.boundary.plot(ax=ax1, color="#555555", linewidth=0.6, linestyle="--")
    # Label
    ring_pt = ring_gdf.geometry.iloc[0].exterior.interpolate(0.25, normalized=True)
    ax1.text(ring_pt.x, ring_pt.y, f"{ring_km} km",
             color="#888888", fontsize=7, ha="left", va="bottom")

add_colorbar(fig1, ax1, SPECTRAL_CMAP, vmin_d, vmax_d, "Distance from Kikar Zion (km)")

ax1.set_axis_off()
fig1.text(0.5, 0.96, "Distance from City Centre",
          color=TEXT_COLOR, fontsize=16, fontweight="bold", ha="center", va="top")
fig1.text(0.5, 0.91, "Centroid distance of each statistical area from Kikar Zion",
          color="#AAAAAA", fontsize=10, ha="center", va="top")

plt.tight_layout(rect=[0, 0, 1, 0.90])
out1 = os.path.join(HERE, "jerusalem_map_distance.png")
fig1.savefig(out1, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
plt.close(fig1)
print(f"  Saved → {out1}")


# ── Map 2: Population density ─────────────────────────────────────────────────
print("Rendering Map 2 – density …")
fig2, ax2 = plt.subplots(figsize=(10, 9), facecolor=BG_COLOR)
ax2.set_facecolor(BG_COLOR)

# Log-scale normalisation (matching the paper's accessibility figures)
pos_mask = areas["density"] > 0
log_dens  = np.where(pos_mask, np.log(areas["density"].clip(lower=1)), 0)
vmin_ld, vmax_ld = log_dens[pos_mask].min(), log_dens.max()
norm_ld   = mcolors.Normalize(vmin=vmin_ld, vmax=vmax_ld)

no_data_rgba = mcolors.to_rgba("#1a1a1a")
colors_ld = np.array([
    SPECTRAL_CMAP(norm_ld(ld)) if pos else no_data_rgba
    for ld, pos in zip(log_dens, pos_mask)
])

areas_wgs.plot(ax=ax2, color=colors_ld, edgecolor=BORDER_COLOR, linewidth=0.3)
plot_star(ax2, centre_wgs)

# Ring circles at 2, 4, 6, 8 km (same as distance map)
for ring_km in [2, 4, 6, 8]:
    ring_buf = centre_proj.buffer(ring_km * 1000)
    ring_gdf = gpd.GeoDataFrame(geometry=[ring_buf], crs=areas.crs).to_crs("EPSG:4326")
    ring_gdf.boundary.plot(ax=ax2, color="#555555", linewidth=0.6, linestyle="--")
    ring_pt = ring_gdf.geometry.iloc[0].exterior.interpolate(0.25, normalized=True)
    ax2.text(ring_pt.x, ring_pt.y, f"{ring_km} km",
             color="#888888", fontsize=7, ha="left", va="bottom")
sm2 = cm.ScalarMappable(cmap=SPECTRAL_CMAP, norm=mcolors.Normalize(vmin=vmin_ld, vmax=vmax_ld))
sm2.set_array([])
cb2 = fig2.colorbar(sm2, ax=ax2, fraction=0.03, pad=0.02, aspect=25)
cb2.set_label(f"Density – people per km² ({POP_YEAR}, log scale)", color=TEXT_COLOR, fontsize=9)
cb2.ax.yaxis.set_tick_params(color=TEXT_COLOR)
# Replace log tick labels with real values
tick_log = np.linspace(vmin_ld, vmax_ld, 5)
tick_real = np.exp(tick_log).astype(int)
cb2.set_ticks(tick_log)
cb2.set_ticklabels([f"{v:,}" for v in tick_real])
plt.setp(cb2.ax.yaxis.get_ticklabels(), color=TEXT_COLOR, fontsize=8)
cb2.outline.set_edgecolor("#444444")

ax2.set_axis_off()
fig2.text(0.5, 0.96, f"Population Density by Statistical Area ({POP_YEAR})",
          color=TEXT_COLOR, fontsize=16, fontweight="bold", ha="center", va="top")
fig2.text(0.5, 0.91, "People per km² (log scale)  ·  Jerusalem areas only",
          color="#AAAAAA", fontsize=10, ha="center", va="top")

plt.tight_layout(rect=[0, 0, 1, 0.90])
out2 = os.path.join(HERE, "jerusalem_map_density.png")
fig2.savefig(out2, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
plt.close(fig2)
print(f"  Saved → {out2}")


# ── Map 3: Employment density ─────────────────────────────────────────────────
print("Rendering Map 3 – employment density …")
fig3, ax3 = plt.subplots(figsize=(10, 9), facecolor=BG_COLOR)
ax3.set_facecolor(BG_COLOR)

pos_mask_e = areas["emp_density"] > 0
log_emp    = np.where(pos_mask_e, np.log(areas["emp_density"].clip(lower=1)), 0)
vmin_le, vmax_le = log_emp[pos_mask_e].min(), log_emp.max()
norm_le    = mcolors.Normalize(vmin=vmin_le, vmax=vmax_le)

colors_le = np.array([
    SPECTRAL_CMAP(norm_le(le)) if pos else no_data_rgba
    for le, pos in zip(log_emp, pos_mask_e)
])

areas_wgs.plot(ax=ax3, color=colors_le, edgecolor=BORDER_COLOR, linewidth=0.3)
plot_star(ax3, centre_wgs)

for ring_km in [2, 4, 6, 8]:
    ring_buf = centre_proj.buffer(ring_km * 1000)
    ring_gdf = gpd.GeoDataFrame(geometry=[ring_buf], crs=areas.crs).to_crs("EPSG:4326")
    ring_gdf.boundary.plot(ax=ax3, color="#555555", linewidth=0.6, linestyle="--")
    ring_pt = ring_gdf.geometry.iloc[0].exterior.interpolate(0.25, normalized=True)
    ax3.text(ring_pt.x, ring_pt.y, f"{ring_km} km",
             color="#888888", fontsize=7, ha="left", va="bottom")

sm3 = cm.ScalarMappable(cmap=SPECTRAL_CMAP, norm=mcolors.Normalize(vmin=vmin_le, vmax=vmax_le))
sm3.set_array([])
cb3 = fig3.colorbar(sm3, ax=ax3, fraction=0.03, pad=0.02, aspect=25)
cb3.set_label(f"Employment density – jobs per km² ({POP_YEAR}, log scale)", color=TEXT_COLOR, fontsize=9)
cb3.ax.yaxis.set_tick_params(color=TEXT_COLOR)
tick_log_e  = np.linspace(vmin_le, vmax_le, 5)
tick_real_e = np.exp(tick_log_e).astype(int)
cb3.set_ticks(tick_log_e)
cb3.set_ticklabels([f"{v:,}" for v in tick_real_e])
plt.setp(cb3.ax.yaxis.get_ticklabels(), color=TEXT_COLOR, fontsize=8)
cb3.outline.set_edgecolor("#444444")

ax3.set_axis_off()
fig3.text(0.5, 0.96, f"Employment Density by Statistical Area ({POP_YEAR})",
          color=TEXT_COLOR, fontsize=16, fontweight="bold", ha="center", va="top")
fig3.text(0.5, 0.91, "Jobs per km² (log scale)  ·  Jerusalem areas only",
          color="#AAAAAA", fontsize=10, ha="center", va="top")

plt.tight_layout(rect=[0, 0, 1, 0.90])
out3 = os.path.join(HERE, "jerusalem_map_employment.png")
fig3.savefig(out3, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
plt.close(fig3)
print(f"  Saved → {out3}")
