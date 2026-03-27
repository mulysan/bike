# Jerusalem Bike Lane Analysis

An interactive web tool for prioritizing proposed bike lane investments in Jerusalem using a gravity-based accessibility model.

## Overview

The tool evaluates proposed ("wish list") bike lanes by measuring their contribution to city-wide accessibility — the potential for residents to reach jobs via cycling. A single self-contained HTML file (~5.5 MB) runs entirely in the browser with no server required.

## Features

### Select & Evaluate Lanes
- Toggle proposed (wish list) bike lanes on/off
- Compute accessibility improvement for any combination of lanes
- Rank all lanes by marginal contribution (additive or subtractive mode)

### Delete Existing Segments
- Click any existing lane segment (completed, under construction, planned, or checked) to open a popup with a **Delete** button
- Deleted segments are removed from the network for subsequent accessibility calculations
- Simulates infrastructure unavailability or maintenance closures

### Draw Custom Lanes
- Draw arbitrary bike lanes on the map
- Immediately evaluate their accessibility impact
- Export/import as GeoJSON

### Find Shortest Path
- Compute shortest cycling paths between statistical areas or arbitrary map points
- "Clear path" button resets both endpoints and the drawn route
- Path visualized with color coding: blue (bike lanes), orange (roads), pink (user-drawn lanes)

### Compute Accessibility
- Full gravity-model computation across all ~200 statistical areas
- Parameters: K (penalty for non-bike roads), θ (distance decay), year (2020–2040 projections)
- Results shown as total N and percentage improvement over baseline

### Area Changes Tab
- After computing accessibility, shows the top 20 statistical areas ranked by percentage improvement in origin accessibility
- Highlights where new infrastructure has the greatest local impact

### Rank Lanes
- **Additive mode**: rank proposed lanes by how much each would add
- **Subtractive mode**: rank existing/selected lanes by how much removing each would cost

## Accessibility Model

$$N = \sum_i \sum_j P_i \times E_j \times \tau_{ij}^{\theta}$$

- **P_i** = Population of area i
- **E_j** = Employment in area j
- **τ_ij** = Effective cycling distance (km), penalized by K for roads without bike lanes
- **θ** = Distance decay parameter (default −1.0)

Roads without bike lanes have their length multiplied by K (default 100), so cyclists strongly prefer bike infrastructure.

## Generating the HTML

```bash
python generate_interactive_map.py
# Output: bike_analysis.html
```

**Requirements:**
```
geopandas >= 0.14
shapely >= 2.0
networkx >= 3.0
scipy >= 1.11
pyproj >= 3.6
```

**Runtime:** ~3–5 minutes (network construction, virtual edge computation, HTML generation).

## Network Statistics

| Metric | Value |
|--------|-------|
| Road network nodes | 9,628 |
| Road network edges | 13,725 |
| Statistical areas | ~200 |
| Completed lane features (merged) | 109 |
| Under-construction features (merged) | 48 |
| Planned features (merged) | 178 |
| In-checking features (merged) | 41 |
| Node merge tolerance | 15 m |
| Segment snap distance | 20 m |

Bike lane segments within the same layer whose endpoints are within 20 m of each other are merged into single features before network construction (Union-Find + `shapely.linemerge`).

## Data Sources

| Data | Source |
|------|--------|
| Statistical areas, population, employment | Jerusalem Transportation Master Plan Team |
| Completed / construction / planned / checked bike lanes | Jerusalem Transportation Master Plan Team |
| Road network | OpenStreetMap |
| Wish list lanes | Author |

## Project Structure

```
bike/
├── generate_interactive_map.py   # Python generator (produces bike_analysis.html)
├── bike_analysis.html             # Generated single-file web app
├── data/                          # KML/GeoJSON input data
└── paper/
    └── ACADEMIC_PAPER.md          # Full methodology paper
```

## Methodology

See [`paper/ACADEMIC_PAPER.md`](paper/ACADEMIC_PAPER.md) for the full academic paper describing the gravity model, network construction, sensitivity analyses, and Jerusalem results.

The in-app **Methodology** button (top-right of the map) provides a concise summary.

## References

- Donaldson & Hornbeck (2016). Railroads and American economic growth. *QJE*, 131(2).
- Tsivanidis (2024). Evaluating Urban Transit Infrastructure: Bogotá's TransMilenio. *AER*, 116(2).
- Dijkstra (1959). A note on two problems in connexion with graphs. *Numerische Mathematik*, 1(1).
