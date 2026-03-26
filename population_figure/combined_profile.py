#!/usr/bin/env python3
"""
combined_profile.py
Overlays 2020 and 2040 density profiles on a single figure.
(No 2050 data available – latest year in jer_areas is 2040.)
"""

import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline
from shapely.geometry import Point
import os

HERE     = os.path.dirname(os.path.abspath(__file__))
SHP_PATH = os.path.join(HERE, "..", "jer_areas.shp")
OUT_PATH = os.path.join(HERE, "jerusalem_density_profile_2025_2040.png")

KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785
RING_WIDTH = 1_000
N_RINGS    = 16
MAX_DIST   = RING_WIDTH * N_RINGS

BG_COLOR   = "#0d0d0d"
GRID_COLOR = "#2a2a2a"
TEXT_COLOR = "#FFFFFF"

YEARS = [
    {"year": 2025, "color": "#00CFCF", "label_offset": 1.06},  # cyan
    {"year": 2040, "color": "#FF6EC7", "label_offset": 1.06},  # hot pink
]

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading jer_areas …")
areas = gpd.read_file(SHP_PATH)
areas = areas[areas["in_jeru"] == 1].copy()
areas["area_m2"] = areas.geometry.area

centre = (
    gpd.GeoDataFrame(geometry=[Point(KIKAR_ZION_LON, KIKAR_ZION_LAT)], crs="EPSG:4326")
    .to_crs(areas.crs).geometry.iloc[0]
)

# Precompute ring geometries and intersection fractions
ring_geoms = []
for r in range(N_RINGS):
    outer = centre.buffer((r + 1) * RING_WIDTH)
    inner = centre.buffer(r * RING_WIDTH) if r > 0 else None
    ring_geoms.append(outer if inner is None else outer.difference(inner))

inter_frac_rings = [
    areas.geometry.intersection(g).area / areas["area_m2"].replace(0, np.nan)
    for g in ring_geoms
]
inter_frac_16 = (
    areas.geometry.intersection(centre.buffer(MAX_DIST)).area
    / areas["area_m2"].replace(0, np.nan)
)

midpoints = np.array([(r + 0.5) * (RING_WIDTH / 1000) for r in range(N_RINGS)])

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

y_max_global = 0

for cfg in YEARS:
    year    = cfg["year"]
    color   = cfg["color"]
    pop_col = f"pop_{year}"
    pop     = areas[pop_col].fillna(0)

    densities = [
        (frac * pop).fillna(0).sum() / (g.area / 1e6)
        for frac, g in zip(inter_frac_rings, ring_geoms)
    ]
    total_pop = (inter_frac_16 * pop).fillna(0).sum()
    pop_label = f"{total_pop / 1e6:.2f}m"

    rw = RING_WIDTH / 1000
    last_nz = max((i for i, d in enumerate(densities) if d > 0), default=0)
    zero_x  = min((last_nz + 3) * rw, 16)
    x_r = [(r + 0.5) * rw for r in range(last_nz + 1)] + [zero_x]
    y_r = list(densities[:last_nz + 1]) + [0]
    x   = np.array([-v for v in reversed(x_r)] + x_r)
    y   = np.array(list(reversed(y_r)) + y_r)

    x_s = np.linspace(-16, 16, 500)
    y_s = np.zeros(len(x_s))
    _ins = (x_s >= x[0]) & (x_s <= x[-1])
    y_s[_ins] = np.clip(make_interp_spline(x, y, k=3)(x_s[_ins]), 0, None)
    y_max_global = max(y_max_global, y_s.max())

    ax.plot(x_s, y_s, color=color, linewidth=2.5, zorder=3, label=f"{year}")
    ax.fill_between(x_s, y_s, alpha=0.12, color=color, zorder=2)

    peak_i = int(np.argmax(y_s))
    # Stagger labels slightly so they don't overlap
    v_offset = cfg["label_offset"]
    ax.text(
        x_s[peak_i], y_s[peak_i] * v_offset,
        f"Jerusalem {year}  {pop_label}",
        color=color, fontsize=13, fontweight="bold",
        ha="center", va="bottom",
    )
    print(f"  {year}: peak={max(densities):,.0f} p/km²  total={total_pop:,.0f}")

ax.grid(color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
ax.set_axisbelow(True)
ax.set_xlim(-16, 16)
ax.set_ylim(0, y_max_global * 1.30)

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

fig.text(0.45, 0.97, "Jerusalem Density Profile – 2025 vs 2040",
         color=TEXT_COLOR, fontsize=18, fontweight="bold", ha="center", va="top")
fig.text(0.45, 0.91, "Radial Population Structure (0–16 km, 1 km bands)",
         color="#AAAAAA", fontsize=11, ha="center", va="top")

note = (
    "Methodology\n"
    "Population in 1 km radial rings from\n"
    "Kikar Zion, average density per km².\n\n"
    "Source: jer_areas shapefile.\n"
    "Data available: 2020–2040.\n"
    "(No 2050 projection in dataset.)"
)
fig.text(
    0.87, 0.93, note,
    color="#BBBBBB", fontsize=8, va="top", ha="left", linespacing=1.55,
    bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a1a",
              edgecolor="#444444", linewidth=0.8),
)

plt.tight_layout(rect=[0, 0, 0.85, 0.88])
fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
plt.close(fig)
print(f"Saved → {OUT_PATH}")
