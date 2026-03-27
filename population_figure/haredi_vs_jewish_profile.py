#!/usr/bin/env python3
"""
haredi_vs_jewish_profile.py
Left side = Haredi (U. Orthodox) density
Right side = Non-Haredi Jewish density
Year: 2025. Each side uses its own sector footprint as density denominator.
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
OUT_PATH = os.path.join(HERE, "jerusalem_density_profile_haredi_vs_jewish.png")

KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785
RING_WIDTH = 1_000
N_RINGS    = 16
MAX_DIST   = RING_WIDTH * N_RINGS
YEAR       = 2025
POP_COL    = f"pop_{YEAR}"

HAREDI_COLOR  = "#A78BFA"   # purple (left)
JEWISH_COLOR  = "#00CFCF"   # cyan   (right)
BG_COLOR      = "#0d0d0d"
GRID_COLOR    = "#2a2a2a"
TEXT_COLOR    = "#FFFFFF"

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading jer_areas …")
all_areas = gpd.read_file(SHP_PATH)
all_areas = all_areas[all_areas["in_jeru"] == 1].copy()
all_areas["area_m2"] = all_areas.geometry.area
all_areas[POP_COL]   = all_areas[POP_COL].fillna(0)

haredi = all_areas[all_areas["sector"] == "U. Orthodox"].copy()
jewish = all_areas[all_areas["sector"] == "Jewish"].copy()
print(f"  Haredi: {len(haredi)}  Non-Haredi Jewish: {len(jewish)}")

centre = (
    gpd.GeoDataFrame(geometry=[Point(KIKAR_ZION_LON, KIKAR_ZION_LAT)], crs="EPSG:4326")
    .to_crs(all_areas.crs).geometry.iloc[0]
)

# ── Ring geometries ───────────────────────────────────────────────────────────
ring_geoms = []
for r in range(N_RINGS):
    outer = centre.buffer((r + 1) * RING_WIDTH)
    inner = centre.buffer(r * RING_WIDTH) if r > 0 else None
    ring_geoms.append(outer if inner is None else outer.difference(inner))

midpoints = np.array([(r + 0.5) * (RING_WIDTH / 1000) for r in range(N_RINGS)])


def sector_densities(areas_df):
    densities = []
    for g in ring_geoms:
        inter     = areas_df.geometry.intersection(g)
        foot_km2  = inter.area.sum() / 1e6
        frac      = inter.area / areas_df["area_m2"].replace(0, np.nan)
        pop_in    = (frac * areas_df[POP_COL]).fillna(0).sum()
        densities.append(pop_in / foot_km2 if foot_km2 > 0 else 0)
    buf16  = centre.buffer(MAX_DIST)
    frac16 = areas_df.geometry.intersection(buf16).area / areas_df["area_m2"].replace(0, np.nan)
    total  = (frac16 * areas_df[POP_COL]).fillna(0).sum()
    return densities, total


haredi_dens, haredi_total = sector_densities(haredi)
jewish_dens, jewish_total = sector_densities(jewish)

print(f"\n  Haredi densities:  {[f'{d:,.0f}' for d in haredi_dens]}")
print(f"  Jewish densities:  {[f'{d:,.0f}' for d in jewish_dens]}")
print(f"  Haredi total: {haredi_total:,.0f}   Jewish total: {jewish_total:,.0f}")

# ── Asymmetric curves – each side tapers independently ───────────────────────
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

xh, yh = _side_spline(haredi_dens, sign=-1)
xj, yj = _side_spline(jewish_dens, sign=+1)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

ax.plot(xh, yh, color=HAREDI_COLOR, linewidth=2.5, zorder=3)
ax.fill_between(xh, yh, alpha=0.15, color=HAREDI_COLOR, zorder=2)

ax.plot(xj, yj, color=JEWISH_COLOR, linewidth=2.5, zorder=3)
ax.fill_between(xj, yj, alpha=0.15, color=JEWISH_COLOR, zorder=2)

ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--", zorder=4)

ax.text(xh[int(np.argmax(yh))], yh.max() * 1.06,
        f"Haredi  {haredi_total/1e3:.0f}k",
        color=HAREDI_COLOR, fontsize=13, fontweight="bold", ha="center", va="bottom")
ax.text(xj[int(np.argmax(yj))], yj.max() * 1.06,
        f"Non-Haredi Jewish  {jewish_total/1e3:.0f}k",
        color=JEWISH_COLOR, fontsize=13, fontweight="bold", ha="center", va="bottom")

ax.grid(color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
ax.set_axisbelow(True)
ax.set_xlim(-16, 16)
ax.set_ylim(0, max(yh.max(), yj.max()) * 1.28)

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

fig.text(0.45, 0.97, f"Jerusalem – Haredi vs Non-Haredi Jewish Density Profile ({YEAR})",
         color=TEXT_COLOR, fontsize=16, fontweight="bold", ha="center", va="top")
fig.text(0.45, 0.91,
         "Radial Population Structure (0–16 km, 1 km bands)  ·  Left = Haredi  |  Right = Non-Haredi Jewish",
         color="#AAAAAA", fontsize=10, ha="center", va="top")

note = (
    "Methodology\n"
    "Left: U. Orthodox sector only.\n"
    "Right: Jewish sector only.\n"
    "Population split by geometric\n"
    "intersection share per ring.\n"
    "Density denominator = each sector's\n"
    "own footprint within the ring (km²).\n\n"
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
print(f"\nSaved → {OUT_PATH}")
