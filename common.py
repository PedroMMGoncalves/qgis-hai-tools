from qgis.core import QgsLineSymbol, QgsRuleBasedRenderer, QgsProcessingLayerPostProcessorInterface

def hai_renderer(field, width=1.0):
    base = QgsLineSymbol.createSimple({'color':'#ffffb2','width':str(width),'capstyle':'round','joinstyle':'round'})
    renderer = QgsRuleBasedRenderer(base)
    root = renderer.rootRule()
    for child in list(root.children()): root.removeChild(child)
    f = '"{}"'.format(field.replace('"','""'))
    specs = [
        (f'{f} IS NULL','#ffffb2','Sem HAI (NULL)'),
        (f'{f} IS NOT NULL AND {f} <= 0.05','#ffffb2','0 - 0.05'),
        (f'{f} > 0.05 AND {f} <= 0.10','#fed976','0.05 - 0.10'),
        (f'{f} > 0.10 AND {f} <= 0.15','#feb24c','0.10 - 0.15'),
        (f'{f} > 0.15 AND {f} <= 0.20','#fd8d3c','0.15 - 0.20'),
        (f'{f} > 0.20 AND {f} <= 0.25','#f03b20','0.20 - 0.25'),
        (f'{f} > 0.25 AND {f} <= 0.30','#bd0026','0.25 - 0.30'),
        (f'{f} > 0.30','#800026','> 0.30')]
    for expr,color,label in specs:
        symbol=QgsLineSymbol.createSimple({'color':color,'width':str(width),'capstyle':'round','joinstyle':'round'})
        rule=QgsRuleBasedRenderer.Rule(symbol); rule.setFilterExpression(expr); rule.setLabel(label); root.appendChild(rule)
    return renderer

class StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    instance=None
    def __init__(self, renderer, name=None):
        super().__init__(); self.renderer=renderer; self.name=name
    @classmethod
    def create(cls, renderer, name=None):
        cls.instance=cls(renderer,name); return cls.instance
    def postProcessLayer(self, layer, context, feedback):
        if layer is None or not layer.isValid(): return
        if self.name: layer.setName(self.name)
        layer.setRenderer(self.renderer.clone()); layer.triggerRepaint()
