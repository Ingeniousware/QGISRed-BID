# -*- coding: utf-8 -*-
import os
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtWidgets import QDockWidget, QMessageBox, QLineEdit
from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSlot
from qgis.core import QgsProject, QgsGeometry, QgsPointXY
from qgis.utils import iface
from qgis.gui import QgsHighlight

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_findElements_dock.ui"))

class QGISRedFindElementsDock(QDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        super(QGISRedFindElementsDock, self).__init__(parent)
        self.setupUi(self)
        self.setDockStyle()
        
        self.element_types = [
            "Reservoirs",
            "Tanks",
            "Junctions",
            "Pumps",
            "Valves",
            "Pipes",
            "Meters",
            "Service Connections",
            "Isolation Valves"
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
            "Isolation Valves": "Isolation Valve"
        }
        
        self.original_ids = []
        self.adjacent_highlights = []
        self.main_highlight = None
        
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.labelFoundElement.setFont(font)
        
        self.setupConnections()
        self.initializeElementTypes()
        self.labelFoundElement.setText("")
        
        # Set window title for the dock
        self.setWindowTitle("Find Elements")
        
    def getAvailableElementTypes(self):
        inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if not inputs_group:
            return []
        
        available_types = []
        for element_type in self.element_types:
            for child in inputs_group.children():
                if child.name() == element_type:
                    available_types.append(element_type)
                    break
        return available_types
        
    def setupConnections(self):
        self.cbElementType.currentIndexChanged.connect(self.updateElementIds)
        self.leElementMask.textChanged.connect(self.filterElementIds)
        self.btFind.clicked.connect(self.findElement)
        self.listWidget.itemClicked.connect(self.onListItemClicked)
        
    def initializeElementTypes(self):
        self.cbElementType.clear()
        available_types = self.getAvailableElementTypes()
        self.cbElementType.addItems(available_types)
    
    def updateFoundElementLabel(self, selected_id):
        if not selected_id:
            self.labelFoundElement.setText("")
            return
            
        element_type = self.cbElementType.currentText()
        singular = self.singular_forms.get(element_type, element_type)
        self.labelFoundElement.setText(f"{singular} {selected_id}")

    def getLayerForElementType(self, element_type):
        project = QgsProject.instance()
        layer_name = element_type  # layer name == element_type
        layers = project.mapLayersByName(layer_name)
        return layers[0] if layers else None
        
    @pyqtSlot()
    def updateElementIds(self):
        self.cbElementId.clear()
        self.original_ids.clear()
        self.labelFoundElement.setText("")
        
        layer = self.getLayerForElementType(self.cbElementType.currentText())
        if layer:
            self.original_ids = sorted([str(f.attribute("Id")) for f in layer.getFeatures() if f.attribute("Id") is not None])
        
        if self.leElementMask.text():
            self.filterElementIds()
        else:
            self.cbElementId.addItems(self.original_ids)
                
    @pyqtSlot()
    def filterElementIds(self):
        mask = self.leElementMask.text().strip()
        self.cbElementId.clear()
        
        if mask:
            filtered_items = [item for item in self.original_ids if mask.lower() in item.lower()]
        else:
            filtered_items = self.original_ids
            
        self.cbElementId.addItems(filtered_items)
        
    def clearHighlights(self):
        # Clear main highlight
        if self.main_highlight:
            self.main_highlight.hide()
            self.main_highlight = None
        
        # Clear adjacent highlights
        for h in self.adjacent_highlights:
            h.hide()
        self.adjacent_highlights.clear()
        
    def clearAllLayerSelections(self):
        # Clear all selections from all layers
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr is not None:
                lyr.removeSelection()
        
    @pyqtSlot()
    def findElement(self):
        # Clear previous highlights and selections before new search
        self.clearHighlights()
        self.clearAllLayerSelections()
        
        self.listWidget.clear()
        selected_type = self.cbElementType.currentText()
        selected_id = self.cbElementId.currentText()
        
        if not selected_id:
            QMessageBox.warning(self, "Warning", "Please select an element ID")
            return
            
        layer = self.getLayerForElementType(selected_type)
        if layer:
            found_feature = None
            for feature in layer.getFeatures():
                if str(feature.attribute("Id")) == selected_id:
                    found_feature = feature
                    # Zoom to feature
                    iface.mapCanvas().zoomToFeatureIds(layer, [feature.id()])
                    # Select it on the layer (optional if you also highlight)
                    layer.selectByIds([feature.id()])
                    
                    singular = self.singular_forms.get(selected_type, selected_type)
                    self.labelFoundElement.setText(f"{singular} {selected_id}")
                    
                    # Highlight the main element in a custom color
                    self.main_highlight = QgsHighlight(iface.mapCanvas(), found_feature.geometry(), layer)
                    self.main_highlight.setColor(QColor("red"))  # main element highlight color
                    self.main_highlight.setWidth(5)
                    self.main_highlight.show()
                    
                    # Determine adjacency type
                    if self.isLineElement(selected_type):
                        self.labelAdjacentNodeLinks.setText("Adjacent Nodes")
                        self.findAdjacentNodesByGeometry(found_feature)
                    else:
                        self.labelAdjacentNodeLinks.setText("Adjacent Links")
                        self.findAdjacentLinksByGeometry(found_feature)
                    break

    def isLineElement(self, element_type):
        return element_type in ["Pipes", "Service Connections", "Pumps"]
      
    def setDockStyle(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFindElements.png')
        self.setWindowIcon(QIcon(icon_path))

        search_icon = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFilter.png'))
        self.leElementMask.addAction(search_icon, QLineEdit.LeadingPosition)

        # Set white background for dropdowns
        self.cbElementType.setStyleSheet("QComboBox { background-color: white; }")
        self.cbElementId.setStyleSheet("QComboBox { background-color: white; }")

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

        node_layers = ["Reservoirs", "Tanks", "Junctions", "Pumps", "Valves", "Meters", "Service Connections", "Isolation Valves"]
        project = QgsProject.instance()

        found_nodes = []
        for node_layer_name in node_layers:
            layers = project.mapLayersByName(node_layer_name)
            if not layers:
                continue
            node_layer = layers[0]

            if node_layer.geometryType() != 0:
                continue

            node_id_field = "Id"
            for f in node_layer.getFeatures():
                node_geom = f.geometry()
                if node_geom.isEmpty():
                    continue
                node_point = QgsGeometry.fromPointXY(QgsPointXY(node_geom.asPoint()))
                if self.areOverlappedPoints(first_point, node_point) or self.areOverlappedPoints(last_point, node_point):
                    singular = self.singular_forms.get(node_layer_name, node_layer_name)
                    found_nodes.append((node_layer, f, f"{singular} {f.attribute(node_id_field)}"))

        # Add nodes to listWidget and highlight them
        for node_layer, feature, node_info in found_nodes:
            self.listWidget.addItem(node_info)
            highlight = QgsHighlight(iface.mapCanvas(), feature.geometry(), node_layer)
            highlight.setColor(QColor("gold"))  # Adjacent features highlight color
            highlight.setWidth(3)
            highlight.show()
            self.adjacent_highlights.append(highlight)

    def findAdjacentLinksByGeometry(self, node_feature):
        node_geom = node_feature.geometry()
        if node_geom.isEmpty():
            return
        
        node_point = QgsPointXY(node_geom.asPoint())
        node_g = QgsGeometry.fromPointXY(node_point)

        link_layers = ["Pipes", "Service Connections", "Pumps"]
        project = QgsProject.instance()

        found_links = []
        for link_layer_name in link_layers:
            layers = project.mapLayersByName(link_layer_name)
            if not layers:
                continue
            link_layer = layers[0]
            if link_layer.geometryType() != 1:
                continue

            link_id_field = "Id"
            for f in link_layer.getFeatures():
                link_geom = f.geometry()
                if link_geom.isMultipart():
                    parts = link_geom.asMultiPolyline()
                    line_points = parts[0] if parts else []
                else:
                    line_points = link_geom.asPolyline()

                if not line_points:
                    continue

                first_p = QgsGeometry.fromPointXY(line_points[0])
                last_p = QgsGeometry.fromPointXY(line_points[-1])

                if self.areOverlappedPoints(node_g, first_p) or self.areOverlappedPoints(node_g, last_p):
                    singular = self.singular_forms.get(link_layer_name, link_layer_name)
                    found_links.append((link_layer, f, f"{singular} {f.attribute(link_id_field)}"))

        # Add links to listWidget and highlight them
        for link_layer, feature, link_info in found_links:
            self.listWidget.addItem(link_info)
            highlight = QgsHighlight(iface.mapCanvas(), feature.geometry(), link_layer)
            highlight.setColor(QColor("gold"))  # Adjacent features highlight color
            highlight.setWidth(3)
            highlight.show()
            self.adjacent_highlights.append(highlight)

    def onListItemClicked(self, item):
        # item.text() is in format "Junction J-1" or "Pipe P-123"
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
            return

        self.cbElementType.setCurrentText(element_type)
        index = self.cbElementId.findText(selected_id)
        if index >= 0:
            self.cbElementId.setCurrentIndex(index)

        self.findElement()
        
    def closeEvent(self, event):
        self.clearHighlights()
        self.clearAllLayerSelections()
        super(QGISRedFindElementsDock, self).closeEvent(event)