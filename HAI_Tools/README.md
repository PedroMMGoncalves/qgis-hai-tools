# HAI Tools

QGIS 4 Processing provider for monitoring transects and Human Activity Index (HAI) mapping.

## Version 0.1.0

Algorithms:

1. **Pontos para segmentos com atributos**
   - orders monitoring points along transects;
   - groups by `Percurso`, `Ano`, `Epoca` by default;
   - preserves point attributes on each segment;
   - applies HAI rule-based symbology when an HAI field is supplied;
   - default line width: 1.0 mm.

2. **HAI em blocos de 500 m - maximo entre epocas**
   - defaults to `Percurso`, `Ano`, `Epoca`, `Seccao`, `GPS`, `HAI`;
   - combines epochs for each route/year;
   - aggregates five consecutive 100 m links into a nominal 500 m block;
   - uses maximum available HAI within the block;
   - marks incomplete terminal blocks using `completo_500`;
   - applies fixed HAI classes automatically.

## Install

QGIS > Plugins > Manage and Install Plugins > Install from ZIP, then select `HAI_Tools_0.1.0.zip`.

After enabling the plugin, open the Processing Toolbox and look for **HAI Tools**.

## Important methodological note

The 500 m algorithm implements the current working interpretation of the PNOST map workflow: 500 m transect units and maximum HAI across campaign observations. The exact original HAI calculation formula is not implemented in v0.1.0 and should be verified against the source monitoring protocol before adding a Calculate HAI algorithm.
