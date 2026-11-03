def classFactory(iface):
    from .plugin import HAIToolsPlugin
    return HAIToolsPlugin(iface)
