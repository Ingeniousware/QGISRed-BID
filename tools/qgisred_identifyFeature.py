from ..ui.qgisred_elementsproperty_dock import QGISRedElementsPropertyDock
from qgis.gui import QgsMapToolIdentify, QgsHighlight
from qgis.utils import iface
from qgis.core import QgsProject, QgsVectorLayer
from PyQt5.QtCore import Qt

class QGISRedIdentifyFeature(QgsMapToolIdentify):
    def __init__(self, canvas, toggle_action=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.toggle_action = toggle_action
        self.currentHighlight = None
        self.dock = None
        self.setupConnections()

    def setupConnections(self):
        project = QgsProject.instance()
        # project.layersAdded.connect(self.onProjectChanged)
        # project.layersRemoved.connect(self.onProjectChanged)
        project.readProject.connect(self.deactivate)
        project.cleared.connect(self.deactivate)
    
    def canvasReleaseEvent(self, event):
        identified_features = self.identify(event.x(), event.y(), self.TopDownStopAtFirst)

        if identified_features:
            identified_feature = identified_features[0]
            feature = identified_feature.mFeature
            layer = identified_feature.mLayer

            print("feature:", feature)

            for lyr in QgsProject.instance().mapLayers().values():
                if isinstance(lyr, QgsVectorLayer):
                    lyr.removeSelection()

            layer.select(feature.id())

            if self.currentHighlight is not None:
                self.currentHighlight.hide()
                self.currentHighlight = None

            self.currentHighlight = QgsHighlight(self.canvas, feature.geometry(), layer)
            self.currentHighlight.setColor(Qt.red)
            self.currentHighlight.setWidth(4)
            self.currentHighlight.setFillColor(Qt.transparent)
            self.currentHighlight.show()

            self.dock = QGISRedElementsPropertyDock.getInstance(iface.mainWindow())

            if not self.dock.isVisible():
                iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

            self.dock.loadFeature(layer, feature)
            self.dock.show()
            self.dock.raise_()
            self.dock.activateWindow()

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.deactivate()

    def deactivate(self):
        self.canvas.unsetMapTool(self.canvas.mapTool())
        self.clearHighlights()
        self.closeDock()
        self.disconnectProjectSignals()
        self.setActionUnchecked()

    def clearHighlights(self):
        if self.currentHighlight is not None:
            self.currentHighlight.hide()
            self.currentHighlight = None

    def closeDock(self):
        if self.dock: 
            self.dock.close()
    
    def setActionUnchecked(self):
        if self.toggle_action:
            self.toggle_action.setChecked(False)

    def disconnectProjectSignals(self):
        project = QgsProject.instance()
        try:
            project.readProject.disconnect(self.deactivate)
        except Exception:
            pass
        try:
            project.cleared.disconnect(self.deactivate)
        except Exception:
            pass
