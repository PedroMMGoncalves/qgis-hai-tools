# -*- coding: utf-8 -*-
"""QGIS Processing tool: HAI por blocos de 500 m.

Agrupa os registos por Percurso + Ano, combina as Epocas pelo valor maximo
de HAI e cria polilinhas formadas por 5 segmentos consecutivos de 100 m.
Aplica simbologia HAI por regras. Compativel com QGIS 4 / Qt6.
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsLineSymbol,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsRuleBasedRenderer,
    QgsWkbTypes,
)


class HAI500mAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    ROUTE_FIELD = "ROUTE_FIELD"
    YEAR_FIELD = "YEAR_FIELD"
    EPOCH_FIELD = "EPOCH_FIELD"
    ORDER_FIELD = "ORDER_FIELD"
    GPS_FIELD = "GPS_FIELD"
    HAI_FIELD = "HAI_FIELD"
    SECTIONS_PER_BLOCK = "SECTIONS_PER_BLOCK"
    LINE_WIDTH = "LINE_WIDTH"
    OUTPUT = "OUTPUT"

    def tr(self, text):
        return QCoreApplication.translate("HAI500mAlgorithm", text)

    def createInstance(self):
        return HAI500mAlgorithm()

    def name(self):
        return "hai_500m_max_epochs"

    def displayName(self):
        return self.tr("HAI em blocos de 500 m - maximo entre epocas")

    def group(self):
        return self.tr("Transectos")

    def groupId(self):
        return "transectos"

    def shortHelpString(self):
        return self.tr(
            "Reproduz a unidade cartografica do mapa HAI: combina as epocas "
            "pelo HAI maximo e agrega 5 segmentos consecutivos de 100 m num "
            "bloco de 500 m. Os blocos incompletos do fim do percurso podem "
            "ser mantidos e ficam identificados pelo campo completo_500."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, self.tr("Camada de pontos"), [QgsProcessing.TypeVectorPoint]
        ))
        self.addParameter(QgsProcessingParameterField(
            self.ROUTE_FIELD, self.tr("Campo do percurso"),
            parentLayerParameterName=self.INPUT, defaultValue="Percurso"
        ))
        self.addParameter(QgsProcessingParameterField(
            self.YEAR_FIELD, self.tr("Campo do ano"),
            parentLayerParameterName=self.INPUT, defaultValue="Ano"
        ))
        self.addParameter(QgsProcessingParameterField(
            self.EPOCH_FIELD, self.tr("Campo da epoca"),
            parentLayerParameterName=self.INPUT, defaultValue="Epoca"
        ))
        self.addParameter(QgsProcessingParameterField(
            self.ORDER_FIELD, self.tr("Campo de ordem/seccao"),
            parentLayerParameterName=self.INPUT, defaultValue="Seccao"
        ))
        self.addParameter(QgsProcessingParameterField(
            self.GPS_FIELD, self.tr("Campo identificador do ponto"),
            parentLayerParameterName=self.INPUT, defaultValue="GPS", optional=True
        ))
        self.addParameter(QgsProcessingParameterField(
            self.HAI_FIELD, self.tr("Campo HAI"),
            parentLayerParameterName=self.INPUT, defaultValue="HAI"
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.SECTIONS_PER_BLOCK,
            self.tr("Numero de segmentos de 100 m por bloco"),
            type=QgsProcessingParameterNumber.Integer,
            defaultValue=5, minValue=1, maxValue=100
        ))
        self.addParameter(QgsProcessingParameterString(
            self.LINE_WIDTH, self.tr("Espessura da linha em mm"),
            defaultValue="1.0"
        ))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, self.tr("HAI 500 m"), QgsProcessing.TypeVectorLine
        ))

    @staticmethod
    def _num(value):
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _point(geometry):
        if geometry is None or geometry.isEmpty():
            return None
        if QgsWkbTypes.isMultiType(geometry.wkbType()):
            pts = geometry.asMultiPoint()
            return QgsPointXY(pts[0]) if pts else None
        return QgsPointXY(geometry.asPoint())

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.tr("Nao foi possivel abrir a camada."))

        route_field = self.parameterAsString(parameters, self.ROUTE_FIELD, context)
        year_field = self.parameterAsString(parameters, self.YEAR_FIELD, context)
        epoch_field = self.parameterAsString(parameters, self.EPOCH_FIELD, context)
        order_field = self.parameterAsString(parameters, self.ORDER_FIELD, context)
        gps_field = self.parameterAsString(parameters, self.GPS_FIELD, context).strip()
        hai_field = self.parameterAsString(parameters, self.HAI_FIELD, context)
        sections_per_block = self.parameterAsInt(parameters, self.SECTIONS_PER_BLOCK, context)
        try:
            line_width = float(self.parameterAsString(parameters, self.LINE_WIDTH, context))
        except (TypeError, ValueError):
            line_width = 1.0
        line_width = max(0.1, min(line_width, 10.0))

        names = [f.name() for f in source.fields()]
        required = [route_field, year_field, epoch_field, order_field, hai_field]
        missing = [n for n in required if n not in names]
        if missing:
            raise QgsProcessingException(self.tr("Campos em falta: {}".format(", ".join(missing))))

        out_fields = QgsFields()
        out_fields.append(QgsField("Percurso", QVariant.String, len=160))
        out_fields.append(QgsField("Ano", QVariant.String, len=20))
        out_fields.append(QgsField("bloco_500", QVariant.Int))
        out_fields.append(QgsField("sec_inicio", QVariant.Double))
        out_fields.append(QgsField("sec_fim", QVariant.Double))
        out_fields.append(QgsField("gps_inicio", QVariant.String, len=120))
        out_fields.append(QgsField("gps_fim", QVariant.String, len=120))
        out_fields.append(QgsField("HAI", QVariant.Double, len=20, prec=6))
        out_fields.append(QgsField("n_segmentos", QVariant.Int))
        out_fields.append(QgsField("n_epocas", QVariant.Int))
        out_fields.append(QgsField("completo_500", QVariant.Bool))
        out_fields.append(QgsField("comprimento", QVariant.Double, len=20, prec=3))

        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT, context, out_fields,
            QgsWkbTypes.LineString, source.sourceCrs()
        )
        if sink is None:
            raise QgsProcessingException(self.tr("Nao foi possivel criar a saida."))

        # route-year -> order -> records from all epochs
        groups = {}
        total = source.featureCount()
        for i, feat in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            order = self._num(feat[order_field])
            point = self._point(feat.geometry())
            if order is None or point is None:
                continue
            key = (str(feat[route_field]), str(feat[year_field]))
            groups.setdefault(key, {}).setdefault(order, []).append({
                "point": point,
                "hai": self._num(feat[hai_field]),
                "epoch": str(feat[epoch_field]),
                "gps": str(feat[gps_field]) if gps_field else "",
            })
            if total:
                feedback.setProgress(int((i + 1) / total * 35))

        created = 0
        incomplete = 0
        null_hai = 0

        for gi, ((route, year), by_order) in enumerate(groups.items()):
            if feedback.isCanceled():
                break

            orders = sorted(by_order.keys())
            positions = []
            for order in orders:
                recs = by_order[order]
                # Coordinates should coincide between epochs; first record is representative.
                point = recs[0]["point"]
                gps = recs[0]["gps"]
                hai_values = [r["hai"] for r in recs if r["hai"] is not None]
                hai_max = max(hai_values) if hai_values else None
                epochs = {r["epoch"] for r in recs}
                positions.append({
                    "order": order, "point": point, "gps": gps,
                    "hai": hai_max, "epochs": epochs
                })

            # Five consecutive point-to-point links require six positions.
            segment_count = max(0, len(positions) - 1)
            block_no = 0
            for start_seg in range(0, segment_count, sections_per_block):
                end_seg = min(start_seg + sections_per_block, segment_count)
                pts = positions[start_seg:end_seg + 1]
                n_segments = end_seg - start_seg
                if len(pts) < 2:
                    continue

                complete = n_segments == sections_per_block
                if not complete:
                    incomplete += 1

                # HAI of a block = maximum of all source section values from all epochs.
                # Use the origin position of each segment, avoiding the next block's first section.
                block_hai_values = [p["hai"] for p in positions[start_seg:end_seg] if p["hai"] is not None]
                block_hai = max(block_hai_values) if block_hai_values else None
                if block_hai is None:
                    null_hai += 1

                block_no += 1
                geom = QgsGeometry.fromPolylineXY([p["point"] for p in pts])
                feat = QgsFeature(out_fields)
                feat.setGeometry(geom)
                all_epochs = set()
                for p in positions[start_seg:end_seg]:
                    all_epochs.update(p["epochs"])
                feat.setAttributes([
                    route,
                    year,
                    block_no,
                    pts[0]["order"],
                    pts[-1]["order"],
                    pts[0]["gps"],
                    pts[-1]["gps"],
                    block_hai,
                    n_segments,
                    len(all_epochs),
                    complete,
                    geom.length(),
                ])
                sink.addFeature(feat, QgsFeatureSink.FastInsert)
                created += 1

            if groups:
                feedback.setProgress(35 + int((gi + 1) / len(groups) * 65))

        renderer = self._renderer("HAI", line_width)
        context.layerToLoadOnCompletionDetails(dest_id).setPostProcessor(
            _HAIStylePostProcessor.create(renderer)
        )

        feedback.pushInfo(self.tr("Pontos de entrada: {}".format(total)))
        feedback.pushInfo(self.tr("Percursos-ano: {}".format(len(groups))))
        feedback.pushInfo(self.tr("Blocos criados: {}".format(created)))
        feedback.pushInfo(self.tr("Blocos incompletos no fim: {}".format(incomplete)))
        feedback.pushInfo(self.tr("Blocos sem HAI: {}".format(null_hai)))
        feedback.pushInfo(self.tr("Agregacao HAI: maximo entre todas as epocas do bloco."))

        return {self.OUTPUT: dest_id}

    @staticmethod
    def _renderer(field_name, width):
        base = QgsLineSymbol.createSimple({
            "color": "#ffffb2", "width": str(width),
            "capstyle": "round", "joinstyle": "round"
        })
        renderer = QgsRuleBasedRenderer(base)
        root = renderer.rootRule()
        for child in list(root.children()):
            root.removeChild(child)

        f = '"{}"'.format(field_name)
        rules = [
            (f"{f} IS NULL", "#ffffb2", "Sem HAI (NULL)"),
            (f"{f} IS NOT NULL AND {f} <= 0.05", "#ffffb2", "0 - 0.05"),
            (f"{f} > 0.05 AND {f} <= 0.10", "#fed976", "0.05 - 0.10"),
            (f"{f} > 0.10 AND {f} <= 0.15", "#feb24c", "0.10 - 0.15"),
            (f"{f} > 0.15 AND {f} <= 0.20", "#fd8d3c", "0.15 - 0.20"),
            (f"{f} > 0.20 AND {f} <= 0.25", "#f03b20", "0.20 - 0.25"),
            (f"{f} > 0.25 AND {f} <= 0.30", "#bd0026", "0.25 - 0.30"),
            (f"{f} > 0.30", "#800026", "> 0.30"),
        ]
        for expression, color, label in rules:
            symbol = QgsLineSymbol.createSimple({
                "color": color, "width": str(width),
                "capstyle": "round", "joinstyle": "round"
            })
            rule = QgsRuleBasedRenderer.Rule(symbol)
            rule.setFilterExpression(expression)
            rule.setLabel(label)
            root.appendChild(rule)
        return renderer


class _HAIStylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    instance = None

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer

    @classmethod
    def create(cls, renderer):
        cls.instance = cls(renderer)
        return cls.instance

    def postProcessLayer(self, layer, context, feedback):
        if layer is None or not layer.isValid():
            return
        layer.setName("HAI_500m_max_epocas")
        layer.setRenderer(self.renderer.clone())
        layer.triggerRepaint()
