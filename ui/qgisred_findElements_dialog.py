# -*- coding: utf-8 -*-

import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QMessageBox
from qgis.PyQt import uic

from qgis.core import QgsProject

from qgis.utils import iface

from ..tools.qgisred_utils import QGISRedUtils

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_findElements_dialog.ui"))

class QGISRedFindElementsDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(QGISRedFindElementsDialog, self).__init__(parent)
        self.setupUi(self)
        self.setDialogStyle()
        
        self.element_types = [
            "All Elements",
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
        
        self.original_ids = []
        
        self.setupConnections()
        self.initializeElementTypes()
    
    def setDialogStyle(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFindElements.png')
        self.setWindowIcon(QIcon(icon_path))

    def setupConnections(self):
        self.cbElementType.currentIndexChanged.connect(self.updateElementIds)
        self.leElementMask.textChanged.connect(self.filterElementIds)
        self.btFind.clicked.connect(self.findElement)
        
    def initializeElementTypes(self):
        self.cbElementType.clear()
        self.cbElementType.addItems(self.element_types)
        
    def getLayerForElementType(self, element_type):
        project = QgsProject.instance()
        if element_type == "All Elements":
            return None
            
        layer_map = {
            "Reservoirs": "Reservoirs",
            "Tanks": "Tanks",
            "Junctions": "Junctions",
            "Pumps": "Pumps",
            "Valves": "Valves",
            "Pipes": "Pipes",
            "Meters": "Meters",
            "Service Connections": "Service Connections",
            "Isolation Valves": "Isolation Valves"
        }
        
        layer_name = layer_map.get(element_type)
        if layer_name:
            layers = project.mapLayersByName(layer_name)
            return layers[0] if layers else None
        return None
        
    def updateElementIds(self):
        self.cbElementId.clear()
        self.original_ids.clear()
        
        selected_type = self.cbElementType.currentText()
        if selected_type == "All Elements":
            for element_type in self.element_types[1:]:
                layer = self.getLayerForElementType(element_type)
                if layer:
                    self.original_ids.extend([str(f.attribute("Id")) for f in layer.getFeatures()])
            self.original_ids = sorted(set(self.original_ids))
        else:
            layer = self.getLayerForElementType(selected_type)
            if layer:
                self.original_ids = sorted([str(f.attribute("Id")) for f in layer.getFeatures()])
        
        if self.leElementMask.text():
            self.filterElementIds()
        else:
            self.cbElementId.addItems(self.original_ids)
                
    def filterElementIds(self):
        mask = self.leElementMask.text().strip()
        
        self.cbElementId.clear()
        
        if mask:
            filtered_items = [item for item in self.original_ids if mask.lower() in item.lower()]
        else:
            filtered_items = self.original_ids
            
        self.cbElementId.addItems(filtered_items)
        
    def findElement(self):
        print("HERE")
        selected_type = self.cbElementType.currentText()
        selected_id = self.cbElementId.currentText()
        
        if not selected_id:
            QMessageBox.warning(self, "Warning", "Please select an element ID")
            return
            
        layer = self.getLayerForElementType(selected_type)
        if layer:
            for feature in layer.getFeatures():
                if str(feature.attribute("Id")) == selected_id:
                    iface.mapCanvas().zoomToFeatureIds(layer, [feature.id()])
                    layer.selectByIds([feature.id()])
                    break