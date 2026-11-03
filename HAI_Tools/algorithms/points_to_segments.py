# -*- coding: utf-8 -*-
"""
QGIS Processing Script: Pontos para segmentos com atributos

Cria um segmento independente entre cada par de pontos consecutivos,
agrupando por um ou mais campos e ordenando por um campo de sequencia.
Os atributos do ponto inicial sao preservados.

Compativel com QGIS baseado em Qt6, usando qgis.PyQt.
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterDistance,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsWkbTypes,
    QgsRuleBasedRenderer,
    QgsLineSymbol,
    QgsProcessingLayerPostProcessorInterface,
)


class PointsToAttributedSegments(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    GROUP_FIELDS = "GROUP_FIELDS"
    ORDER_FIELD = "ORDER_FIELD"
    GPS_FIELD = "GPS_FIELD"
    MAX_DISTANCE = "MAX_DISTANCE"
    STYLE_FIELD = "STYLE_FIELD"
    LINE_WIDTH = "LINE_WIDTH"
    OUTPUT = "OUTPUT"

    def tr(self, text):
        return QCoreApplication.translate("PointsToAttributedSegments", text)

    def createInstance(self):
        return PointsToAttributedSegments()

    def name(self):
        return "points_to_attributed_segments"

    def displayName(self):
        return self.tr("Pontos para segmentos com atributos")

    def group(self):
        return self.tr("Transectos")

    def groupId(self):
        return "transectos"

    def shortHelpString(self):
        return self.tr(
            "Cria um segmento entre cada par de pontos consecutivos. "
            "Os pontos sao separados pelos campos de agrupamento e ordenados "
            "pelo campo de sequencia. Cada segmento conserva todos os atributos "
            "do ponto inicial. O campo de distancia maxima permite impedir "
            "ligacoes anormalmente longas; use 0 para nao aplicar limite."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Camada de pontos"),
                [QgsProcessing.TypeVectorPoint],
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.GROUP_FIELDS,
                self.tr("Campos de agrupamento"),
                parentLayerParameterName=self.INPUT,
                allowMultiple=True,
                defaultValue=["Percurso", "Ano", "Epoca"],
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.ORDER_FIELD,
                self.tr("Campo de ordem/sequencia"),
                parentLayerParameterName=self.INPUT,
                allowMultiple=False,
                defaultValue="Seccao",
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.GPS_FIELD,
                self.tr("Campo identificador do ponto (opcional)"),
                parentLayerParameterName=self.INPUT,
                allowMultiple=False,
                defaultValue="GPS",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterDistance(
                self.MAX_DISTANCE,
                self.tr("Distancia maxima entre pontos; 0 = sem limite"),
                defaultValue=0.0,
                parentParameterName=self.INPUT,
                optional=False,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.STYLE_FIELD,
                self.tr("Campo HAI para simbologia (opcional)"),
                parentLayerParameterName=self.INPUT,
                allowMultiple=False,
                defaultValue="HAI",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.LINE_WIDTH,
                self.tr("Espessura da linha HAI em mm"),
                defaultValue="1.0",
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Segmentos"),
                QgsProcessing.TypeVectorLine,
            )
        )

    @staticmethod
    def _sort_value(value):
        if value is None:
            return (2, "")
        try:
            return (0, float(value))
        except (TypeError, ValueError):
            return (1, str(value))

    @staticmethod
    def _single_point(geometry):
        if geometry is None or geometry.isEmpty():
            return None

        if QgsWkbTypes.isMultiType(geometry.wkbType()):
            points = geometry.asMultiPoint()
            if not points:
                return None
            return QgsPointXY(points[0])

        return QgsPointXY(geometry.asPoint())

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.tr("Nao foi possivel abrir a camada de pontos."))

        group_fields = self.parameterAsFields(parameters, self.GROUP_FIELDS, context)
        order_field = self.parameterAsString(parameters, self.ORDER_FIELD, context)
        gps_field = self.parameterAsString(parameters, self.GPS_FIELD, context).strip()
        max_distance = self.parameterAsDouble(parameters, self.MAX_DISTANCE, context)
        style_field = self.parameterAsString(parameters, self.STYLE_FIELD, context).strip()
        try:
            line_width = float(self.parameterAsString(parameters, self.LINE_WIDTH, context))
        except (TypeError, ValueError):
            line_width = 1.0
        line_width = max(0.1, min(line_width, 10.0))

        if not group_fields:
            raise QgsProcessingException(self.tr("Selecione pelo menos um campo de agrupamento."))

        source_names = [field.name() for field in source.fields()]
        required = list(group_fields) + [order_field]
        missing = [name for name in required if name not in source_names]
        if missing:
            raise QgsProcessingException(
                self.tr("Campos em falta: {}".format(", ".join(missing)))
            )

        if gps_field and gps_field not in source_names:
            raise QgsProcessingException(self.tr("O campo identificador selecionado nao existe."))

        if style_field and style_field not in source_names:
            raise QgsProcessingException(self.tr("O campo de simbologia selecionado nao existe."))

        output_fields = QgsFields()
        for field in source.fields():
            output_fields.append(field)

        output_fields.append(QgsField("ord_inicio", QVariant.String, len=80))
        output_fields.append(QgsField("ord_fim", QVariant.String, len=80))
        output_fields.append(QgsField("id_inicio", QVariant.String, len=120))
        output_fields.append(QgsField("id_fim", QVariant.String, len=120))
        output_fields.append(QgsField("distancia", QVariant.Double, len=20, prec=3))

        sink, destination_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            output_fields,
            QgsWkbTypes.LineString,
            source.sourceCrs(),
        )

        if sink is None:
            raise QgsProcessingException(self.tr("Nao foi possivel criar a camada de saida."))

        groups = {}
        total = source.featureCount()
        step = 50.0 / total if total else 0.0

        for index, feature in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            key = tuple(feature[name] for name in group_fields)
            groups.setdefault(key, []).append(feature)
            feedback.setProgress(int(index * step))

        created = 0
        empty_geometries = 0
        zero_length = 0
        excessive_distance = 0
        group_count = len(groups)

        for group_index, (key, features) in enumerate(groups.items()):
            if feedback.isCanceled():
                break

            features.sort(key=lambda f: self._sort_value(f[order_field]))

            for position in range(len(features) - 1):
                current_feature = features[position]
                next_feature = features[position + 1]

                p1 = self._single_point(current_feature.geometry())
                p2 = self._single_point(next_feature.geometry())

                if p1 is None or p2 is None:
                    empty_geometries += 1
                    continue

                geometry = QgsGeometry.fromPolylineXY([p1, p2])
                distance = geometry.length()

                if distance == 0:
                    zero_length += 1
                    continue

                if max_distance > 0 and distance > max_distance:
                    excessive_distance += 1
                    continue

                output_feature = QgsFeature(output_fields)
                output_feature.setGeometry(geometry)

                order_start = current_feature[order_field]
                order_end = next_feature[order_field]
                id_start = current_feature[gps_field] if gps_field else ""
                id_end = next_feature[gps_field] if gps_field else ""

                attributes = list(current_feature.attributes())
                attributes.extend([
                    "" if order_start is None else str(order_start),
                    "" if order_end is None else str(order_end),
                    "" if id_start is None else str(id_start),
                    "" if id_end is None else str(id_end),
                    distance,
                ])

                output_feature.setAttributes(attributes)
                sink.addFeature(output_feature, QgsFeatureSink.FastInsert)
                created += 1

            if group_count:
                feedback.setProgress(50 + int(((group_index + 1) / group_count) * 50))

        feedback.pushInfo(self.tr("Pontos de entrada: {}".format(total)))
        feedback.pushInfo(self.tr("Grupos encontrados: {}".format(group_count)))
        feedback.pushInfo(self.tr("Segmentos criados: {}".format(created)))
        feedback.pushInfo(self.tr("Ignorados por geometria vazia: {}".format(empty_geometries)))
        feedback.pushInfo(self.tr("Ignorados por comprimento zero: {}".format(zero_length)))
        feedback.pushInfo(self.tr("Ignorados por distancia excessiva: {}".format(excessive_distance)))

        # Simbologia HAI por regras explicitas.
        # Garante cobertura dos limites e torna NULL visivel com a primeira cor amarela.
        if style_field:
            base_symbol = QgsLineSymbol.createSimple({
                "color": "#fff7bc",
                "width": str(line_width),
                "capstyle": "round",
                "joinstyle": "round",
            })
            renderer = QgsRuleBasedRenderer(base_symbol)
            root = renderer.rootRule()
            for child in list(root.children()):
                root.removeChild(child)

            field_expr = '"{}"'.format(style_field.replace('"', '""'))
            rules = [
                (f'{field_expr} IS NULL', "#fff7bc", "Sem HAI (NULL)"),
                (f'{field_expr} IS NOT NULL AND {field_expr} <= 0.05', "#fff7bc", "<= 0.05"),
                (f'{field_expr} > 0.05 AND {field_expr} <= 0.10', "#fee391", "0.05 - 0.10"),
                (f'{field_expr} > 0.10 AND {field_expr} <= 0.15', "#fec44f", "0.10 - 0.15"),
                (f'{field_expr} > 0.15 AND {field_expr} <= 0.20', "#fe9929", "0.15 - 0.20"),
                (f'{field_expr} > 0.20 AND {field_expr} <= 0.25', "#ec7014", "0.20 - 0.25"),
                (f'{field_expr} > 0.25 AND {field_expr} <= 0.30', "#cc4c02", "0.25 - 0.30"),
                (f'{field_expr} > 0.30', "#8c2d04", "> 0.30"),
            ]

            for expression, color, label in rules:
                symbol = QgsLineSymbol.createSimple({
                    "color": color,
                    "width": str(line_width),
                    "capstyle": "round",
                    "joinstyle": "round",
                })
                rule = QgsRuleBasedRenderer.Rule(symbol)
                rule.setFilterExpression(expression)
                rule.setLabel(label)
                root.appendChild(rule)

            context.layerToLoadOnCompletionDetails(destination_id).setPostProcessor(
                _StylePostProcessor.create(renderer)
            )
            feedback.pushInfo(self.tr("Simbologia HAI por regras preparada para: {}".format(style_field)))

        return {self.OUTPUT: destination_id}


class _StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    instance = None

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer

    @classmethod
    def create(cls, renderer):
        cls.instance = cls(renderer)
        return cls.instance

    def postProcessLayer(self, layer, context, feedback):
        layer.setRenderer(self.renderer.clone())
        layer.triggerRepaint()
