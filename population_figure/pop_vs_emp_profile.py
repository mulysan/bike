#!/usr/bin/env python3
"""
pop_vs_emp_profile.py
Left side = population density, right side = employment density.
All Jerusalem areas, year 2025. Full ring area as denominator for both sides.
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
OUT_PATH = os.path.join(HERE, "jerusalem_density_profile_pop_vs_emp.png")

KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785
RING_WIDTH = 1_000
N_RINGS    = 16
MAX_DIST   = RING_WIDTH * N_RINGS
YEAR       = 2025

POP_COLOR = "#FF6EC7"   # pink  (left)
EMP_COLOR = "#FFD700"   # gold  (right)
BG_COLOR  = "#0d0d0d"
GRID_COLOR = "#2a2a2a"
TEXT_COLOR = "#FFFFFF"

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading jer_areas …")
areas = gpd.read_file(SHP_PATH)
areas = areas[areas["in_jeru"] == 1].copy()
areas["area_m2"] = areas.geometry.area
areas[f"pop_{YEAR}"] = areas[f"pop_{YEAR}"].fillna(0)
areas[f"emp_{YEAR}"] = areas[f"emp_{YEAR}"].fillna(0)

centre = (
    gpd.GeoDataFrame(geometry=[Point(KIKAR_ZION_LON, KIKAR_ZION_LAT)], crs="EPSG:4326")
    .to_crs(areas.crs).geometry.iloc[0]
)

# ── Ring geometries & intersection fractions ──────────────────────────────────
ring_geoms = []
for r in range(N_RINGS):
    outer = centre.buffer((r + 1) * RING_WIDTH)
    inner = centre.buffer(r * RING_WIDTH) if r > 0 else None
    ring_geoms.append(outer if inner is None else outer.difference(inner))

inter_fracs = []
ring_footprint_km2 = []
for g in ring_geoms:
    inter_area = areas.geometry.intersection(g).area
    inter_fracs.append(inter_area / areas["area_m2"].replace(0, np.nan))
    ring_footprint_km2.append(inter_area.sum() / 1e6)

inter_frac_16 = (
    areas.geometry.intersection(centre.buffer(MAX_DIST)).area
    / areas["area_m2"].replace(0, np.nan)
)

midpoints = np.array([(r + 0.5) * (RING_WIDTH / 1000) for r in range(N_RINGS)])


def ring_densities(col):
    vals = areas[col].fillna(0)
    dens = [
        (frac * vals).fillna(0).sum() / foot_km2 if foot_km2 > 0 else 0
        for frac, foot_km2 in zip(inter_fracs, ring_footprint_km2)
    ]
    total = (inter_frac_16 * vals).fillna(0).sum()
    return dens, total


pop_dens, pop_total = ring_densities(f"pop_{YEAR}")
emp_dens, emp_total = ring_densities(f"emp_{YEAR}")

print(f"  Pop densities: {[f'{d:,.0f}' for d in pop_dens]}")
print(f"  Emp densities: {[f'{d:,.0f}' for d in emp_dens]}")
print(f"  Pop total: {pop_total:,.0f}   Emp total: {emp_total:,.0f}")

# ── Smooth curves (each side tapers independently to zero) ───────────────────
rw = RING_WIDTH / 1000

def _side_spline(dens, sign, n=500):
    last_nz = max((i for i, d in enumerate(dens) if d > 0), default=0)
    zero_x  = min((last_nz + 3) * rw, 16)
    xs = np.array([0] + [(r + 0.5) * rw for r in range(last_nz + 1)] + [zero_x]) * sign
    ys = np.array([dens[0]] + list(dens[:last_nz + 1]) + [0])
    if sign < 0:
        xs, ys = xs[::-1], ys[::-1]
    # Extend to full half: left -16→0, right 0→16
    x_full = np.linspace(-16 if sign < 0 else 0, 0 if sign < 0 else 16, n)
    y_full = np.zeros(n)
    _ins = (x_full >= xs[0]) & (x_full <= xs[-1])
    y_full[_ins] = np.clip(make_interp_spline(xs, ys, k=3)(x_full[_ins]), 0, None)
    return x_full, y_full

x_pop, y_pop_s = _side_spline(pop_dens, sign=-1)
x_emp, y_emp_s = _side_spline(emp_dens, sign=+1)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

ax.plot(x_pop, y_pop_s, color=POP_COLOR, linewidth=2.5, zorder=3)
ax.fill_between(x_pop, y_pop_s, alpha=0.15, color=POP_COLOR, zorder=2)

ax.plot(x_emp, y_emp_s, color=EMP_COLOR, linewidth=2.5, zorder=3)
ax.fill_between(x_emp, y_emp_s, alpha=0.15, color=EMP_COLOR, zorder=2)

ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--", zorder=4)

ax.text(x_pop[int(np.argmax(y_pop_s))], y_pop_s.max() * 1.06,
        f"Population  {pop_total/1e6:.2f}m",
        color=POP_COLOR, fontsize=13, fontweight="bold", ha="center", va="bottom")
ax.text(x_emp[int(np.argmax(y_emp_s))], y_emp_s.max() * 1.06,
        f"Employment  {emp_total/1e3:.0f}k",
        color=EMP_COLOR, fontsize=13, fontweight="bold", ha="center", va="bottom")

# Grid & axes
ax.grid(color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
ax.set_axisbelow(True)
ax.set_xlim(-16, 16)
ax.set_ylim(0, max(y_pop_s.max(), y_emp_s.max()) * 1.28)  # noqa: already updated vars

x_ticks = list(range(-16, 0, 2)) + list(range(0, 17, 2))
ax.set_xticks(x_ticks)
ax.set_xticklabels([str(abs(v)) for v in x_ticks], color=TEXT_COLOR, fontsize=10)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
plt.setp(ax.get_yticklabels(), color=TEXT_COLOR, fontsize=10)
ax.tick_params(colors=TEXT_COLOR, which="both")
for spine in ax.spines.values():
    spine.set_edgecolor(GRID_COLOR)

ax.set_xlabel("Distance from Kikar Zion (km)", color=TEXT_COLOR, fontsize=12, labelpad=10)
ax.set_ylabel("Density (per km²)",             color=TEXT_COLOR, fontsize=12, labelpad=10)

fig.text(0.45, 0.97, f"Jerusalem – Population vs Employment Density ({YEAR})",
         color=TEXT_COLOR, fontsize=17, fontweight="bold", ha="center", va="top")
fig.text(0.45, 0.91,
         "Radial Structure (0–16 km, 1 km bands)  ·  Left = Population  |  Right = Employment",
         color="#AAAAAA", fontsize=10, ha="center", va="top")

note = (
    "Methodology\n"
    "All Jerusalem areas (in_jeru=1).\n"
    "Population split by geometric\n"
    "intersection share per ring.\n"
    "Density denominator = full ring\n"
    "area (km²) for both sides.\n\n"
    f"Source: jer_areas, {YEAR} projections."
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
