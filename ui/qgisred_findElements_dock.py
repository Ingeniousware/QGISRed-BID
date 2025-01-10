# -*- coding: utf-8 -*-
import os
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtWidgets import QDockWidget, QMessageBox, QLineEdit
from qgis.PyQt import uic
from PyQt5.QtCore import Qt, QTimer
from qgis.PyQt.QtCore import pyqtSlot
from qgis.core import QgsProject, QgsGeometry, QgsPointXY, QgsRectangle, QgsVectorLayer, QgsSettings
from qgis.utils import iface
from qgis.gui import QgsHighlight

from ..tools.qgisred_utils import QGISRedUtils

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_findElements_dock.ui"))

class QGISRedFindElementsDock(QDockWidget, FORM_CLASS):
    _instance = None
    
    @classmethod
    def getInstance(cls, parent=None):
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance

    def __init__(self, parent=None):
        if QGISRedFindElementsDock._instance is not None:
            raise Exception("QGISRedFindElementsDock is a singleton! Use getInstance() instead.")
            
        super(QGISRedFindElementsDock, self).__init__(parent)
        self.setupUi(self)

        # Prevent stacking
        self.setObjectName("QGISRedFindElementsDock")
        
        # Dock widget is not floating by default
        self.setFloating(False)
        
        if parent:
            parent.addDockWidget(Qt.LeftDockWidgetArea, self)
        
        self.element_types = [
            "Reservoirs",
            "Tanks",
            "Junctions",
            "Pumps",
            "Valves",
            "Pipes",
            "Meters",
            "Service Connections",
            "Isolation Valves",
            "Sources"
        ]
        
        self.singular_forms = {
            "Reservoirs": "Reservoir",
            "Tanks": "Tank",
            "Junctions": "Junction",
            "Pumps": "Pump",
            "Valves": "Valve",
            "Pipes": "Pipe",
            "Meters": "Meter",
            "Service Connections": "Service Connection",
            "Isolation Valves": "Isolation Valve",
            "Sources": "Source"
        }

        self.layers_identifiers = {
            "Reservoirs": "qgisred_main_reservoirs",
            "Tanks": "qgisred_main_tanks",
            "Junctions": "qgisred_main_junctions",
            "Pumps": "qgisred_main_pumps",
            "Valves": "qgisred_main_valves",
            "Pipes": "qgisred_main_pipes",
            "Meters": "qgisred_main_meters",
            "Service Connections": "qgisred_main_serviceconnections",
            "Isolation Valves": "qgisred_main_isolationvalves",
            "Sources": "qgisred_main_sources",
            "Multiple Demands" : "qgisred_main_multipledemands"
        }

        
        self.original_ids = []
        self.adjacent_highlights = []
        self.main_highlight = None
        self.current_selected_highlight = None 

        self.link_layers = ["qgisred_main_pipes", "qgisred_main_serviceconnections", "qgisred_main_pumps", "qgisred_main_valves"]
        self.node_layers = ["qgisred_main_reservoirs", "qgisred_main_tanks", "qgisred_main_pumps", "qgisred_main_junctions", 
                            "qgisred_main_meters", "qgisred_main_isolationvalves", "qgisred_main_sources", "qgisred_main_multipledemands"]
        
        self.above_pipes_layers = ["Meters"]
        self.setDockStyle()
        
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.labelFoundElement.setFont(font)
        
        self.setupConnections()
        self.initializeCustomLayerProperties()
        self.initializeElementTypes()
        self.labelFoundElement.setText("")
        
        settings = QgsSettings()
        if settings.contains("QGISRed/FindElements/geometry"):
            self.restoreGeometry(settings.value("QGISRed/FindElements/geometry"))
    
    def getAvailableElementTypes(self):
        inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if not inputs_group:
            return []
        
        available_types = []

        checked_layers = inputs_group.checkedLayers()

        for identifier in self.layers_identifiers.values():
            for layer in checked_layers:
                if layer.customProperty("qgisred_identifier") == identifier:
                    available_types.append(layer.name())
                    break

        return available_types

    def setupConnections(self):
        self.cbElementType.currentIndexChanged.connect(self.updateElementIds)
        self.leElementMask.textChanged.connect(self.filterElementIds)
        self.btFind.clicked.connect(self.findElement)
        self.listWidget.itemClicked.connect(self.onListItemSingleClicked)
        self.listWidget.itemDoubleClicked.connect(self.onListItemDoubleClicked)
        self.btClear.clicked.connect(self.clearAll)
        QgsProject.instance().cleared.connect(self.clearAll)

        root = QgsProject.instance().layerTreeRoot()
        inputs_group = root.findGroup("Inputs")
        if inputs_group:
            inputs_group.addedChildren.connect(self.onLayerTreeChanged)
            inputs_group.removedChildren.connect(self.onLayerTreeChanged)
            for layer in inputs_group.findLayers():
                self.connectLayerSignals(layer.layer())

    def initializeElementTypes(self):
        self.cbElementType.clear()
        available_types = self.getAvailableElementTypes()
        self.cbElementType.addItems(available_types)
    
    def updateFoundElementLabel(self, selected_id):
        if not selected_id:
            self.labelFoundElement.setText("")
            return
            
        element_type = self.cbElementType.currentText()
        singular = self.singular_forms.get(element_type) or element_type
        self.labelFoundElement.setText(f"{singular} {selected_id}")

    def getLayerForElementType(self, element_type):
        project = QgsProject.instance()
        layer_name = element_type
        layers = project.mapLayersByName(layer_name)
        return layers[0] if layers else None
        
    @pyqtSlot()
    def updateElementIds(self):
        self.cbElementId.clear()
        self.original_ids.clear()
        self.labelFoundElement.setText("")

        layer = self.getLayerForElementType(self.cbElementType.currentText())
        if layer:
            for f in layer.getFeatures():
                id_val = self.getFeatureIdValue(f, layer)
                if id_val:
                    self.original_ids.append(id_val)

            self.original_ids = sorted(set(self.original_ids))

        if self.leElementMask.text():
            self.filterElementIds()
        else:
            self.cbElementId.addItem("")
            self.cbElementId.addItems(self.original_ids)
                
    @pyqtSlot()
    def filterElementIds(self):
        mask = self.leElementMask.text().strip()
        self.cbElementId.clear()
        
        if mask:
            filtered_items = [item for item in self.original_ids if mask.lower() in item.lower()]
        else:
            filtered_items = self.original_ids
            
        self.cbElementId.addItem("")
        self.cbElementId.addItems(filtered_items)
        
    def clearHighlights(self):
        if self.main_highlight:
            self.main_highlight.hide()
            self.main_highlight = None
        
        for h in self.adjacent_highlights:
            h.hide()
        self.adjacent_highlights.clear()
        
        if self.current_selected_highlight:
            self.current_selected_highlight.hide()
            self.current_selected_highlight = None
            
        canvas = iface.mapCanvas()
        scene = canvas.scene()
        for item in scene.items():
            if isinstance(item, QgsHighlight):
                item.hide()
                scene.removeItem(item)
                del item
                
        canvas.refresh()

    def setDockStyle(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFindElements.png')
        self.setWindowIcon(QIcon(icon_path))

        search_icon = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFilter.png'))
        self.leElementMask.addAction(search_icon, QLineEdit.LeadingPosition)

        self.cbElementType.setStyleSheet("QComboBox { background-color: white; }")
        self.cbElementId.setStyleSheet("QComboBox { background-color: white; }")
        
    def clearAllLayerSelections(self):
        # Only remove selection from vector layers
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                lyr.removeSelection()
        
    @pyqtSlot()
    def findElement(self):
        self.clearHighlights()
        self.clearAllLayerSelections()
        
        self.listWidget.clear()
        selected_type = self.cbElementType.currentText()
        selected_id = self.cbElementId.currentText()
        
        # If blank ID is selected, just clear everything and return
        if selected_id == "":
            self.labelFoundElement.setText("")
            return
            
        if not selected_id:
            QMessageBox.warning(self, "Warning", "Please select an element ID")
            return
            
        layer = self.getLayerForElementType(selected_type)
        if layer:
            found_feature = None
            for feature in layer.getFeatures():
                if self.getFeatureIdValue(feature, layer) == selected_id:
                    found_feature = feature
                    break

            if not found_feature:
                QMessageBox.information(self, "Info", "Feature not found")
                return

            singular = self.singular_forms.get(selected_type) or selected_type
            self.labelFoundElement.setText(f"{singular} {selected_id}")

            # Highlight main feature
            highlight = QgsHighlight(iface.mapCanvas(), found_feature.geometry(), layer)
            highlight.setColor(QColor("red"))
            highlight.setWidth(5)
            highlight.show()
            self.main_highlight = highlight
            HighlightManager(highlight)

            # Adjust map view
            self.adjustMapView(found_feature)

            # Select the feature
            layer.selectByIds([found_feature.id()])

            # Find adjacent elements
            if self.isLineElement(layer):
                self.findAdjacentNodesByGeometry(found_feature)
            else:
                self.findAdjacentLinksByGeometry(found_feature)

    def isLineElement(self, layer):
        return layer.customProperty("qgisred_identifier") in self.link_layers
    
    def areOverlappedPoints(self, point1, point2, tolerance=0.1):
        return point1.distance(point2) < tolerance

    def findAdjacentNodesByGeometry(self, line_feature):
        geom = line_feature.geometry()
        if geom.isMultipart():
            parts = geom.asMultiPolyline()
            line_points = parts[0] if parts else []
        else:
            line_points = geom.asPolyline()

        if not line_points:
            return

        first_point = QgsGeometry.fromPointXY(line_points[0])
        last_point = QgsGeometry.fromPointXY(line_points[-1])

        found_nodes = []
        node_map_layers = [
            layer
            for layer in self.getCheckedInputGroupLayers()
            if layer.customProperty("qgisred_identifier") in self.node_layers
        ]

        for node_layer in node_map_layers:
            if node_layer.geometryType() != 0:  # Not a point layer
                continue

            for f in node_layer.getFeatures():
                node_geom = f.geometry()
                if node_geom.isEmpty():
                    continue
                node_point = QgsGeometry.fromPointXY(QgsPointXY(node_geom.asPoint()))
                if (
                    self.areOverlappedPoints(first_point, node_point)
                    or self.areOverlappedPoints(last_point, node_point)
                ):
                    node_id = self.getFeatureIdValue(f, node_layer)
                    singular = self.singular_forms.get(node_layer.name()) or node_layer.name()
                    found_nodes.append((node_layer, f, f"{singular} {node_id}"))

        for node_layer, feature, node_info in found_nodes:
            self.listWidget.addItem(node_info)

    def findAdjacentLinksByGeometry(self, node_feature):
        node_geom = node_feature.geometry()
        if node_geom.isEmpty():
            return

        node_point = QgsPointXY(node_geom.asPoint())
        node_g = QgsGeometry.fromPointXY(node_point)

        tolerance = 1e-9
        found_links = []
        link_map_layers = [
            layer
            for layer in self.getCheckedInputGroupLayers()
            if layer.customProperty("qgisred_identifier") in self.link_layers
        ]

        for link_layer in link_map_layers:
            if link_layer.geometryType() != 1:  # Not a line layer
                continue

            for f in link_layer.getFeatures():
                link_geom = f.geometry()
                if link_geom.isMultipart():
                    parts = link_geom.asMultiPolyline()
                    line_points = parts[0] if parts else []
                else:
                    line_points = link_geom.asPolyline()

                if not line_points:
                    continue

                # Check if the node intersects with any part of the line
                if (
                    node_g.distance(link_geom) < tolerance
                    or self.areOverlappedPoints(node_g, QgsGeometry.fromPointXY(line_points[0]))
                    or self.areOverlappedPoints(node_g, QgsGeometry.fromPointXY(line_points[-1]))
                ):
                    link_id = self.getFeatureIdValue(f, link_layer)
                    singular = self.singular_forms.get(link_layer.name()) or link_layer.name()
                    found_links.append((link_layer, f, f"{singular} {link_id}"))

        for link_layer, feature, link_info in found_links:
            self.listWidget.addItem(link_info)

    def onListItemSingleClicked(self, item):
        if self.current_selected_highlight:
            self.current_selected_highlight.hide()
            self.current_selected_highlight = None

        text = item.text()
        parts = text.split(" ", 1)
        if len(parts) < 2:
            return

        singular_type = parts[0]
        selected_id = parts[1].strip()

        element_type = None
        for plural, singular in self.singular_forms.items():
            if singular == singular_type:
                element_type = plural
                break
        if not element_type:
            element_type = singular_type

        layer = self.getLayerForElementType(element_type)
        if layer:
            for feature in layer.getFeatures():
                if self.getFeatureIdValue(feature, layer) == selected_id:
                    highlight = QgsHighlight(iface.mapCanvas(), feature.geometry(), layer)
                    highlight.setColor(QColor("orange"))
                    highlight.setWidth(5)
                    highlight.show()
                    self.current_selected_highlight = highlight
                    HighlightManager(highlight)
                    break


    def getLayerIdField(self, layer):
        if not layer:
            return "Id"

        identifier = layer.customProperty("qgisred_identifier", "")
        if identifier in ["qgisred_main_sources", "qgisred_main_multipledemands"]:
            return "BaseValue"
        return "Id"
    
    def getFeatureIdValue(self, feature, layer):
        field_name = self.getLayerIdField(layer)
        value = feature.attribute(field_name)
        if value is None:
            return ""
        return str(value)
                         
    def onListItemDoubleClicked(self, item):
        # Clear the mask before refreshing the selection
        self.leElementMask.clear()
        
        text = item.text()
        parts = text.split(" ", 1)
        if len(parts) < 2:
            return

        singular_type = parts[0]  # e.g. "Junction"
        selected_id = parts[1].strip()

        element_type = None
        for plural, singular in self.singular_forms.items():
            if singular == singular_type:
                element_type = plural
                break

        if not element_type:
           element_type = singular_type

        self.cbElementType.setCurrentText(element_type)
        index = self.cbElementId.findText(selected_id)
        if index >= 0:
            self.cbElementId.setCurrentIndex(index)

        self.findElement()

    def closeEvent(self, event):
        root = QgsProject.instance().layerTreeRoot()
        inputs_group = root.findGroup("Inputs")
        if inputs_group:
            try:
                inputs_group.addedChildren.disconnect(self.onLayerTreeChanged)
                inputs_group.removedChildren.disconnect(self.onLayerTreeChanged)
                for layer in inputs_group.findLayers():
                    self.disconnectLayerSignals(layer.layer())
            except:
                pass
                
        settings = QgsSettings()
        settings.setValue("QGISRed/FindElements/geometry", self.saveGeometry())
        
        self.clearHighlights()
        self.clearAllLayerSelections()
        
        QGISRedFindElementsDock._instance = None
        
        super(QGISRedFindElementsDock, self).closeEvent(event)

    def adjustMapView(self, feature):
        canvas = iface.mapCanvas()
        current_extent = canvas.extent()
        geom = feature.geometry()
        feature_extent = geom.boundingBox()

        map_width = current_extent.width()
        map_height = current_extent.height()
        feat_width = feature_extent.width()
        feat_height = feature_extent.height()

        is_point = (feat_width == 0 and feat_height == 0)

        feat_largest_dim = max(feat_width, feat_height)
        map_largest_dim = max(map_width, map_height)
        ratio = feat_largest_dim / map_largest_dim if map_largest_dim != 0 else 1

        center_x = feature_extent.center().x()
        center_y = feature_extent.center().y()

        new_extent = QgsRectangle(current_extent)

        # Zoom logic (skip if point)
        if not is_point:
            # If ratio > 0.25 -> feature too big, zoom out
            if ratio > 0.25:
                factor = ratio / 0.25
                new_width = map_width * factor
                new_height = map_height * factor
                new_extent = self.recenterExtent(new_width, new_height, center_x, center_y)
            # If ratio < 0.05 -> feature too small, zoom in
            elif ratio < 0.05:
                factor = 0.05 / ratio
                new_width = map_width / factor
                new_height = map_height / factor
                new_extent = self.recenterExtent(new_width, new_height, center_x, center_y)
            else:
                # No zoom change
                new_extent = QgsRectangle(current_extent)
        else:
            # If point, no zoom adjustment
            new_extent = QgsRectangle(current_extent)

        new_extent = self.applyMinimalPan(new_extent, feature_extent)

        canvas.setExtent(new_extent)
        canvas.refresh()

    def recenterExtent(self, new_width, new_height, center_x, center_y):
        half_w = new_width / 2.0
        half_h = new_height / 2.0
        return QgsRectangle(center_x - half_w, center_y - half_h, center_x + half_w, center_y + half_h)

    def applyMinimalPan(self, current_extent, feature_extent):
        margin_x = current_extent.width() * 0.1
        margin_y = current_extent.height() * 0.1

        # Distances from feature to map edges
        left_dist = feature_extent.xMinimum() - current_extent.xMinimum()
        right_dist = current_extent.xMaximum() - feature_extent.xMaximum()
        top_dist = current_extent.yMaximum() - feature_extent.yMaximum()
        bottom_dist = feature_extent.yMinimum() - current_extent.yMinimum()

        new_extent = QgsRectangle(current_extent)

        # Horizontal panning
        if left_dist < margin_x:
            shift = margin_x - left_dist
            new_extent.setXMinimum(new_extent.xMinimum() - shift)
            new_extent.setXMaximum(new_extent.xMaximum() - shift)

        if right_dist < margin_x:
            shift = margin_x - right_dist
            new_extent.setXMinimum(new_extent.xMinimum() + shift)
            new_extent.setXMaximum(new_extent.xMaximum() + shift)

        # Vertical panning
        if top_dist < margin_y:
            shift = margin_y - top_dist
            new_extent.setYMinimum(new_extent.yMinimum() + shift)
            new_extent.setYMaximum(new_extent.yMaximum() + shift)

        if bottom_dist < margin_y:
            shift = margin_y - bottom_dist
            new_extent.setYMinimum(new_extent.yMinimum() - shift)
            new_extent.setYMaximum(new_extent.yMaximum() - shift)

        return new_extent

    def onProjectClosed(self):
        self.clearHighlights()
        self.clearAllLayerSelections()

    @pyqtSlot()
    def clearAll(self):
        self.clearHighlights()
        self.clearAllLayerSelections()
        self.leElementMask.clear()
        self.cbElementId.setCurrentIndex(0)
        self.labelFoundElement.setText("")  
        self.listWidget.clear()  
    
    def onLayerTreeChanged(self):
        current_type = self.cbElementType.currentText()
        current_id = self.cbElementId.currentText()
        
        # Refresh element types
        self.initializeCustomLayerProperties()
        self.initializeElementTypes()
        # Try to restore previous selection
        type_index = self.cbElementType.findText(current_type)
        if type_index >= 0:
            self.cbElementType.setCurrentIndex(type_index)
            id_index = self.cbElementId.findText(current_id)
            if id_index >= 0:
                self.cbElementId.setCurrentIndex(id_index)

    def connectLayerSignals(self, layer_node):
        try:
            layer_node.nameChanged.connect(self.onLayerTreeChanged)
            if layer_node.layer():
                layer_node.layer().dataChanged.connect(self.onLayerTreeChanged)
        except:
            pass

    def disconnectLayerNodeSignals(self, layer_node):
        try:
            layer_node.nameChanged.disconnect(self.onLayerTreeChanged)
            if layer_node.layer():
                layer_node.layer().dataChanged.disconnect(self.onLayerTreeChanged)
        except:
            pass

    def getCheckedInputGroupLayers(self):
        input_layers = []
        inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        
        if inputs_group:
            input_layers = inputs_group.checkedLayers()
        
        return input_layers

    # def initializeCustomLayerProperties(self):
    #     inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
    #     if not inputs_group:
    #         return
            
    #     for layer in inputs_group.findLayers():
    #         layer_name = layer.name()
    #         for element_type, identifier in self.layers_identifiers.items():
    #             if layer_name == element_type:
    #                 layer_obj = layer.layer()
    #                 if not layer_obj.customProperty("qgisred_identifier"):
    #                     layer_obj.setCustomProperty("qgisred_identifier", identifier)
    def initializeCustomLayerProperties(self):
        print("Initializing custom layer properties...")
        inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if not inputs_group:
            print("No 'Inputs' group found in the project.")
            return
            
        print("Found 'Inputs' group. Iterating through its layers...")
        for layer in inputs_group.findLayers():
            layer_name = layer.name()
            print(f"Checking layer: {layer_name}")
            for element_type, identifier in self.layers_identifiers.items():
                print(f"Matching with element_type: {element_type}, identifier: {identifier}")
                if layer_name == element_type:
                    print(f"Layer name matches element_type: {element_type}")
                    layer_obj = layer.layer()
                    custom_property = layer_obj.customProperty("qgisred_identifier", None)
                    print(f"Current custom property 'qgisred_identifier': {custom_property}")
                    if not custom_property:
                        print(f"Setting custom property 'qgisred_identifier' to: {identifier}")
                        layer_obj.setCustomProperty("qgisred_identifier", identifier)
                    else:
                        print(f"Custom property already set to: {custom_property}")

class HighlightManager:
    def __init__(self, highlight, duration_ms=5000):
        self.highlight = highlight
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.clear_highlight)
        self.timer.start(duration_ms)
    
    def clear_highlight(self):
        if self.highlight:
            self.highlight.hide()
            self.highlight = None
        self.timer.stop()