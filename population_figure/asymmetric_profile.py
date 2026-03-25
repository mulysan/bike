#!/usr/bin/env python3
"""
asymmetric_profile.py
Left side = Jewish population density (Jewish + U. Orthodox)
Right side = Arab population density (Arab + arabs behind separation wall)

Each side uses its own sector footprint as the density denominator.
Year: 2025
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
OUT_PATH = os.path.join(HERE, "jerusalem_density_profile_jews_vs_arabs.png")

KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785
RING_WIDTH = 2_000
N_RINGS    = 8
MAX_DIST   = RING_WIDTH * N_RINGS
YEAR       = 2025
POP_COL    = f"pop_{YEAR}"

JEWISH_SECTORS = {"Jewish", "U. Orthodox"}
ARAB_SECTORS   = {"Arab", "arabs behined seperation wall"}

JEWISH_COLOR = "#00CFCF"   # cyan  (left)
ARAB_COLOR   = "#FF9933"   # orange (right)
BG_COLOR     = "#0d0d0d"
GRID_COLOR   = "#2a2a2a"
TEXT_COLOR   = "#FFFFFF"

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading jer_areas …")
all_areas = gpd.read_file(SHP_PATH)
all_areas = all_areas[all_areas["in_jeru"] == 1].copy()
all_areas["area_m2"] = all_areas.geometry.area
all_areas[POP_COL]   = all_areas[POP_COL].fillna(0)

jewish = all_areas[all_areas["sector"].isin(JEWISH_SECTORS)].copy()
arab   = all_areas[all_areas["sector"].isin(ARAB_SECTORS)].copy()
print(f"  Jewish: {len(jewish)}  Arab: {len(arab)}")

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
    """Density per ring using the sector's own footprint as denominator."""
    densities = []
    for g in ring_geoms:
        inter   = areas_df.geometry.intersection(g)
        foot_km2 = inter.area.sum() / 1e6
        frac    = inter.area / areas_df["area_m2"].replace(0, np.nan)
        pop_in  = (frac * areas_df[POP_COL]).fillna(0).sum()
        densities.append(pop_in / foot_km2 if foot_km2 > 0 else 0)
    buf16 = centre.buffer(MAX_DIST)
    frac16 = areas_df.geometry.intersection(buf16).area / areas_df["area_m2"].replace(0, np.nan)
    total  = (frac16 * areas_df[POP_COL]).fillna(0).sum()
    return densities, total


jewish_dens, jewish_total = sector_densities(jewish)
arab_dens,   arab_total   = sector_densities(arab)

print(f"\n  Jewish densities: {[f'{d:,.0f}' for d in jewish_dens]}")
print(f"  Arab   densities: {[f'{d:,.0f}' for d in arab_dens]}")
print(f"  Jewish total: {jewish_total:,.0f}   Arab total: {arab_total:,.0f}")

# ── Build asymmetric x / y ────────────────────────────────────────────────────
# Left  (negative x) = Jewish, reading outward from centre to left
# Right (positive x) = Arab,   reading outward from centre to right
rw = RING_WIDTH / 1000

def _side_spline(dens, sign, n=250):
    """Build a spline for one side (+1=right, -1=left) with gradual taper to zero."""
    last_nz = max((i for i, d in enumerate(dens) if d > 0), default=0)
    zero_x  = min((last_nz + 3) * rw, 16)
    xs = [(r + 0.5) * rw for r in range(last_nz + 1)] + [zero_x]
    ys = list(dens[:last_nz + 1]) + [0]
    xs = np.array(xs) * sign
    if sign < 0:
        xs, ys = xs[::-1], ys[::-1]
    pts = np.linspace(xs[0], xs[-1], n)
    return pts, np.clip(make_interp_spline(xs, ys, k=3)(pts), 0, None)

x_sl, y_sl = _side_spline(jewish_dens, sign=-1)
x_sr, y_sr = _side_spline(arab_dens,   sign=+1)

mask_left  = x_sl <= 0
mask_right = x_sr >= 0

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

# Left (Jewish) – cyan
ax.plot(x_sl, y_sl, color=JEWISH_COLOR, linewidth=2.5, zorder=3)
ax.fill_between(x_sl, y_sl, alpha=0.15, color=JEWISH_COLOR, zorder=2)

# Right (Arab) – orange
ax.plot(x_sr, y_sr, color=ARAB_COLOR, linewidth=2.5, zorder=3)
ax.fill_between(x_sr, y_sr, alpha=0.15, color=ARAB_COLOR, zorder=2)

# Centre divider
ax.axvline(0, color="#555555", linewidth=0.8, linestyle="--", zorder=4)

# Labels
ax.text(x_sl[int(np.argmax(y_sl))], y_sl.max() * 1.06,
        f"Jewish  {jewish_total/1e6:.2f}m",
        color=JEWISH_COLOR, fontsize=13, fontweight="bold", ha="center", va="bottom")
ax.text(x_sr[int(np.argmax(y_sr))], y_sr.max() * 1.06,
        f"Arab  {arab_total/1e6:.2f}m",
        color=ARAB_COLOR, fontsize=13, fontweight="bold", ha="center", va="bottom")

# Side labels
ax.text(-14, ax.get_ylim()[1] * 0.02 if ax.get_ylim()[1] > 0 else 200,
        "← Jewish", color=JEWISH_COLOR, fontsize=10, alpha=0.6, va="bottom")
ax.text( 14, ax.get_ylim()[1] * 0.02 if ax.get_ylim()[1] > 0 else 200,
        "Arab →",   color=ARAB_COLOR,   fontsize=10, alpha=0.6, va="bottom", ha="right")

# Grid & axes
ax.grid(color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
ax.set_axisbelow(True)
ax.set_xlim(-16, 16)
ax.set_ylim(0, max(y_sl.max(), y_sr.max()) * 1.28)

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

fig.text(0.45, 0.97, f"Jerusalem – Jewish vs Arab Density Profile ({YEAR})",
         color=TEXT_COLOR, fontsize=17, fontweight="bold", ha="center", va="top")
fig.text(0.45, 0.91, "Radial Population Structure (0–16 km, 2 km bands)  ·  Left = Jewish  |  Right = Arab",
         color="#AAAAAA", fontsize=10, ha="center", va="top")

note = (
    "Methodology\n"
    "Left: Jewish + U. Orthodox areas.\n"
    "Right: Arab + separation-wall areas.\n"
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
