from ..ui.qgisred_elementsData_dock import QGISRedElementsDataDock
from qgis.gui import QgsMapToolIdentify
from qgis.utils import iface
from PyQt5.QtCore import Qt

class QGISRedIdentifyFeature(QgsMapToolIdentify):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas

    def canvasReleaseEvent(self, event):
        identified_features = self.identify(event.x(), event.y(), self.TopDownStopAtFirst)

        if identified_features:
            feature = identified_features[0].mFeature
            layer = identified_features[0].mLayer

            print("feature : ", feature)

            dock = QGISRedElementsDataDock.getInstance(iface.mainWindow())

            if not dock.isVisible():
                iface.addDockWidget(Qt.RightDockWidgetArea, dock)

            dock.loadFeature(layer, feature)
            dock.show()
            dock.raise_()
            dock.activateWindow()

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.deactivate()

    def deactivate(self):
        self.canvas.unsetMapTool(self.canvas.mapTool())
