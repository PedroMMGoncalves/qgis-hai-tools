# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QCoreApplication,QVariant
from qgis.core import (QgsFeature,QgsFeatureSink,QgsField,QgsFields,QgsGeometry,QgsPointXY,QgsProcessing,QgsProcessingAlgorithm,QgsProcessingException,QgsProcessingParameterFeatureSink,QgsProcessingParameterFeatureSource,QgsProcessingParameterField,QgsProcessingParameterNumber,QgsProcessingParameterString,QgsWkbTypes)
from .common import hai_renderer,StylePostProcessor

class HAI500mAlgorithm(QgsProcessingAlgorithm):
    INPUT='INPUT'; ROUTE_FIELD='ROUTE_FIELD'; YEAR_FIELD='YEAR_FIELD'; EPOCH_FIELD='EPOCH_FIELD'; ORDER_FIELD='ORDER_FIELD'; GPS_FIELD='GPS_FIELD'; HAI_FIELD='HAI_FIELD'; SECTIONS_PER_BLOCK='SECTIONS_PER_BLOCK'; LINE_WIDTH='LINE_WIDTH'; OUTPUT='OUTPUT'
    def tr(self,t): return QCoreApplication.translate('HAI500mAlgorithm',t)
    def createInstance(self): return HAI500mAlgorithm()
    def name(self): return 'hai_500m_max_epochs'
    def displayName(self): return self.tr('HAI em blocos de 500 m - maximo entre epocas')
    def group(self): return self.tr('Transectos')
    def groupId(self): return 'transectos'
    def shortHelpString(self): return self.tr('Calcula a media do HAI das secoes por epoca em cada bloco e seleciona o maximo entre epocas.')
    def initAlgorithm(self,config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT,'Camada de pontos',[QgsProcessing.TypeVectorPoint]))
        for key,label,default,opt in [(self.ROUTE_FIELD,'Campo do percurso','Percurso',False),(self.YEAR_FIELD,'Campo do ano','Ano',False),(self.EPOCH_FIELD,'Campo da epoca','Epoca',False),(self.ORDER_FIELD,'Campo de ordem/seccao','Seccao',False),(self.GPS_FIELD,'Identificador do ponto','GPS',True),(self.HAI_FIELD,'Campo HAI','HAI',False)]: self.addParameter(QgsProcessingParameterField(key,label,parentLayerParameterName=self.INPUT,defaultValue=default,optional=opt))
        self.addParameter(QgsProcessingParameterNumber(self.SECTIONS_PER_BLOCK,'Segmentos de 100 m por bloco',QgsProcessingParameterNumber.Integer,5,minValue=1,maxValue=100))
        self.addParameter(QgsProcessingParameterString(self.LINE_WIDTH,'Espessura da linha em mm',defaultValue='1.0'))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT,'HAI 500 m',QgsProcessing.TypeVectorLine))
    @staticmethod
    def num(v):
        try:return float(str(v).replace(',','.'))
        except:return None
    def processAlgorithm(self,p,c,f):
        src=self.parameterAsSource(p,self.INPUT,c)
        if src is None: raise QgsProcessingException('Camada invalida.')
        rf=self.parameterAsString(p,self.ROUTE_FIELD,c); yf=self.parameterAsString(p,self.YEAR_FIELD,c); ef=self.parameterAsString(p,self.EPOCH_FIELD,c); of=self.parameterAsString(p,self.ORDER_FIELD,c); gf=self.parameterAsString(p,self.GPS_FIELD,c).strip(); hf=self.parameterAsString(p,self.HAI_FIELD,c); n=self.parameterAsInt(p,self.SECTIONS_PER_BLOCK,c)
        try: width=max(.1,min(float(self.parameterAsString(p,self.LINE_WIDTH,c)),10))
        except: width=1.0
        fields=QgsFields()
        for x in [QgsField('Percurso',QVariant.String,160),QgsField('Ano',QVariant.String,20),QgsField('bloco_500',QVariant.Int),QgsField('sec_inicio',QVariant.Double),QgsField('sec_fim',QVariant.Double),QgsField('gps_inicio',QVariant.String,120),QgsField('gps_fim',QVariant.String,120),QgsField('HAI',QVariant.Double,20,6),QgsField('n_segmentos',QVariant.Int),QgsField('n_epocas',QVariant.Int),QgsField('completo_500',QVariant.Bool),QgsField('comprimento',QVariant.Double,20,3)]: fields.append(x)
        sink,dest=self.parameterAsSink(p,self.OUTPUT,c,fields,QgsWkbTypes.LineString,src.sourceCrs())
        groups={}
        for feat in src.getFeatures():
            order=self.num(feat[of]); hai=self.num(feat[hf])
            if order is None or feat.geometry().isEmpty(): continue
            key=(str(feat[rf]),str(feat[yf])); groups.setdefault(key,{}).setdefault(order,[]).append({'point':QgsPointXY(feat.geometry().asPoint()),'epoch':str(feat[ef]),'hai':hai,'gps':str(feat[gf]) if gf else ''})
        made=0
        for (route,year),byorder in groups.items():
            orders=sorted(byorder); positions=[{'order':o,'point':byorder[o][0]['point'],'gps':byorder[o][0]['gps']} for o in orders]
            for block,start in enumerate(range(0,max(0,len(positions)-1),n),1):
                end=min(start+n,len(positions)-1); pts=positions[start:end+1]
                if len(pts)<2: continue
                epoch_values={}
                for pos in positions[start:end]:
                    for rec in byorder[pos['order']]:
                        if rec['hai'] is not None: epoch_values.setdefault(rec['epoch'],[]).append(rec['hai'])
                epoch_means={e:sum(v)/len(v) for e,v in epoch_values.items() if v}; block_hai=max(epoch_means.values()) if epoch_means else None
                geom=QgsGeometry.fromPolylineXY([x['point'] for x in pts]); out=QgsFeature(fields); out.setGeometry(geom); out.setAttributes([route,year,block,pts[0]['order'],pts[-1]['order'],pts[0]['gps'],pts[-1]['gps'],block_hai,end-start,len(epoch_means),(end-start)==n,geom.length()]); sink.addFeature(out,QgsFeatureSink.FastInsert); made+=1
        c.layerToLoadOnCompletionDetails(dest).setPostProcessor(StylePostProcessor.create(hai_renderer('HAI',width),'HAI_500m_max_epocas'))
        f.pushInfo('Blocos criados: {}'.format(made)); f.pushInfo('Agregacao: media por epoca, seguida do maximo entre epocas.'); return {self.OUTPUT:dest}
