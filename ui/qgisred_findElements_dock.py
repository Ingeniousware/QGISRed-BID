# -*- coding: utf-8 -*-
import os
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtWidgets import QDockWidget, QMessageBox, QLineEdit
from qgis.PyQt import uic
from PyQt5.QtCore import Qt
from qgis.PyQt.QtCore import pyqtSlot
from qgis.core import QgsProject, QgsGeometry, QgsPointXY, QgsRectangle
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
        self.current_selected_highlight = None  # Track single-click highlight
        
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.labelFoundElement.setFont(font)
        
        self.setupConnections()
        self.initializeElementTypes()
        self.labelFoundElement.setText("")

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
        self.listWidget.itemClicked.connect(self.onListItemSingleClicked)
        self.listWidget.itemDoubleClicked.connect(self.onListItemDoubleClicked)
        
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
            self.original_ids = sorted([str(f.attribute("Id")) for f in layer.getFeatures() if f.attribute("Id") is not None])
        
        if self.leElementMask.text():
            self.filterElementIds()
        else:
            # Always add a blank item at the top
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
            
        # Always add a blank item at the top
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
        
    def clearAllLayerSelections(self):
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr is not None:
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
                if str(feature.attribute("Id")) == selected_id:
                    found_feature = feature
                    break

            if not found_feature:
                QMessageBox.information(self, "Info", "Feature not found")
                return

            singular = self.singular_forms.get(selected_type, selected_type)
            self.labelFoundElement.setText(f"{singular} {selected_id}")

            # Highlight main feature
            self.main_highlight = QgsHighlight(iface.mapCanvas(), found_feature.geometry(), layer)
            self.main_highlight.setColor(QColor("red"))
            self.main_highlight.setWidth(5)
            self.main_highlight.show()

            # Adjust map view
            self.adjustMapView(found_feature)

            # Select the feature
            layer.selectByIds([found_feature.id()])

            # Find adjacent elements
            if self.isLineElement(selected_type):
                self.labelAdjacentNodeLinks.setText("Adjacent Nodes")
                self.findAdjacentNodesByGeometry(found_feature)
            else:
                self.labelAdjacentNodeLinks.setText("Adjacent Links")
                self.findAdjacentLinksByGeometry(found_feature)

    def isLineElement(self, element_type):
        return element_type in ["Pipes", "Service Connections", "Pumps"]
      
    def setDockStyle(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFindElements.png')
        self.setWindowIcon(QIcon(icon_path))

        search_icon = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFilter.png'))
        self.leElementMask.addAction(search_icon, QLineEdit.LeadingPosition)

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

        for node_layer, feature, node_info in found_nodes:
            self.listWidget.addItem(node_info)

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
            return
        layer = self.getLayerForElementType(element_type)
        if layer:
            for feature in layer.getFeatures():
                if str(feature.attribute("Id")) == selected_id:
                    highlight = QgsHighlight(iface.mapCanvas(), feature.geometry(), layer)
                    highlight.setColor(QColor("orange"))
                    highlight.setWidth(5)
                    highlight.show()
                    self.current_selected_highlight = highlight
                    break

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
