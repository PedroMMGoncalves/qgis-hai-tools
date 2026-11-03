from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsFeatureSink,QgsProcessing,QgsProcessingAlgorithm,QgsProcessingException,QgsProcessingParameterFeatureSink,QgsProcessingParameterFeatureSource,QgsProcessingParameterField,QgsProcessingParameterString)
from .common import hai_renderer,StylePostProcessor
class ApplyHAISymbologyAlgorithm(QgsProcessingAlgorithm):
    INPUT='INPUT'; HAI_FIELD='HAI_FIELD'; LINE_WIDTH='LINE_WIDTH'; OUTPUT='OUTPUT'
    def tr(self,t): return QCoreApplication.translate('ApplyHAISymbologyAlgorithm',t)
    def createInstance(self): return ApplyHAISymbologyAlgorithm()
    def name(self): return 'apply_hai_symbology'
    def displayName(self): return self.tr('Aplicar simbologia HAI')
    def group(self): return self.tr('Simbologia')
    def groupId(self): return 'simbologia'
    def initAlgorithm(self,config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT,'Camada de linhas',[QgsProcessing.TypeVectorLine])); self.addParameter(QgsProcessingParameterField(self.HAI_FIELD,'Campo HAI',parentLayerParameterName=self.INPUT,defaultValue='HAI')); self.addParameter(QgsProcessingParameterString(self.LINE_WIDTH,'Espessura em mm',defaultValue='1.0')); self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT,'Linhas com simbologia HAI',QgsProcessing.TypeVectorLine))
    def processAlgorithm(self,p,c,f):
        src=self.parameterAsSource(p,self.INPUT,c); field=self.parameterAsString(p,self.HAI_FIELD,c)
        if src is None or field not in [x.name() for x in src.fields()]: raise QgsProcessingException('Camada ou campo HAI invalido.')
        try: width=max(.1,min(float(self.parameterAsString(p,self.LINE_WIDTH,c)),10))
        except: width=1.0
        sink,dest=self.parameterAsSink(p,self.OUTPUT,c,src.fields(),src.wkbType(),src.sourceCrs())
        for feat in src.getFeatures(): sink.addFeature(feat,QgsFeatureSink.FastInsert)
        c.layerToLoadOnCompletionDetails(dest).setPostProcessor(StylePostProcessor.create(hai_renderer(field,width))); return {self.OUTPUT:dest}
