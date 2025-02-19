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
        print("[DEBUG] QGISRedIdentifyFeature initialized.")

    def setupConnections(self):
        print("[DEBUG] Setting up project connections...")
        project = QgsProject.instance()
        project.readProject.connect(self.deactivate)
        project.cleared.connect(self.deactivate)

    def canvasReleaseEvent(self, event):
        print(f"[DEBUG] canvasReleaseEvent triggered at x={event.x()}, y={event.y()}")
        identified_features = self.identify(event.x(), event.y(), self.TopDownStopAtFirst)

        if identified_features:
            identified_feature = identified_features[0]
            feature = identified_feature.mFeature
            layer = identified_feature.mLayer

            print("[DEBUG] Identified features found.")
            print(f"[DEBUG] Feature ID = {feature.id()}, geometry type = {feature.geometry().type() if feature.geometry() else None}")

            for lyr in QgsProject.instance().mapLayers().values():
                if isinstance(lyr, QgsVectorLayer):
                    lyr.removeSelection()
            layer.select(feature.id())

            self.clearHighlights()

            self.currentHighlight = QgsHighlight(self.canvas, feature.geometry(), layer)
            self.currentHighlight.setColor(Qt.red)
            self.currentHighlight.setWidth(4)
            self.currentHighlight.setFillColor(Qt.transparent)
            self.currentHighlight.show()
            print("[DEBUG] Highlight set for the identified feature.")

            # Get or create the dock
            print("[DEBUG] Retrieving QGISRedElementsPropertyDock instance...")
            self.dock = QGISRedElementsPropertyDock.getInstance(iface.mainWindow())
            if not self.dock.isVisible():
                iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
                print("[DEBUG] Dock was not visible, added to UI.")

            identifier = layer.customProperty("qgisred_identifier")
            print(f"[DEBUG] layer.customProperty('qgisred_identifier') = {identifier}")

            if not identifier:
                print("[DEBUG] No identifier found, falling back to default loadFeature.")
                self.dock.loadFeature(layer, feature)
            else:
                # Determine which handler and tabs to use based on the identifier.
                if identifier == 'qgisred_pipes':
                    tabs = ['tabData', 'tabResults', 'tabCurves', 'tabControls']
                    self.dock.handlePipes(layer, feature, tabs)
                elif identifier == 'qgisred_valves':
                    tabs = ['tabData', 'tabResults', 'tabCurves', 'tabControls']
                    self.dock.handleValves(layer, feature, tabs)
                elif identifier == 'qgisred_pumps':
                    tabs = ['tabData', 'tabResults', 'tabCurves', 'tabPatterns', 'tabControls']
                    self.dock.handlePumps(layer, feature, tabs)
                elif identifier == 'qgisred_junctions':
                    tabs = ['tabData', 'tabResults', 'tabPatterns', 'tabControls']
                    self.dock.handleJunctions(layer, feature, tabs)
                elif identifier == 'qgisred_tanks':
                    tabs = ['tabData', 'tabResults', 'tabCurves', 'tabPatterns', 'tabControls']
                    self.dock.handleTanks(layer, feature, tabs)
                elif identifier == 'qgisred_reservoirs':
                    tabs = ['tabData', 'tabResults', 'tabPatterns', 'tabControls']
                    self.dock.handleReservoirs(layer, feature, tabs)
                else:
                    # Fallback if the identifier does not match any known type.
                    print("[DEBUG] Unrecognized identifier, using generic loadFeature.")
                    self.dock.loadFeature(layer, feature)

            self.dock.show()
            self.dock.raise_()
            self.dock.activateWindow()
        else:
            print("[DEBUG] No features identified at the clicked location.")

    def keyReleaseEvent(self, e):
        print(f"[DEBUG] keyReleaseEvent triggered. Key = {e.key()}")
        if e.key() == Qt.Key_Escape:
            self.deactivate()

    def deactivate(self):
        print("[DEBUG] Deactivate called: unsetting map tool, clearing highlights, closing dock.")
        self.canvas.unsetMapTool(self.canvas.mapTool())
        self.clearHighlights()
        self.closeDock()
        self.disconnectProjectSignals()
        self.setActionUnchecked()

    def clearHighlights(self):
        if self.currentHighlight is not None:
            print("[DEBUG] Hiding current highlight.")
            self.currentHighlight.hide()
            self.currentHighlight = None

    def closeDock(self):
        if self.dock:
            print("[DEBUG] Closing the dock.")
            self.dock.close()

    def setActionUnchecked(self):
        if self.toggle_action:
            print("[DEBUG] Toggling action to unchecked.")
            self.toggle_action.setChecked(False)

    def disconnectProjectSignals(self):
        print("[DEBUG] Disconnecting project signals.")
        project = QgsProject.instance()
        try:
            project.readProject.disconnect(self.deactivate)
        except Exception as e:
            print(f"[DEBUG] Could not disconnect readProject signal: {e}")
        try:
            project.cleared.disconnect(self.deactivate)
        except Exception as e:
            print(f"[DEBUG] Could not disconnect cleared signal: {e}")
