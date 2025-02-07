# -*- coding: utf-8 -*-
import os
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtWidgets import QDockWidget, QMessageBox, QLineEdit
from qgis.PyQt import uic
from PyQt5.QtCore import Qt, QTimer, QEvent
from qgis.PyQt.QtCore import pyqtSlot
from qgis.core import QgsProject, QgsGeometry, QgsLayerTreeLayer, QgsLayerTreeGroup, QgsPointXY, QgsRectangle, QgsVectorLayer, QgsSettings, QgsVectorLayer, QgsFeature, QgsRenderContext, QgsLayerMetadata
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

        self.listWidget.installEventFilter(self)

        self.setObjectName("QGISRedFindElementsDock")
        
        self.setFloating(False)
        
        if parent:
            parent.addDockWidget(Qt.LeftDockWidgetArea, self)

        self.element_types = [
            'Pipes', 
            'Junctions',
            'Multiple Demands',
            'Reservoirs',
            'Tanks',
            'Pumps'
            'Valves',
            'Sources',
            'Service Connections',
            'Isolation Valves',
            'Meters'
        ]
 
        self.singular_forms = {
            "Pipes": "Pipe",
            "Junctions": "Junction",
            "Multiple Demands": "Multiple Demand",
            "Reservoirs": "Reservoir",
            "Tanks": "Tank",
            "Pumps": "Pump",
            "Valves": "Valve",
            "Sources": "Source",
            "Service Connections": "Service Connection",
            "Isolation Valves": "Isolation Valve",
            "Meters": "Meter"
        }

        self.layers_identifiers = {
            "Pipes": "qgisred_main_pipes",
            "Junctions": "qgisred_main_junctions",
            "Multiple Demands": "qgisred_main_demands",
            "Reservoirs": "qgisred_main_reservoirs",
            "Tanks": "qgisred_main_tanks",
            "Pumps": "qgisred_main_pumps",
            "Valves": "qgisred_main_valves",
            "Sources": "qgisred_main_sources",
            "Service Connections": "qgisred_main_serviceconnections",
            "Isolation Valves": "qgisred_main_isolationvalves",
            "Meters": "qgisred_main_meters"
        }

        self.original_ids = []
        self.adjacent_highlights = []
        self.main_highlight = None
        self.current_selected_highlight = None 

        self.link_layers = ["qgisred_main_pipes", "qgisred_main_pumps", "qgisred_main_valves"]

        self.node_layers = ["qgisred_main_reservoirs", "qgisred_main_tanks", "qgisred_main_junctions"
                            , "qgisred_main_sources", "qgisred_main_demands"]
        
        self.special_layers = ["qgisred_main_serviceconnections"]
        
        self.sources_and_demands = ["qgisred_main_sources", "qgisred_main_demands"]

        self.digital_twins = [
            "qgisred_main_meters",
            "qgisred_main_isolationvalves",
            "qgisred_main_serviceconnections"
        ]

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

    def findNodeLayer(self, node_id):
        for layer in self.getCheckedInputGroupLayers():
            identifier = layer.customProperty("qgisred_identifier", "")
            if identifier in self.node_layers:
                # Skip if it's a Source or Multiple Demand
                if identifier in self.sources_and_demands:
                    continue
                for feature in layer.getFeatures():
                    if self.getFeatureIdValue(feature, layer) == node_id:
                        return layer, feature
        return None, None

    def eventFilter(self, obj, event):
        if obj == self.listWidget and event.type() == QEvent.FocusOut or (event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape):
            self.listWidget.clearSelection()
            self.listWidget.setCurrentRow(-1)
        return super(QGISRedFindElementsDock, self).eventFilter(obj, event)
        
    def getAvailableElementTypes(self):
        inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if not inputs_group:
            return []
        
        available_types = []

        checked_layers = inputs_group.checkedLayers()

        for identifier in self.layers_identifiers.values():
            for layer in checked_layers:
                if layer:
                    if layer.customProperty("qgisred_identifier") == identifier:
                        available_types.append(layer.name())
                        break

        return available_types

    def setupConnections(self):
        self.cbElementType.currentIndexChanged.connect(self.updateElementIds)
        self.leElementMask.textChanged.connect(self.filterElementIds)
        self.btFind.clicked.connect(self.onFindButtonClicked)
        self.listWidget.itemClicked.connect(self.onListItemSingleClicked)
        self.listWidget.itemDoubleClicked.connect(self.onListItemDoubleClicked)
        self.btClear.clicked.connect(self.clearAll)
        self.cbElementId.currentIndexChanged.connect(self.onElementIdChanged)

        project = QgsProject.instance()
        project.layersAdded.connect(self.onLayerTreeChanged)
        project.layersRemoved.connect(self.onLayerTreeChanged)
        project.readProject.connect(self.onLayerTreeChanged)
        project.cleared.connect(self.onLayerTreeChanged)

        root = project.layerTreeRoot()
        inputs_group = root.findGroup("Inputs")
        if inputs_group:
            inputs_group.addedChildren.connect(self.onLayerTreeChanged)
            inputs_group.removedChildren.connect(self.onLayerTreeChanged)
            for layer_node in inputs_group.findLayers():
                self.connectLayerSignals(layer_node)

    @pyqtSlot(int)
    def onElementIdChanged(self, index):
        self.labelFoundElement.setText("")
        self.listWidget.clear()

    def initializeElementTypes(self):
        self.cbElementType.clear()
        available_types = self.getAvailableElementTypes()
        self.cbElementType.addItems(available_types)
    
    def updateFoundElementLabel(self, selected_id, layer=None):
        if not selected_id:
            self.labelFoundElement.setText("")
            return

        if layer:
            # Restrict search to the provided layer.
            node_feature = None
            for feat in layer.getFeatures():
                if self.getFeatureIdValue(feat, layer) == selected_id:
                    node_feature = feat
                    break
            node_layer = layer if node_feature else None
        else:
            node_layer, node_feature = self.findNodeLayer(selected_id)

        if node_layer and node_feature:
            suffixes = []

            # Get the node's identifier from the layer custom property.
            node_identifier = node_layer.customProperty("qgisred_identifier", "")

            # Only check for a source if the node is a junction, reservoir or tank.
            if node_identifier in ["qgisred_main_junctions", "qgisred_main_reservoirs", "qgisred_main_tanks"]:
                source_layer = self.getLayerByIdentifier("qgisred_main_sources")
                if source_layer:
                    for src_feat in source_layer.getFeatures():
                        if (not src_feat.geometry().isEmpty() and
                                self.areOverlappedPoints(node_feature.geometry(), src_feat.geometry())):
                            suffixes.append("(Source)")
                            break

            # For junctions, check for a multiple demand (if any).
            if node_identifier == "qgisred_main_junctions":
                demand_layer = self.getLayerByIdentifier("qgisred_main_demands")
                if demand_layer:
                    for dmnd_feat in demand_layer.getFeatures():
                        if (not dmnd_feat.geometry().isEmpty() and
                                self.areOverlappedPoints(node_feature.geometry(), dmnd_feat.geometry())):
                            suffixes.append("(Mult.Dem)")
                            break

            singular_node_type = self.singular_forms.get(node_layer.name(), node_layer.name())
            suffix_str = " ".join(suffixes)
            self.labelFoundElement.setText(f"{singular_node_type} {selected_id} {suffix_str}".strip())
        else:
            # Fallback if no matching node feature is found.
            element_type = self.cbElementType.currentText()
            singular_element_type = self.singular_forms.get(element_type, element_type)
            self.labelFoundElement.setText(f"{singular_element_type} {selected_id}")

    def setDefaultValue(self):
        self.clearAll()

        pipes_layer = self.getLayerByIdentifier("qgisred_main_pipes")
        if not pipes_layer:
            return

        pipes_layer_name = pipes_layer.name()
        self.cbElementType.setCurrentText(pipes_layer_name)
        self.updateElementIds()

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
                id_val = self.getFeatureIdValue(f, layer, True)
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
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                lyr.removeSelection()

    def findOverlappedNode(self, point_feature, current_layer):
        feature_geom = point_feature.geometry()
        if feature_geom.isEmpty():
            return None, None

        feature_point = feature_geom.asPoint()
        feature_point_geom = QgsGeometry.fromPointXY(feature_point)

        for node_layer in self.getCheckedInputGroupLayers():
            if node_layer == current_layer:
                continue

            node_identifier = node_layer.customProperty("qgisred_identifier", "")
            if node_identifier in self.node_layers and node_identifier not in self.sources_and_demands:
                for node_feature in node_layer.getFeatures():
                    node_geom = node_feature.geometry()
                    if node_geom.isEmpty():
                        continue

                    node_point = node_geom.asPoint()
                    node_point_geom = QgsGeometry.fromPointXY(node_point)

                    if self.areOverlappedPoints(feature_point_geom, node_point_geom):
                        return node_feature, node_layer

        return None, None

    def findSourceOrDemandForNodeId(self, node_id):
        node_layer, node_feat = self.findNodeLayer(node_id)
        if not node_layer or not node_feat:
            return None, None 

        node_geom = node_feat.geometry()
        if node_geom.isEmpty():
            return None, None 

        # Check sources and demands layers directly
        for layer in self.getCheckedInputGroupLayers():
            identifier = layer.customProperty("qgisred_identifier", "")
            if identifier in self.sources_and_demands: 
                for feat in layer.getFeatures():
                    feat_geom = feat.geometry()
                    if feat_geom.isEmpty():
                        continue
                    if self.areOverlappedPoints(node_geom, feat_geom):
                        return feat, layer
        return None, None

    def getFeatureIdValue(self, feature, layer, special_naming=False):
        if not layer:
            return "Id"
                
        identifier = layer.customProperty("qgisred_identifier")
            
        if identifier in self.sources_and_demands:
            node_feature, node_layer = self.findOverlappedNode(feature, layer)
            if node_feature:
                node_id = self.extractNodeId(node_feature.attribute("Id"))
                if special_naming:
                    singular = self.singular_forms.get(node_layer.name(), node_layer.name())
                    suffix_list = []
                    if identifier == "qgisred_main_sources":
                        suffix_list.append("(Source)")
                    else:
                        suffix_list.append("(Mult.Dem)")
                    other_layer_id = "qgisred_main_demands" if identifier == "qgisred_main_sources" else "qgisred_main_sources"
                    other_layer_obj = self.getLayerByIdentifier(other_layer_id)
                    if other_layer_obj:
                        for other_feat in other_layer_obj.getFeatures():
                            if self.areOverlappedPoints(node_feature.geometry(), other_feat.geometry()):
                                if other_layer_id == "qgisred_main_sources":
                                    suffix_list.append("(Source)")
                                else:
                                    suffix_list.append("(Mult.Dem)")
                                break
                    suffix_str = " ".join(suffix_list)
                    return f"{singular} {node_id} {suffix_str}"
                return str(node_id)
            return ""
        else:
            value = feature.attribute("Id")
            id_str = str(value) if value is not None else ""
            if special_naming and identifier in ["qgisred_main_junctions", "qgisred_main_reservoirs", "qgisred_main_tanks"]:
                suffixes = []
                source_layer = self.getLayerByIdentifier("qgisred_main_sources")
                if source_layer:
                    for src_feat in source_layer.getFeatures():
                        if self.areOverlappedPoints(feature.geometry(), src_feat.geometry()):
                            suffixes.append("(Source)")
                            break
                if identifier == "qgisred_main_junctions":
                    demand_layer = self.getLayerByIdentifier("qgisred_main_demands")
                    if demand_layer:
                        for dmnd_feat in demand_layer.getFeatures():
                            if self.areOverlappedPoints(feature.geometry(), dmnd_feat.geometry()):
                                suffixes.append("(Mult.Dem)")
                                break
                if suffixes:
                    id_str += " " + " ".join(suffixes)
            return id_str


    def getLayerByIdentifier(self, identifier):
        for layer in self.getCheckedInputGroupLayers():
            if layer.customProperty("qgisred_identifier") == identifier:
                return layer
        return None
    
    def extractNodeId(self, text):
        text = text.replace(" (Source)", "").replace(" (Mult.Dem)", "")
        
        parts = text.strip().split()
        if len(parts) > 1:
            return parts[-1]
        return text

    def onFindButtonClicked(self):
        if self.listWidget.currentItem():
            self.onListItemDoubleClicked(self.listWidget.currentItem())
        else:
            self.findElement()

    @pyqtSlot()
    def findElement(self):
        self.clearHighlights()
        self.clearAllLayerSelections()
        
        self.listWidget.clear()
        selected_type = self.cbElementType.currentText()
        selected_id = self.extractNodeId(self.cbElementId.currentText()) 
        element_identifier = self.layers_identifiers.get(selected_type)
        
        if selected_id == "":
            self.labelFoundElement.setText("")
            return
            
        if not selected_id:
            QMessageBox.warning(self, "Warning", "Please select an element ID")
            return
        
        layer = self.getLayerForElementType(selected_type)
        if layer:
            found_feature = None
            found_feature_layer = None

            if layer.customProperty("qgisred_identifier") in self.sources_and_demands:
                found_feature, found_feature_layer = self.findSourceOrDemandForNodeId(selected_id)
            else:
                for feature in layer.getFeatures():
                    if self.getFeatureIdValue(feature, layer) == selected_id:
                        found_feature = feature
                        found_feature_layer = layer
                        break

            if not found_feature:
                QMessageBox.information(self, "Info", "Feature not found")
                return
                
            # Now update the label using the specific layer where the feature was found.
            self.updateFoundElementLabel(selected_id, found_feature_layer)
            
            highlight = QgsHighlight(iface.mapCanvas(), found_feature.geometry(), layer)
            highlight.setColor(QColor("red"))
            highlight.setWidth(5)
            highlight.show()
            self.main_highlight = highlight
            
            self.adjustMapView(found_feature)
            
            identifier = layer.customProperty("qgisred_identifier")
            # if identifier in self.only_node_layers:
            #     # Only highlight the node; do not show adjacent elements.
            #     return
    
            if self.isLineElement(layer):
                self.findAdjacentNodesByGeometry(found_feature)
            # elif self.isSpecialElement(layer):
            #     self.findNodesAndLinksAdjacencies(found_feature)
            elif identifier == "qgisred_main_meters":
                self.findMeterAdjacency(found_feature, layer)
            elif identifier == "qgisred_main_isolationvalves":
                self.findIsolationValveAdjacency(found_feature, layer)
            elif identifier == "qgisred_main_serviceconnections":
                self.findServiceConnectionAdjacency(found_feature, layer) 
            else:
                self.findAdjacentLinksByGeometry(found_feature)


    def isLineElement(self, layer):
        return layer.customProperty("qgisred_identifier") in self.link_layers
    
    def isSpecialElement(self, layer):
        return layer.customProperty("qgisred_identifier") in self.special_layers
    
    def areOverlappedPoints(self, point1, point2, tolerance=1e-9):
        return point1.distance(point2) < tolerance

    def addServiceConnectionAdjacencies(self, current_geom, tolerance):
        service_layers = [
            layer for layer in self.getCheckedInputGroupLayers()
            if layer.customProperty("qgisred_identifier") == "qgisred_main_serviceconnections"
        ]
        for layer in service_layers:
            for feat in layer.getFeatures():
                service_geom = feat.geometry()
                if service_geom.isEmpty():
                    continue
                if current_geom.intersects(service_geom) or current_geom.distance(service_geom) < tolerance:
                    service_id = self.getFeatureIdValue(feat, layer)
                    singular = self.singular_forms.get(layer.name(), layer.name())
                    item_text = f"{singular} {service_id}"
                    self.listWidget.addItem(item_text)

    def findAdjacentNodesByGeometry(self, line_feature):
        geom = line_feature.geometry()
        if geom.isEmpty():
            return

        if geom.isMultipart():
            parts = geom.asMultiPolyline()
            line_points = parts[0] if parts else []
        else:
            line_points = geom.asPolyline()

        if not line_points:
            return

        line_geom = QgsGeometry.fromPolylineXY(line_points)
        tolerance = 1e-6
        found_nodes = []

        node_map_layers = [
            layer
            for layer in self.getCheckedInputGroupLayers()
            if (
                layer.customProperty("qgisred_identifier") in self.node_layers 
                or layer.customProperty("qgisred_identifier") in self.special_layers
            )
        ]

        for node_layer in node_map_layers:
            if node_layer.geometryType() != 0:
                continue

            identifier = node_layer.customProperty("qgisred_identifier", "")
            if identifier in self.sources_and_demands:
                continue

            for f in node_layer.getFeatures():
                node_geom = f.geometry()
                if node_geom.isEmpty():
                    continue

                dist = line_geom.distance(node_geom)
                if dist < tolerance:
                    node_id = self.getFeatureIdValue(f, node_layer)
                    layer_name = node_layer.name()
                    singular = self.singular_forms.get(layer_name) or layer_name

                    node_suffixes = []
                    if identifier in ["qgisred_main_junctions", "qgisred_main_reservoirs", "qgisred_main_tanks"]:
                        source_layer = self.getLayerByIdentifier("qgisred_main_sources")
                        if source_layer:
                            for src_feat in source_layer.getFeatures():
                                if self.areOverlappedPoints(node_geom, src_feat.geometry()):
                                    node_suffixes.append("(Source)")
                                    break
                        if identifier == "qgisred_main_junctions":
                            demand_layer = self.getLayerByIdentifier("qgisred_main_demands")
                            if demand_layer:
                                for dmnd_feat in demand_layer.getFeatures():
                                    if self.areOverlappedPoints(node_geom, dmnd_feat.geometry()):
                                        node_suffixes.append("(Mult.Dem)")
                                        break

                    suffix_str = ""
                    if node_suffixes:
                        suffix_str = " " + " ".join(node_suffixes)
                    node_info = f"{singular} {node_id}{suffix_str}"

                    found_nodes.append((node_layer, f, node_info))

        for node_layer, feature, node_info in found_nodes:
            self.listWidget.addItem(node_info)

        # Check for adjacent service connections
        self.addServiceConnectionAdjacencies(line_geom, tolerance)

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
            if link_layer.geometryType() != 1:
                continue

            identifier = link_layer.customProperty("qgisred_identifier", "")
            if not identifier:
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

                if (
                    node_g.distance(link_geom) < tolerance
                    or self.areOverlappedPoints(node_g, QgsGeometry.fromPointXY(line_points[0]))
                    or self.areOverlappedPoints(node_g, QgsGeometry.fromPointXY(line_points[-1]))
                ):
                    link_id = self.getFeatureIdValue(f, link_layer)
                    layer_name = link_layer.name()
                    singular = self.singular_forms.get(layer_name) or layer_name
                    found_links.append((link_layer, f, f"{singular} {link_id}"))

        for link_layer, feature, link_info in found_links:
            self.listWidget.addItem(link_info)

        # Check for adjacent service connections
        self.addServiceConnectionAdjacencies(node_g, tolerance)

    def extractTypeAndId(self, text):
        original_text = text.strip()
        
        text_clean = original_text.replace(" (Source)", "").replace(" (Mult.Dem)", "").strip()

        sorted_singulars = sorted(self.singular_forms.values(), key=len, reverse=True)
        for singular in sorted_singulars:
            if text_clean.startswith(singular + " "):
                selected_id = text_clean[len(singular):].strip()
                if original_text.startswith(singular + " "):
                    full_id = original_text[len(singular):].strip()
                else:
                    full_id = selected_id
                return singular, selected_id, full_id

        parts = text_clean.split(" ", 1)
        if len(parts) < 2:
            return None, None, None
        singular = parts[0]
        selected_id = parts[1].strip()
        if original_text.startswith(singular + " "):
            full_id = original_text[len(singular):].strip()
        else:
            full_id = selected_id
        return singular, selected_id, full_id

    def getIdentifierFromLayerName(self, layer_name):
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if layers:
            layer = layers[0]
            return layer.customProperty("qgisred_identifier", None)
        return None

    def onListItemSingleClicked(self, item):
        if self.current_selected_highlight:
            self.current_selected_highlight.hide()
            self.current_selected_highlight = None

        singular_type, selected_id, _ = self.extractTypeAndId(item.text())
        if not singular_type or not selected_id:
            return

        element_identifier = None
        for plural, singular in self.singular_forms.items():
            if singular == singular_type:
                element_identifier = self.layers_identifiers.get(plural)
                break

        if not element_identifier:
            element_identifier = self.getIdentifierFromLayerName(singular_type)

        matching_layers = [
            layer for layer in self.getCheckedInputGroupLayers()
            if layer.customProperty("qgisred_identifier") == element_identifier
        ]

        for layer in matching_layers:
            for feature in layer.getFeatures():
                if self.getFeatureIdValue(feature, layer) == selected_id:
                    highlight = QgsHighlight(iface.mapCanvas(), feature.geometry(), layer)
                    highlight.setColor(QColor("orange"))
                    highlight.setWidth(5)
                    highlight.show()
                    self.current_selected_highlight = highlight
                    self.adjustMapView(feature)
                    return

    def onListItemDoubleClicked(self, item):
        self.leElementMask.clear()
        singular_type, selected_id, full_id = self.extractTypeAndId(item.text())
        if not singular_type or not selected_id:
            return

        element_type = None
        for plural, singular in self.singular_forms.items():
            if singular == singular_type:
                element_type = plural
                break

        if not element_type:
            element_type = singular_type

        self.cbElementType.setCurrentText(element_type)

        index = self.cbElementId.findText(full_id)

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

        if not is_point:
            if ratio > 0.25:
                factor = ratio / 0.25
                new_width = map_width * factor
                new_height = map_height * factor
                new_extent = self.recenterExtent(new_width, new_height, center_x, center_y)
            elif ratio < 0.05:
                factor = 0.05 / ratio
                new_width = map_width / factor
                new_height = map_height / factor
                new_extent = self.recenterExtent(new_width, new_height, center_x, center_y)
            else:
                new_extent = QgsRectangle(current_extent)
        else:
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

        left_dist = feature_extent.xMinimum() - current_extent.xMinimum()
        right_dist = current_extent.xMaximum() - feature_extent.xMaximum()
        top_dist = current_extent.yMaximum() - feature_extent.yMaximum()
        bottom_dist = feature_extent.yMinimum() - current_extent.yMinimum()

        new_extent = QgsRectangle(current_extent)

        if left_dist < margin_x:
            shift = margin_x - left_dist
            new_extent.setXMinimum(new_extent.xMinimum() - shift)
            new_extent.setXMaximum(new_extent.xMaximum() - shift)

        if right_dist < margin_x:
            shift = margin_x - right_dist
            new_extent.setXMinimum(new_extent.xMinimum() + shift)
            new_extent.setXMaximum(new_extent.xMaximum() + shift)

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
        print( "on layer tree changed called:" )
        current_type = self.cbElementType.currentText()
        current_id = self.extractNodeId(self.cbElementId.currentText())
        self.initializeCustomLayerProperties()
        self.initializeElementTypes()
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
                layer_node.visibilityChanged.connect(self.onLayerTreeChanged)
        except:
            pass

    def disconnectLayerNodeSignals(self, layer_node):
        try:
            layer_node.nameChanged.disconnect(self.onLayerTreeChanged)
            layer_node.visibilityChanged.disconnect(self.onLayerTreeChanged)
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

    def initializeCustomLayerProperties(self):
        inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if not inputs_group:
            return
        for layer in inputs_group.findLayers():
            layer_name = layer.name()
            for element_type, identifier in self.layers_identifiers.items():
                if layer_name == element_type:
                    layer_obj = layer.layer()
                    if not layer_obj:
                        continue

                    custom_property = layer_obj.customProperty("qgisred_identifier", None)
                    if not custom_property:
                        layer_obj.setCustomProperty("qgisred_identifier", identifier)

                    layer_metadata = QgsLayerMetadata()
                    layer_metadata.setIdentifier(identifier)
                    layer_obj.setMetadata(layer_metadata)

    def findNodesAndLinksAdjacencies(self, feature):
        geom = feature.geometry()
        if geom.isEmpty():
            return

        line_points = []
        if geom.isMultipart():
            parts = geom.asMultiPolyline()
            for part in parts:
                if part:
                    line_points.extend(part)
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
            if node_layer.geometryType() != 0:
                continue
                
            identifier = node_layer.customProperty("qgisred_identifier", "")
            if not identifier:
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
                    
                    layer_name = next((name for name, id in self.layers_identifiers.items() if id == identifier), identifier)
                    singular = self.singular_forms.get(layer_name) or layer_name
                    
                    node_info = f"{singular} {node_id}"

        tolerance = 1e-9
        found_links = []
        link_map_layers = [
            layer
            for layer in self.getCheckedInputGroupLayers()
            if layer.customProperty("qgisred_identifier") in self.link_layers
        ]
        
        for link_layer in link_map_layers:
            if link_layer.geometryType() != 1:
                continue
                
            identifier = link_layer.customProperty("qgisred_identifier", "")
            if not identifier:
                continue
                
            for f in link_layer.getFeatures():
                link_geom = f.geometry()
                if link_geom.isEmpty():
                    continue
                if link_geom.isMultipart():
                    parts = link_geom.asMultiPolyline()
                    link_points = parts[0] if parts else []
                else:
                    link_points = link_geom.asPolyline()
                if not link_points:
                    continue
                feature_geom = QgsGeometry.fromPolylineXY(line_points)
                if (
                    feature_geom.distance(link_geom) < tolerance
                    or self.areOverlappedPoints(QgsGeometry.fromPointXY(line_points[0]),
                                                QgsGeometry.fromPointXY(link_points[0]))
                    or self.areOverlappedPoints(QgsGeometry.fromPointXY(line_points[-1]),
                                                QgsGeometry.fromPointXY(link_points[-1]))
                    or self.areOverlappedPoints(QgsGeometry.fromPointXY(line_points[0]),
                                                QgsGeometry.fromPointXY(link_points[-1]))
                    or self.areOverlappedPoints(QgsGeometry.fromPointXY(line_points[-1]),
                                                QgsGeometry.fromPointXY(link_points[0]))
                ):
                    link_id = self.getFeatureIdValue(f, link_layer)
                    
                    layer_name = next((name for name, id in self.layers_identifiers.items() if id == identifier), identifier)
                    singular = self.singular_forms.get(layer_name) or layer_name
                    found_links.append((link_layer, f, f"{singular} {link_id}"))

        for node_layer, feature_item, node_info in found_nodes:
            self.listWidget.addItem(node_info)

        for link_layer, feature_item, link_info in found_links:
            self.listWidget.addItem(link_info)

    def findServiceConnectionAdjacency(self, feature, current_layer):
        geom = feature.geometry()
        if geom.isEmpty():
            return

        if geom.isMultipart():
            parts = geom.asMultiPolyline()
            if not parts or not parts[0]:
                return
            line_points = parts[0]
        else:
            line_points = geom.asPolyline()

        if not line_points:
            return

        endpoints = [QgsPointXY(line_points[0]), QgsPointXY(line_points[-1])]
        tolerance = 1e-6

        for pt in endpoints:
            dummy_feature = QgsFeature()
            dummy_feature.setGeometry(QgsGeometry.fromPointXY(pt))
            node_feature, node_layer = self.findOverlappedNode(dummy_feature, current_layer)
            if node_feature and node_layer.customProperty("qgisred_identifier") == "qgisred_main_junctions":
                junction_item_text = self.getFeatureIdValue(node_feature, node_layer, special_naming=True)
                junction_full_name = node_layer.name() + ' ' + junction_item_text
                self.listWidget.addItem(junction_full_name)
                return

        for pt in endpoints:
            pt_geom = QgsGeometry.fromPointXY(pt)
            for layer in self.getCheckedInputGroupLayers():
                if layer.customProperty("qgisred_identifier") == "qgisred_main_pipes":
                    for f in layer.getFeatures():
                        pipe_geom = f.geometry()
                        if pipe_geom.isEmpty():
                            continue
                        if pt_geom.distance(pipe_geom) < tolerance:
                            pipe_id = self.getFeatureIdValue(f, layer)
                            singular = self.singular_forms.get(layer.name(), layer.name())
                            self.listWidget.addItem(f"{singular} {pipe_id}")
                            return

    def findIsolationValveAdjacency(self, feature, current_layer):
        geom = feature.geometry()
        if geom.isEmpty():
            return

        tolerance = 1e-6

        node_feature, node_layer = self.findOverlappedNode(feature, current_layer)
        if node_feature and node_layer.customProperty("qgisred_identifier") == "qgisred_main_junctions":
            node_item_text = self.getFeatureIdValue(node_feature, node_layer, special_naming=True)
            node_full_name = node_layer.name() + ' ' + node_item_text
            self.listWidget.addItem(node_full_name)
            return

        for layer in self.getCheckedInputGroupLayers():
            if layer.customProperty("qgisred_identifier") == "qgisred_main_pipes":
                for f in layer.getFeatures():
                    pipe_geom = f.geometry()
                    if pipe_geom.isEmpty():
                        continue
                    if geom.distance(pipe_geom) < tolerance:
                        pipe_id = self.getFeatureIdValue(f, layer)
                        singular = self.singular_forms.get(layer.name(), layer.name())
                        self.listWidget.addItem(f"{singular} {pipe_id}")
                        return 

    def findMeterAdjacency(self, feature, current_layer):
        geom = feature.geometry()
        if geom.isEmpty():
            return

        tolerance = 1e-6

        node_feature, node_layer = self.findOverlappedNode(feature, current_layer)
        if node_feature and node_layer.customProperty("qgisred_identifier") in [
            "qgisred_main_junctions", "qgisred_main_tanks", "qgisred_main_reservoirs"
        ]:
            node_item_text = self.getFeatureIdValue(node_feature, node_layer, special_naming=True)
            if node_layer.customProperty("qgisred_identifier") == "qgisred_main_junctions":
                layer_name = node_layer.name()
                node_item_text = self.singular_forms.get(layer_name, layer_name) + ' ' + node_item_text
            self.listWidget.addItem(node_item_text)
            return

        for layer in self.getCheckedInputGroupLayers():
            if layer.customProperty("qgisred_identifier") in [
                "qgisred_main_pipes", "qgisred_main_pumps", "qgisred_main_valves"
            ]:
                for f in layer.getFeatures():
                    link_geom = f.geometry()
                    if link_geom.isEmpty():
                        continue
                    if geom.distance(link_geom) < tolerance:
                        adj_id = self.getFeatureIdValue(f, layer)
                        singular = self.singular_forms.get(layer.name(), layer.name())
                        self.listWidget.addItem(f"{singular} {adj_id}")
                        return
         
    def disconnectLayerSignals(self, layer):
        try:
            if hasattr(layer, 'nameChanged'):
                try:
                    layer.nameChanged.disconnect(self.onLayerTreeChanged)
                except:
                    pass
            if hasattr(layer, 'dataChanged'):
                try:
                    layer.dataChanged.disconnect(self.onLayerTreeChanged)
                except:
                    pass
            if hasattr(layer, 'visibilityChanged'):
                try:
                    layer.visibilityChanged.disconnect(self.onLayerTreeChanged)
                except:
                    pass
        except:
            pass