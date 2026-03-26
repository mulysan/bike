#!/usr/bin/env python3
"""
density_profile.py
Radial population density profile for Jerusalem, centered on Kikar Zion.
Replicates the style of "European Density Profiles" (radial 1 km rings).

Generates one figure per year in YEARS.
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

# ── Fixed parameters ──────────────────────────────────────────────────────────
KIKAR_ZION_LON = 35.2232
KIKAR_ZION_LAT = 31.7785
RING_WIDTH = 1_000   # metres (1 km)
N_RINGS    = 16       # bands 0-1, 1-2, …, 15-16 km
MAX_DIST   = RING_WIDTH * N_RINGS   # 16 km
YEARS      = [2020, 2025, 2040]

# ── Style ─────────────────────────────────────────────────────────────────────
CITY_COLOR = "#FF6EC7"
BG_COLOR   = "#0d0d0d"
GRID_COLOR = "#2a2a2a"
TEXT_COLOR = "#FFFFFF"
FILL_ALPHA = 0.15

# ── Load shapefile once ───────────────────────────────────────────────────────
print("Loading jer_areas …")
_areas_raw = gpd.read_file(SHP_PATH)
_areas_raw = _areas_raw[_areas_raw["in_jeru"] == 1].copy()
_areas_raw["area_m2"] = _areas_raw.geometry.area

centre_wgs = gpd.GeoDataFrame(
    geometry=[Point(KIKAR_ZION_LON, KIKAR_ZION_LAT)], crs="EPSG:4326"
)
CENTRE = centre_wgs.to_crs(_areas_raw.crs).geometry.iloc[0]
print(f"  Kikar Zion (EPSG:2039): {CENTRE.x:.0f}, {CENTRE.y:.0f}")

MIDPOINTS = np.array([(r + 0.5) * (RING_WIDTH / 1000) for r in range(N_RINGS)])
BUF16     = CENTRE.buffer(MAX_DIST)

# Precompute ring geometries and intersection fractions (geometry is year-independent)
print("Pre-computing ring intersections …")
_ring_geoms = []
for r in range(N_RINGS):
    outer = CENTRE.buffer((r + 1) * RING_WIDTH)
    inner = CENTRE.buffer(r * RING_WIDTH) if r > 0 else None
    _ring_geoms.append(outer if inner is None else outer.difference(inner))

_inter_frac_rings = []   # one array per ring
for ring_geom in _ring_geoms:
    frac = (_areas_raw.geometry.intersection(ring_geom).area
            / _areas_raw["area_m2"].replace(0, np.nan))
    _inter_frac_rings.append(frac)

_inter_frac_16km = (_areas_raw.geometry.intersection(BUF16).area
                    / _areas_raw["area_m2"].replace(0, np.nan))


# ── Per-year computation and plotting ─────────────────────────────────────────
def compute_densities(pop_col):
    pop = _areas_raw[pop_col].fillna(0)
    densities = []
    for r, (ring_geom, frac) in enumerate(zip(_ring_geoms, _inter_frac_rings)):
        ring_area_km2 = ring_geom.area / 1e6
        pop_in_ring   = (frac * pop).fillna(0).sum()
        densities.append(pop_in_ring / ring_area_km2)
    total_pop = (_inter_frac_16km * pop).fillna(0).sum()
    return densities, total_pop


def make_figure(year):
    pop_col = f"pop_{year}"
    print(f"\n── {year} ──────────────────────────────────────")
    ring_densities, total_pop = compute_densities(pop_col)
    for r, d in enumerate(ring_densities):
        print(f"  Ring {r*2}-{r*2+2} km: {d:,.0f} p/km²")

    pop_label = f"{total_pop / 1e6:.2f}m"
    print(f"  Total within 16 km: {total_pop:,.0f}  → {pop_label}")

    rw = RING_WIDTH / 1000
    last_nz = max((i for i, d in enumerate(ring_densities) if d > 0), default=0)
    zero_x  = min((last_nz + 3) * rw, 16)   # 2 rings of taper beyond last non-zero
    x_r = [(r + 0.5) * rw for r in range(last_nz + 1)] + [zero_x]
    y_r = list(ring_densities[:last_nz + 1]) + [0]
    x   = np.array([-v for v in reversed(x_r)] + [0] + x_r)
    y   = np.array(list(reversed(y_r)) + [ring_densities[0]] + y_r)

    x_smooth = np.linspace(-16, 16, 500)
    y_smooth  = np.zeros(len(x_smooth))
    _ins = (x_smooth >= x[0]) & (x_smooth <= x[-1])
    y_smooth[_ins] = np.clip(make_interp_spline(x, y, k=3)(x_smooth[_ins]), 0, None)

    fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    ax.plot(x_smooth, y_smooth, color=CITY_COLOR, linewidth=2.5, zorder=3)
    ax.fill_between(x_smooth, y_smooth, alpha=FILL_ALPHA, color=CITY_COLOR, zorder=2)

    peak_i = int(np.argmax(y_smooth))
    ax.text(
        x_smooth[peak_i], y_smooth[peak_i] * 1.06,
        f"Jerusalem {pop_label}",
        color=CITY_COLOR, fontsize=14, fontweight="bold",
        ha="center", va="bottom",
    )

    ax.grid(color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
    ax.set_axisbelow(True)

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

    fig.text(0.45, 0.97, f"Jerusalem Density Profile – {year}",
             color=TEXT_COLOR, fontsize=18, fontweight="bold", ha="center", va="top")
    fig.text(0.45, 0.91, "Radial Population Structure (0–16 km, 1 km bands)",
             color="#AAAAAA", fontsize=11, ha="center", va="top")

    methodology = (
        "Methodology\n"
        "Population measured in 1 km radial rings\n"
        "from Kikar Zion (city centre), showing\n"
        "average density (people per km²) within\n"
        "each ring, not cumulative totals.\n\n"
        f"Source: jer_areas shapefile,\n"
        f"{year} population projections.\n\n"
        "All figures represent population within\n"
        "16 km of Kikar Zion."
    )
    fig.text(
        0.87, 0.93, methodology,
        color="#BBBBBB", fontsize=8, va="top", ha="left", linespacing=1.55,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a1a",
                  edgecolor="#444444", linewidth=0.8),
    )

    plt.tight_layout(rect=[0, 0, 0.85, 0.88])
    out = os.path.join(HERE, f"jerusalem_density_profile_{year}.png")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)
    print(f"  Saved → {out}")


# ── Run ───────────────────────────────────────────────────────────────────────
for yr in YEARS:
    make_figure(yr)
