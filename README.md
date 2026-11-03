# HAI Tools for QGIS

**HAI Tools** is an open-source QGIS Processing plugin for preparing environmental monitoring transects and mapping the **Human Activity Index (HAI)**.

> **Status:** Experimental  
> **Version:** 0.2.0  
> **QGIS:** 4.x / Qt6

## Overview

Field monitoring datasets are often collected as point observations along transects, while analysis and cartographic representation require continuous or aggregated line segments.

HAI Tools provides a reproducible QGIS Processing workflow for:

- reconstructing transects from ordered monitoring points;
- preserving observation attributes on resulting line segments;
- visualizing existing HAI values;
- aggregating HAI observations into nominal 500 m transect units;
- combining repeated monitoring campaigns;
- applying consistent HAI cartographic classes.

The plugin was initially developed for biodiversity and human-pressure monitoring workflows based on transect observations in the Parque Natural Obo de Sao Tome (PNOST), Sao Tome and Principe.

## Tools

### 1. Points to Attributed Segments

Converts ordered point observations into individual line segments while preserving the attributes associated with the starting observation.

Default configuration:

| Parameter | Default field |
|---|---|
| Transect | `Percurso` |
| Year | `Ano` |
| Campaign | `Epoca` |
| Sequence | `Seccao` |
| Point identifier | `GPS` |
| HAI | `HAI` |

Points are grouped by `Percurso + Ano + Epoca` and ordered using `Seccao`. Each pair of consecutive points generates one attributed line segment.

### 2. HAI in 500 m Transect Blocks

Aggregates monitoring observations into nominal **500 m units**. The default workflow assumes observations approximately every 100 m and combines five consecutive point-to-point segments into one block.

Processing is performed by `Percurso + Ano`. Repeated campaigns (`Epoca`) are handled independently before the final cartographic value is selected.

Current workflow:

1. reconstruct the transect from ordered points;
2. create five-segment blocks;
3. calculate the arithmetic mean of the available section HAI values within each block and campaign;
4. select the maximum campaign-level value for the block;
5. create one polyline per block;
6. apply the predefined HAI symbology.

Terminal blocks with fewer than five segments are retained and flagged using `completo_500`.

> **Methodological note:** step 3 is currently a working implementation and remains to be verified against the original HAI calculation protocol. The plugin does not claim this is the authoritative HAI formula.

## HAI classification

| HAI | Class |
|---|---|
| 0.00-0.05 | Very low |
| >0.05-0.10 | Low |
| >0.10-0.15 | Moderate-low |
| >0.15-0.20 | Moderate |
| >0.20-0.25 | Moderate-high |
| >0.25-0.30 | High |
| >0.30 | Very high |

A sequential yellow-to-red scheme is applied automatically. NULL values use the first yellow colour for visual continuity but remain explicitly identified as NULL in the rule-based renderer. Default line width is **1.0 mm**.

## Installation

### Recommended: GitHub Release

1. Download the latest `HAI_Tools_*.zip` from **Releases**.
2. In QGIS, open **Plugins > Manage and Install Plugins > Install from ZIP**.
3. Select the downloaded ZIP.
4. Enable **HAI Tools**.
5. Open **Processing Toolbox > HAI Tools**.

No third-party Python packages are required.

### Development installation

Clone this repository and copy/link the `HAI_Tools` directory into the active QGIS profile plugin directory.

## Output attributes: 500 m tool

| Field | Description |
|---|---|
| `Percurso` | Transect identifier |
| `Ano` | Monitoring year |
| `bloco_500` | Sequential block number |
| `sec_inicio` | Initial section |
| `sec_fim` | Final section |
| `gps_inicio` | Initial monitoring point |
| `gps_fim` | Final monitoring point |
| `HAI` | HAI assigned to the mapped block |
| `n_segmentos` | Number of constituent segments |
| `n_epocas` | Number of campaigns represented |
| `completo_500` | Whether the nominal five-segment block is complete |
| `comprimento` | Geometric length of the resulting polyline |

## Methodological status

HAI Tools is under methodological validation. The plugin currently operates on an **existing HAI field**. It does not yet calculate HAI directly from raw human-activity observations.

The intended workflow is:

1. **Prepare Transects** - implemented
2. **Calculate HAI** - planned, pending verification of the original formula
3. **Aggregate HAI** - implemented
4. **Compare HAI** - planned

Future development may include interannual change analysis, campaign comparison, delta HAI mapping, batch processing and validation diagnostics.

## Repository structure

```text
qgis-hai-tools/
├── HAI_Tools/
│   ├── __init__.py
│   ├── plugin.py
│   ├── provider.py
│   ├── metadata.txt
│   └── algorithms/
│       ├── __init__.py
│       ├── points_to_segments.py
│       └── hai_500m.py
├── README.md
├── LICENSE
├── CITATION.cff
└── .gitignore
```

## Requirements

- QGIS 4.x
- Python 3
- Qt6
- QGIS Processing framework

Initially developed and tested against QGIS 4.2.x.

## Citation

If this software contributes to research, please cite the repository. A versioned DOI can be added later through Zenodo when a stable methodological release is available.

See `CITATION.cff` for machine-readable citation metadata.

## License

GNU General Public License v3.0. See `LICENSE`.

## Contributing

Issues, methodological corrections, test datasets and code improvements are welcome. Validation of the original HAI calculation methodology is a priority.

## Author

Pedro Goncalves

## Disclaimer

HAI Tools is experimental software under active development. Analytical results should be independently validated before use in scientific publication, conservation management or decision-making.
