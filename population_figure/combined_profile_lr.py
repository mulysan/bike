#!/usr/bin/env python3
"""
combined_profile_lr.py
Asymmetric profile: left side = 2025 density, right side = 2040 density.
All Jerusalem TMP areas. Full ring area as density denominator.
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
OUT_PATH = os.path.join(HERE, "jerusalem_density_profile_2025_vs_2040_lr.png")

KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785
RING_WIDTH = 1_000
N_RINGS    = 16
MAX_DIST   = RING_WIDTH * N_RINGS

COLOR_2025 = "#00CFCF"   # cyan  (left)
COLOR_2040 = "#FF6EC7"   # pink  (right)
BG_COLOR   = "#0d0d0d"
GRID_COLOR = "#2a2a2a"
TEXT_COLOR = "#FFFFFF"

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading jer_areas …")
areas = gpd.read_file(SHP_PATH)
areas = areas[areas["in_jeru"] == 1].copy()
areas["area_m2"] = areas.geometry.area
for col in ["pop_2025", "pop_2040"]:
    areas[col] = areas[col].fillna(0)

centre = (
    gpd.GeoDataFrame(geometry=[Point(KIKAR_ZION_LON, KIKAR_ZION_LAT)], crs="EPSG:4326")
    .to_crs(areas.crs).geometry.iloc[0]
)

# ── Ring geometries & fractions ───────────────────────────────────────────────
ring_geoms = []
for r in range(N_RINGS):
    outer = centre.buffer((r + 1) * RING_WIDTH)
    inner = centre.buffer(r * RING_WIDTH) if r > 0 else None
    ring_geoms.append(outer if inner is None else outer.difference(inner))

inter_fracs = [
    areas.geometry.intersection(g).area / areas["area_m2"].replace(0, np.nan)
    for g in ring_geoms
]
inter_frac_16 = (
    areas.geometry.intersection(centre.buffer(MAX_DIST)).area
    / areas["area_m2"].replace(0, np.nan)
)

rw = RING_WIDTH / 1000

def ring_densities(pop_col):
    pop = areas[pop_col]
    dens = [(frac * pop).fillna(0).sum() / (g.area / 1e6)
            for frac, g in zip(inter_fracs, ring_geoms)]
    total = (inter_frac_16 * pop).fillna(0).sum()
    return dens, total

def _side_spline(dens, sign, n=500):
    last_nz = max((i for i, d in enumerate(dens) if d > 0), default=0)
    zero_x  = min((last_nz + 3) * rw, 16)
    xs = np.array([(r + 0.5) * rw for r in range(last_nz + 1)] + [zero_x]) * sign
    ys = np.array(list(dens[:last_nz + 1]) + [0])
    if sign < 0:
        xs, ys = xs[::-1], ys[::-1]
    x_full = np.linspace(-16 if sign < 0 else 0, 0 if sign < 0 else 16, n)
    y_full = np.zeros(n)
    _ins = (x_full >= xs[0]) & (x_full <= xs[-1])
    y_full[_ins] = np.clip(make_interp_spline(xs, ys, k=3)(x_full[_ins]), 0, None)
    return x_full, y_full

dens_2025, total_2025 = ring_densities("pop_2025")
dens_2040, total_2040 = ring_densities("pop_2040")

x_l, y_l = _side_spline(dens_2025, sign=-1)   # 2025 on left
x_r, y_r = _side_spline(dens_2040, sign=+1)   # 2040 on right

print(f"  2025 total: {total_2025:,.0f}   2040 total: {total_2040:,.0f}")

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

ax.plot(x_l, y_l, color=COLOR_2025, linewidth=2.5, zorder=3)
ax.fill_between(x_l, y_l, alpha=0.15, color=COLOR_2025, zorder=2)

ax.plot(x_r, y_r, color=COLOR_2040, linewidth=2.5, zorder=3)
ax.fill_between(x_r, y_r, alpha=0.15, color=COLOR_2040, zorder=2)

ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--", zorder=4)

ax.text(x_l[int(np.argmax(y_l))], y_l.max() * 1.06,
        f"2025  {total_2025/1e6:.2f}m",
        color=COLOR_2025, fontsize=13, fontweight="bold", ha="center", va="bottom")
ax.text(x_r[int(np.argmax(y_r))], y_r.max() * 1.06,
        f"2040  {total_2040/1e6:.2f}m",
        color=COLOR_2040, fontsize=13, fontweight="bold", ha="center", va="bottom")

ax.grid(color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
ax.set_axisbelow(True)
ax.set_xlim(-16, 16)
ax.set_ylim(0, max(y_l.max(), y_r.max()) * 1.28)

x_ticks = list(range(-16, 0, 2)) + list(range(0, 17, 2))
ax.set_xticks(x_ticks)
ax.set_xticklabels([str(abs(v)) for v in x_ticks], color=TEXT_COLOR, fontsize=10)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
plt.setp(ax.get_yticklabels(), color=TEXT_COLOR, fontsize=10)
ax.tick_params(colors=TEXT_COLOR, which="both")
for spine in ax.spines.values():
    spine.set_edgecolor(GRID_COLOR)

ax.set_xlabel("Distance from Kikar Zion (km)", color=TEXT_COLOR, fontsize=12, labelpad=10)
ax.set_ylabel("Density (People per km²)",       color=TEXT_COLOR, fontsize=12, labelpad=10)

fig.text(0.45, 0.97, "Jerusalem – 2025 vs 2040 Density Profile",
         color=TEXT_COLOR, fontsize=17, fontweight="bold", ha="center", va="top")
fig.text(0.45, 0.91,
         "Radial Population Structure (0–16 km, 1 km bands)  ·  Left = 2025  |  Right = 2040",
         color="#AAAAAA", fontsize=10, ha="center", va="top")

note = (
    "Methodology\n"
    "All Jerusalem TMP areas.\n"
    "Population split by geometric\n"
    "intersection share per ring.\n"
    "Density denominator = full ring\n"
    "area (km²) for both sides.\n\n"
    "Source: jer_areas shapefile."
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
