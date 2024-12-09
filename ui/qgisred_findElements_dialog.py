# -*- coding: utf-8 -*-

import os
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QDialog, QMessageBox, QLineEdit
from PyQt5 import sip
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QVariant, Qt
from PyQt5.QtCore import pyqtSlot
from qgis.core import (
    QgsLayerTreeGroup, QgsLayerTreeLayer, QgsLayerTreeNode, QgsProject,
    QgsVectorFileWriter, QgsVectorLayer,
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat
)
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_findElements_dialog.ui"))

class QGISRedFindElementsDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(QGISRedFindElementsDialog, self).__init__(parent)
        self.setupUi(self)
        self.setDialogStyle()
        
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
        
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.labelFoundElement.setFont(font)
        
        self.setupConnections()
        self.initializeElementTypes()
        self.labelFoundElement.setText("")
        
        # current_id = self.cbElementId.currentText()
        # if current_id:
        #     self.updateFoundElementLabel(current_id)

    def getAvailableElementTypes(self):
        inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if not inputs_group:
            return []
        
        available_types = []
        for element_type in self.element_types:
            for child in inputs_group.children():
                if isinstance(child, QgsLayerTreeLayer) and child.name() == element_type:
                    available_types.append(element_type)
                    break
        return available_types
        
    def setupConnections(self):
        self.cbElementType.currentIndexChanged.connect(self.updateElementIds)
        self.leElementMask.textChanged.connect(self.filterElementIds)
        self.btFind.clicked.connect(self.findElement)
        #self.cbElementId.currentTextChanged.connect(self.updateFoundElementLabel)
        
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
        
    @pyqtSlot()
    def updateElementIds(self):
        self.cbElementId.clear()
        self.original_ids.clear()
        self.labelFoundElement.setText("")
        
        layer = self.getLayerForElementType(self.cbElementType.currentText())
        if layer:
            self.original_ids = sorted([str(f.attribute("Id")) for f in layer.getFeatures()])
        
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
        
    @pyqtSlot()
    def findElement(self):
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
                    
                    # Update labels after finding element
                    singular = self.singular_forms.get(selected_type, selected_type)
                    self.labelFoundElement.setText(f"{singular} {selected_id}")
                    
                    if self.isLineElement(selected_type):
                        self.labelAdjacentNodeLinks.setText("Adjacent Nodes")
                    else:
                        self.labelAdjacentNodeLinks.setText("Adjacent Links")
                    break

    def isLineElement(self, element_type):
        return element_type in ["Pipes", "Service Connections"]
      
    def setDialogStyle(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFindElements.png')
        self.setWindowIcon(QIcon(icon_path))

        search_icon = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFilter.png'))
        self.leElementMask.addAction(search_icon, QLineEdit.LeadingPosition)

        # Set white background for dropdowns
        self.cbElementType.setStyleSheet("QComboBox { background-color: white; }")
        self.cbElementId.setStyleSheet("QComboBox { background-color: white; }")