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
from shapely.geometry import Point
import os

HERE     = os.path.dirname(os.path.abspath(__file__))
SHP_PATH = os.path.join(HERE, "..", "jer_areas.shp")
OUT_PATH = os.path.join(HERE, "jerusalem_density_profile_pop_vs_emp.png")

KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785
RING_WIDTH = 2_000
N_RINGS    = 8
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

inter_fracs = [
    areas.geometry.intersection(g).area / areas["area_m2"].replace(0, np.nan)
    for g in ring_geoms
]
ring_areas_km2 = [g.area / 1e6 for g in ring_geoms]

inter_frac_16 = (
    areas.geometry.intersection(centre.buffer(MAX_DIST)).area
    / areas["area_m2"].replace(0, np.nan)
)

midpoints = np.array([(r + 0.5) * (RING_WIDTH / 1000) for r in range(N_RINGS)])


def ring_densities(col):
    vals = areas[col].fillna(0)
    dens = [(frac * vals).fillna(0).sum() / km2
            for frac, km2 in zip(inter_fracs, ring_areas_km2)]
    total = (inter_frac_16 * vals).fillna(0).sum()
    return dens, total


pop_dens, pop_total = ring_densities(f"pop_{YEAR}")
emp_dens, emp_total = ring_densities(f"emp_{YEAR}")

print(f"  Pop densities: {[f'{d:,.0f}' for d in pop_dens]}")
print(f"  Emp densities: {[f'{d:,.0f}' for d in emp_dens]}")
print(f"  Pop total: {pop_total:,.0f}   Emp total: {emp_total:,.0f}")

# ── Smooth curves ─────────────────────────────────────────────────────────────
# Left  (negative x) = population, outward from centre
# Right (positive x) = employment, outward from centre
x_left  = -midpoints[::-1]
x_right =  midpoints

rw = RING_WIDTH / 1000

def steps_left(dens):
    x, y = [], []
    for r in range(len(dens) - 1, -1, -1):
        x += [-(r + 1) * rw, -r * rw]
        y += [dens[r], dens[r]]
    return np.array(x), np.array(y)

def steps_right(dens):
    x, y = [], []
    for r in range(len(dens)):
        x += [r * rw, (r + 1) * rw]
        y += [dens[r], dens[r]]
    return np.array(x), np.array(y)

xl_pop, yl_pop = steps_left(pop_dens)
xr_emp, yr_emp = steps_right(emp_dens)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

ax.plot(xl_pop, yl_pop, color=POP_COLOR, linewidth=2.0, zorder=3)
ax.fill_between(xl_pop, yl_pop, alpha=0.15, color=POP_COLOR, zorder=2)

ax.plot(xr_emp, yr_emp, color=EMP_COLOR, linewidth=2.0, zorder=3)
ax.fill_between(xr_emp, yr_emp, alpha=0.15, color=EMP_COLOR, zorder=2)

ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--", zorder=4)

ax.text(-rw / 2, pop_dens[0] * 1.06,
        f"Population  {pop_total/1e6:.2f}m",
        color=POP_COLOR, fontsize=13, fontweight="bold", ha="center", va="bottom")
ax.text( rw / 2, emp_dens[0] * 1.06,
        f"Employment  {emp_total/1e3:.0f}k",
        color=EMP_COLOR, fontsize=13, fontweight="bold", ha="center", va="bottom")

# Grid & axes
ax.grid(color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
ax.set_axisbelow(True)
ax.set_xlim(-16, 16)
ax.set_ylim(0, max(yl_pop.max(), yr_emp.max()) * 1.28)

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
         "Radial Structure (0–16 km, 2 km bands)  ·  Left = Population  |  Right = Employment",
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
