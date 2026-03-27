#!/usr/bin/env python3
"""
density_by_sector_bar.py
Bar chart: average population density (p/km²) by sector group.
Groups: Haredi, Non-Haredi Jewish, Arab (within wall), Arab (behind wall).
Density = total group population / total group area footprint.
Year: 2025.
"""

import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

HERE     = os.path.dirname(os.path.abspath(__file__))
SHP_PATH = os.path.join(HERE, "..", "jer_areas.shp")
OUT_PATH = os.path.join(HERE, "jerusalem_density_by_sector_bar.png")

YEAR    = 2025
POP_COL = f"pop_{YEAR}"

BG_COLOR   = "#0d0d0d"
GRID_COLOR = "#2a2a2a"
TEXT_COLOR = "#FFFFFF"

GROUPS = [
    {"label": "Haredi\n(U. Orthodox)",    "sectors": {"U. Orthodox"},                       "color": "#A78BFA"},
    {"label": "Jewish\n(non-Haredi)",      "sectors": {"Jewish"},                             "color": "#00CFCF"},
    {"label": "Arab\n(within wall)",       "sectors": {"Arab"},                               "color": "#FF9933"},
    {"label": "Arab\n(behind wall)",       "sectors": {"arabs behined seperation wall"},      "color": "#FF4444"},
]

# ── Load ──────────────────────────────────────────────────────────────────────
areas = gpd.read_file(SHP_PATH)
areas = areas[areas["in_jeru"] == 1].copy()
areas["area_m2"] = areas.geometry.area
areas[POP_COL]   = areas[POP_COL].fillna(0)

# ── Compute density per group ─────────────────────────────────────────────────
labels, densities, colors, totals = [], [], [], []

for g in GROUPS:
    sub = areas[areas["sector"].isin(g["sectors"])]
    total_pop  = sub[POP_COL].sum()
    total_km2  = sub["area_m2"].sum() / 1e6
    density    = total_pop / total_km2 if total_km2 > 0 else 0
    labels.append(g["label"])
    densities.append(density)
    colors.append(g["color"])
    totals.append(total_pop)
    print(f"{g['label'].replace(chr(10),' '):30s}  pop={total_pop:>10,.0f}  area={total_km2:6.1f} km²  density={density:>8,.0f} p/km²")

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG_COLOR)
ax.set_facecolor(BG_COLOR)

x = np.arange(len(labels))
bars = ax.bar(x, densities, color=colors, width=0.55, zorder=3)

# Value labels above bars
for bar, d, total in zip(bars, densities, totals):
    ax.text(bar.get_x() + bar.get_width() / 2, d + max(densities) * 0.01,
            f"{d:,.0f}",
            color=TEXT_COLOR, fontsize=11, fontweight="bold",
            ha="center", va="bottom")
    ax.text(bar.get_x() + bar.get_width() / 2, d / 2,
            f"{total/1e3:.0f}k",
            color="black", fontsize=9, alpha=0.7,
            ha="center", va="center")

ax.set_xticks(x)
ax.set_xticklabels(labels, color=TEXT_COLOR, fontsize=11)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
plt.setp(ax.get_yticklabels(), color=TEXT_COLOR, fontsize=10)
ax.tick_params(colors=TEXT_COLOR, which="both")
for spine in ax.spines.values():
    spine.set_edgecolor(GRID_COLOR)

ax.grid(axis="y", color=GRID_COLOR, linewidth=0.6, linestyle="-", zorder=1)
ax.set_axisbelow(True)
ax.set_ylim(0, max(densities) * 1.20)

ax.set_ylabel("Average Density (People per km²)", color=TEXT_COLOR, fontsize=12, labelpad=10)

fig.text(0.5, 0.97, f"Jerusalem – Average Population Density by Sector ({YEAR})",
         color=TEXT_COLOR, fontsize=15, fontweight="bold", ha="center", va="top")
fig.text(0.5, 0.91, "Total group population ÷ total group area footprint",
         color="#AAAAAA", fontsize=10, ha="center", va="top")

plt.tight_layout(rect=[0, 0, 1, 0.89])
fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
plt.close(fig)
print(f"\nSaved → {OUT_PATH}")
