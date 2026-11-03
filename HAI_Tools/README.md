# HAI Tools v0.3.0
QGIS 4 Processing plugin with three tools:
1. Points to attributed segments.
2. HAI aggregation into nominal 500 m blocks.
3. Apply standard HAI symbology to line layers.

The 500 m tool calculates the mean of available 100 m section HAI values independently for each campaign, then selects the maximum campaign-level value. This remains a working methodological interpretation pending confirmation of the original HAI protocol.

Install using QGIS > Plugins > Manage and Install Plugins > Install from ZIP.
