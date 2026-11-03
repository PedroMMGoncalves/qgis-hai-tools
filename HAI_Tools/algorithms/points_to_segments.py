# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsFeature,QgsFeatureSink,QgsField,QgsFields,QgsGeometry,QgsPointXY,QgsProcessing,QgsProcessingAlgorithm,QgsProcessingException,QgsProcessingParameterDistance,QgsProcessingParameterFeatureSink,QgsProcessingParameterFeatureSource,QgsProcessingParameterField,QgsProcessingParameterString,QgsWkbTypes)
from .common import hai_renderer, StylePostProcessor

class PointsToAttributedSegments(QgsProcessingAlgorithm):
    INPUT='INPUT'; GROUP_FIELDS='GROUP_FIELDS'; ORDER_FIELD='ORDER_FIELD'; GPS_FIELD='GPS_FIELD'; MAX_DISTANCE='MAX_DISTANCE'; STYLE_FIELD='STYLE_FIELD'; LINE_WIDTH='LINE_WIDTH'; OUTPUT='OUTPUT'
    def tr(self,t): return QCoreApplication.translate('PointsToAttributedSegments',t)
    def createInstance(self): return PointsToAttributedSegments()
    def name(self): return 'points_to_attributed_segments'
    def displayName(self): return self.tr('Pontos para segmentos com atributos')
    def group(self): return self.tr('Transectos')
    def groupId(self): return 'transectos'
    def shortHelpString(self): return self.tr('Cria segmentos entre pontos consecutivos, preserva os atributos do ponto inicial e pode aplicar simbologia HAI.')
    def initAlgorithm(self,config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT,self.tr('Camada de pontos'),[QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterField(self.GROUP_FIELDS,self.tr('Campos de agrupamento'),parentLayerParameterName=self.INPUT,allowMultiple=True,defaultValue=['Percurso','Ano','Epoca']))
        self.addParameter(QgsProcessingParameterField(self.ORDER_FIELD,self.tr('Campo de ordem/sequencia'),parentLayerParameterName=self.INPUT,defaultValue='Seccao'))
        self.addParameter(QgsProcessingParameterField(self.GPS_FIELD,self.tr('Identificador do ponto (opcional)'),parentLayerParameterName=self.INPUT,defaultValue='GPS',optional=True))
        self.addParameter(QgsProcessingParameterDistance(self.MAX_DISTANCE,self.tr('Distancia maxima; 0 = sem limite'),defaultValue=0,parentParameterName=self.INPUT,minValue=0))
        self.addParameter(QgsProcessingParameterField(self.STYLE_FIELD,self.tr('Campo HAI para simbologia (opcional)'),parentLayerParameterName=self.INPUT,defaultValue='HAI',optional=True))
        self.addParameter(QgsProcessingParameterString(self.LINE_WIDTH,self.tr('Espessura da linha em mm'),defaultValue='1.0'))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT,self.tr('Segmentos'),QgsProcessing.TypeVectorLine))
    @staticmethod
    def sort_value(v):
        try:return (0,float(v))
        except:return (1,str(v))
    def processAlgorithm(self,p,c,f):
        src=self.parameterAsSource(p,self.INPUT,c)
        if src is None: raise QgsProcessingException('Camada invalida.')
        groupsf=self.parameterAsFields(p,self.GROUP_FIELDS,c); orderf=self.parameterAsString(p,self.ORDER_FIELD,c); gpsf=self.parameterAsString(p,self.GPS_FIELD,c).strip(); stylef=self.parameterAsString(p,self.STYLE_FIELD,c).strip(); maxd=self.parameterAsDouble(p,self.MAX_DISTANCE,c)
        try: width=max(.1,min(float(self.parameterAsString(p,self.LINE_WIDTH,c)),10))
        except: width=1.0
        names=[x.name() for x in src.fields()]; missing=[x for x in groupsf+[orderf] if x not in names]
        if missing: raise QgsProcessingException('Campos em falta: '+', '.join(missing))
        fields=QgsFields(); [fields.append(x) for x in src.fields()]
        for x in [QgsField('ord_inicio', QVariant.String, len=80),QgsField('ord_fim', QVariant.String, len=80),QgsField('id_inicio', QVariant.String, len=120),QgsField('id_fim', QVariant.String, len=120),QgsField('distancia', QVariant.Double, len=20, prec=3)]: fields.append(x)
        sink,dest=self.parameterAsSink(p,self.OUTPUT,c,fields,QgsWkbTypes.LineString,src.sourceCrs())
        groups={}
        for feat in src.getFeatures(): groups.setdefault(tuple(feat[x] for x in groupsf),[]).append(feat)
        made=skipped=0
        for feats in groups.values():
            feats.sort(key=lambda x:self.sort_value(x[orderf]))
            for a,b in zip(feats,feats[1:]):
                if a.geometry().isEmpty() or b.geometry().isEmpty(): skipped+=1; continue
                p1=QgsPointXY(a.geometry().asPoint()); p2=QgsPointXY(b.geometry().asPoint()); geom=QgsGeometry.fromPolylineXY([p1,p2]); d=geom.length()
                if d==0 or (maxd>0 and d>maxd): skipped+=1; continue
                out=QgsFeature(fields); out.setGeometry(geom); attrs=list(a.attributes()); attrs += [str(a[orderf]),str(b[orderf]),str(a[gpsf]) if gpsf else '',str(b[gpsf]) if gpsf else '',d]; out.setAttributes(attrs); sink.addFeature(out,QgsFeatureSink.FastInsert); made+=1
        if stylef and stylef in names: c.layerToLoadOnCompletionDetails(dest).setPostProcessor(StylePostProcessor.create(hai_renderer(stylef,width)))
        f.pushInfo('Segmentos criados: {}'.format(made)); f.pushInfo('Segmentos ignorados: {}'.format(skipped)); return {self.OUTPUT:dest}
