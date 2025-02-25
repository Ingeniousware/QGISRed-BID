from ..ui.qgisred_elementproperties_dock import QGISRedElementsPropertyDock
from qgis.gui import QgsMapToolIdentify, QgsHighlight
from qgis.utils import iface
from qgis.core import QgsProject, QgsVectorLayer
from PyQt5.QtCore import Qt

class QGISRedIdentifyFeature(QgsMapToolIdentify):
    def __init__(self, canvas, toggle_action=None, useFindDock=False):
        super().__init__(canvas)
        self.canvas = canvas
        self.toggle_action = toggle_action
        self.useFindDock = useFindDock
        self.currentHighlight = None
        self.dock = None
        self.ignoreNextRelease = False
        self.setupConnections()

    # -----------------------
    # Helper Methods
    # -----------------------
    def getHandlers(self):
        return {
            'qgisred_meters': (['tabData', 'tabResults', 'tabCurves', 'tabControls'], 'handleMeters'),
            'qgisred_isolationvalves': (['tabData', 'tabResults', 'tabCurves', 'tabControls'], 'handleIsolationValves'),
            'qgisred_junctions': (['tabData', 'tabResults', 'tabPatterns', 'tabControls'], 'handleJunctions'),
            'qgisred_valves': (['tabData', 'tabResults', 'tabCurves', 'tabControls'], 'handleValves'),
            'qgisred_pumps': (['tabData', 'tabResults', 'tabCurves', 'tabPatterns', 'tabControls'], 'handlePumps'),
            'qgisred_tanks': (['tabData', 'tabResults', 'tabCurves', 'tabPatterns', 'tabControls'], 'handleTanks'),
            'qgisred_reservoirs': (['tabData', 'tabResults', 'tabPatterns', 'tabControls'], 'handleReservoirs'),
            'qgisred_pipes': (['tabData', 'tabResults', 'tabCurves', 'tabControls'], 'handlePipes'),
            'qgisred_serviceconnections': (['tabData', 'tabResults', 'tabCurves', 'tabControls'], 'handleServiceConnections')
        }

    def clearSelections(self):
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                lyr.removeSelection()

    def highlightFeature(self, layer, feature):
        self.clearHighlights()
        self.currentHighlight = QgsHighlight(self.canvas, feature.geometry(), layer)
        self.currentHighlight.setColor(Qt.red)
        self.currentHighlight.setWidth(4)
        self.currentHighlight.setFillColor(Qt.transparent)
        self.currentHighlight.show()

    def showFeatureInDock(self, layer, feature, handler=None):
        if self.useFindDock:
            print("use dockkk" )
            from ..ui.qgisred_findElements_dock import QGISRedFindElementsDock
            self.dock = QGISRedFindElementsDock.getInstance(self.canvas)
            self.dock.findFeature(layer, feature)
            return
        else:
            self.dock = QGISRedElementsPropertyDock.getInstance(self.canvas)
            if not self.dock.isVisible():
                iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            if self.dock.findElemetsdock:
                self.dock.findElemetsdock.findFeature(layer, feature)
            if handler:
                tabs, method_name = handler
                getattr(self.dock, method_name)(layer, feature, tabs)
            else:
                self.dock.loadFeature(layer, feature)
            self.dock.show()
            self.dock.raise_()
            self.dock.activateWindow()

    def selectFeature(self, layer, feature):
        layer.select(feature.id())

    def getFeatureByPriority(self, all_features):
        handlers = self.getHandlers()
        selected_feature = None
        selected_layer = None
        selected_handler = None

        for identifier_key, handler_data in handlers.items():
            for result in all_features:
                identifier = result.mLayer.customProperty("qgisred_identifier")
                if identifier == identifier_key:
                    selected_feature = result.mFeature
                    selected_layer = result.mLayer
                    selected_handler = handler_data
                    break
            if selected_handler:
                break

        if not selected_handler and all_features:
            top_result = all_features[0]
            selected_feature = top_result.mFeature
            selected_layer = top_result.mLayer

        return selected_layer, selected_feature, selected_handler

    def getSortedFeatures(self, all_features):
        handlers = self.getHandlers()
        sorted_results = []
        for result in all_features:
            identifier = result.mLayer.customProperty("qgisred_identifier")
            if identifier in handlers:
                priority = list(handlers.keys()).index(identifier)
            else:
                priority = len(handlers)
            sorted_results.append((priority, result))
        sorted_results.sort(key=lambda x: x[0])
        return sorted_results

    # -----------------------
    # Additional Methods
    # -----------------------
    def clearHighlights(self):
        if self.currentHighlight is not None:
            self.currentHighlight.hide()
            self.currentHighlight = None

    def closeDock(self):
        if self.dock:
            self.dock.close()

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

    def setActionUnchecked(self):
        if self.toggle_action:
            self.toggle_action.setChecked(False)

    def setupConnections(self):
        project = QgsProject.instance()
        project.readProject.connect(self.deactivate)
        project.cleared.connect(self.deactivate)

    # -----------------------
    # Event Handlers
    # -----------------------
    def canvasReleaseEvent(self, event):
        if self.ignoreNextRelease:
            self.ignoreNextRelease = False
            return

        all_features = self.identify(event.x(), event.y(), self.TopDownAll)
        if not all_features:
            return

        selected_layer, selected_feature, selected_handler = self.getFeatureByPriority(all_features)

        if self.useFindDock:
            print("true 1")
            self.showFeatureInDock(selected_layer, selected_feature, selected_handler)
            return
        
        self.clearSelections()
        self.selectFeature(selected_layer, selected_feature)
        self.highlightFeature(selected_layer, selected_feature)
        self.showFeatureInDock(selected_layer, selected_feature, selected_handler)

    def canvasDoubleClickEvent(self, event):
        self.ignoreNextRelease = True

        all_features = self.identify(event.x(), event.y(), self.TopDownAll)
        if not all_features:
            return

        sorted_results = self.getSortedFeatures(all_features)
        if len(sorted_results) < 2:
            self.canvasReleaseEvent(event)
            return

        second_result = sorted_results[1][1]
        selected_feature = second_result.mFeature
        selected_layer = second_result.mLayer

        handlers = self.getHandlers()
        identifier = selected_layer.customProperty("qgisred_identifier")
        selected_handler = handlers.get(identifier, None)

        if self.useFindDock:
            print("true 2")
            self.showFeatureInDock(selected_layer, selected_feature, selected_handler)
            return
    
        self.clearSelections()
        self.selectFeature(selected_layer, selected_feature)
        self.highlightFeature(selected_layer, selected_feature)
        self.showFeatureInDock(selected_layer, selected_feature, selected_handler)

    def deactivate(self):
        self.canvas.unsetMapTool(self.canvas.mapTool())
        self.clearHighlights()
        self.closeDock()
        self.disconnectProjectSignals()
        self.setActionUnchecked()

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.deactivate()
