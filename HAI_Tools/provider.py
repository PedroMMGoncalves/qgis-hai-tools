from qgis.core import QgsProcessingProvider
from .algorithms.points_to_segments import PointsToAttributedSegments
from .algorithms.hai_500m import HAI500mAlgorithm

class HAIToolsProvider(QgsProcessingProvider):
    def id(self):
        return "haitools"

    def name(self):
        return "HAI Tools"

    def longName(self):
        return self.name()

    def loadAlgorithms(self):
        self.addAlgorithm(PointsToAttributedSegments())
        self.addAlgorithm(HAI500mAlgorithm())
