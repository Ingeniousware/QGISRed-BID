# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDockWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt
from qgis.PyQt import uic
from qgis.core import QgsProject

from ..tools.qgisred_utils import QGISRedUtils
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_queriesbyattributes_dock.ui"))

class QGISRedQueriesByAttributesDock(QDockWidget, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(QGISRedQueriesByAttributesDock, self).__init__(parent or iface.mainWindow())
        self.setupUi(self) 
        self.iface = iface
        self.canvas = iface.mapCanvas()

        self.initializeQueriesByAttributes()

    def initializeQueriesByAttributes(self):
        self.elementIdentifiers = {
            'Pipes': 'qgisred_pipes', 
            'Junctions': 'qgisred_junctions',
            'Multiple Demands': 'qgisred_demands',
            'Reservoirs': 'qgisred_reservoirs',
            'Tanks': 'qgisred_tanks',
            'Pumps': 'qgisred_pumps',
            'Valves': 'qgisred_valves',
            'Sources': 'qgisred_sources',
            'Service Connections': 'qgisred_serviceconnections',
            'Isolation Valves': 'qgisred_isolationvalves',
            'Meters': 'qgisred_meters'
        }
        
        self.conditionsByType = {
            'numeric': ['=', '>', '<', '>=', '<=', '≠'],
            'text': ['=', '≠', 'contains', 'starts with', 'ends with'],
            'date': ['=', '>', '<', '>=', '<=', '≠'],
            'boolean': ['is true', 'is false']
        }
    
        self.fieldTypeMapping = {
            'int': 'numeric',
            'double': 'numeric',
            'string': 'text',
            'date': 'date',
            'datetime': 'date',
            'time': 'date',
            'bool': 'boolean'
        }

        if self.tableWidgetCriteria.columnCount() == 0:
            self.tableWidgetCriteria.setColumnCount(1)
            self.tableWidgetCriteria.setHorizontalHeaderLabels(["Query Conditions"])
            self.tableWidgetCriteria.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        self.initializeElementTypes()
        self.setupConnections()

    def setupConnections(self):
        self.cbElementType.currentIndexChanged.connect(self.updateProperties)
        self.cbProperty.currentIndexChanged.connect(self.updateValues)
        self.btAdd.clicked.connect(self.addItemToTable)

    def resizeToMinimumHeight(self):
        self.layout().activate()
        self.adjustSize()

    def updateProperties(self):
        selectedLayer = self.cbElementType.currentData(Qt.UserRole)
        
        if not selectedLayer:
            return
        
        self.cbProperty.clear()
        
        fields = selectedLayer.fields()
        
        for field in fields:
            fieldName = field.name()
            if fieldName.lower() != "id" and fieldName.lower() != "descrip":
                self.cbProperty.addItem(f"{fieldName}")

        if self.cbProperty.count() > 0:
            self.updateConditions()
            self.updateValues()

    def initializeElementTypes(self):
        self.cbElementType.clear()
        inputsGroup = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if inputsGroup:
            checkedLayers = inputsGroup.checkedLayers()
            for element, identifier in self.elementIdentifiers.items():
                for layer in checkedLayers:
                    if layer and layer.customProperty("qgisred_identifier") == identifier:
                        self.cbElementType.addItem(layer.name())
                        self.cbElementType.setItemData(self.cbElementType.count() - 1, layer, Qt.UserRole)
        
        self.updateProperties()

    def getAvailableElementTypes(self):
        inputsGroup = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if not inputsGroup:
            return []
        availableTypes = []
        checkedLayers = inputsGroup.checkedLayers()
        for element, identifier in self.elementIdentifiers.items():
            for layer in checkedLayers:
                if layer and layer.customProperty("qgisred_identifier") == identifier:
                    availableTypes.append(layer.name())
                    break
        return availableTypes

    def updateConditions(self):
        self.cbCondition.clear()
        
        selectedLayer = self.cbElementType.currentData(Qt.UserRole)
        if not selectedLayer:
            return
        
        selectedPropertyText = self.cbProperty.currentText()
        if not selectedPropertyText:
            return
        
        fieldName = selectedPropertyText.split(':')[0].strip()
        
        field = selectedLayer.fields().field(fieldName)
            
        qgisType = field.typeName().lower()
        conditionType = self.fieldTypeMapping.get(qgisType, 'text')
        
        self.cbCondition.addItems(self.conditionsByType.get('numeric', []))

    def updateValues(self):
        self.cbValue.clear()
        
        selectedLayer = self.cbElementType.currentData(Qt.UserRole)
        if not selectedLayer:
            return
        
        selectedPropertyText = self.cbProperty.currentText()
        if not selectedPropertyText:
            return
        
        fieldName = selectedPropertyText.split(':')[0].strip()
        field = selectedLayer.fields().field(fieldName)
        qgisType = field.typeName().lower()
        fieldType = self.fieldTypeMapping.get(qgisType, 'text')
        
        if fieldType == 'boolean':
            self.cbValue.addItems(['true', 'false'])
        
        elif fieldType == 'numeric':
            min_val, max_val = self.getFieldMinMax(selectedLayer, fieldName)
            
            if min_val is not None and max_val is not None:
                interval = (max_val - min_val) / 5
                
                for i in range(5):
                    start = min_val + (i * interval)
                    end = min_val + ((i + 1) * interval)
                    
                    if isinstance(min_val, int) and isinstance(max_val, int):
                        start_rounded = int(round(start))
                        end_rounded = int(round(end))
                        if i == 4:
                            end_rounded = max_val
                        range_text = f"{start_rounded} - {end_rounded}"
                    else:
                        if i == 4:
                            range_text = f"{start:.2f} - {max_val:.2f}"
                        else:
                            range_text = f"{start:.2f} - {end:.2f}"
                    
                    self.cbValue.addItem(range_text)
        
        elif fieldType == 'date':
            unique_values = self.getUniqueFieldValues(selectedLayer, fieldName)
            for value in unique_values:
                if value is not None:
                    self.cbValue.addItem(str(value))
        
        else:  # text fields
            # Get all unique values
            unique_values = self.getUniqueFieldValues(selectedLayer, fieldName)
            for value in unique_values:
                if value is not None: 
                    self.cbValue.addItem(str(value))

    def getFieldMinMax(self, layer, fieldName):
        min_val = None
        max_val = None
        
        if layer and layer.fields().indexFromName(fieldName) != -1:
            for feature in layer.getFeatures():
                value = feature[fieldName]
                if value is not None:
                    min_val = value
                    max_val = value
                    break
            
            for feature in layer.getFeatures():
                value = feature[fieldName]
                if value is not None:
                    if value < min_val:
                        min_val = value
                    if value > max_val:
                        max_val = value
        
        return min_val, max_val

    def getUniqueFieldValues(self, layer, fieldName):
        unique_values = set()
        
        if layer and layer.fields().indexFromName(fieldName) != -1:
            for feature in layer.getFeatures():
                value = feature[fieldName]
                unique_values.add(value)
        
        return sorted(list(unique_values))


    def addItemToTable(self):
        property_text = self.cbProperty.currentText()
        condition_text = self.cbCondition.currentText()
        value_text = self.cbValue.currentText()
        
        if not property_text or not condition_text or not value_text:
            return
        
        concat_text = f"{property_text} {condition_text} {value_text}"
        
        row_count = self.tableWidgetCriteria.rowCount()
        
        self.tableWidgetCriteria.insertRow(row_count)
        
        item = QTableWidgetItem(concat_text)
        item.setTextAlignment(Qt.AlignCenter)

        self.tableWidgetCriteria.setItem(row_count, 0, item)
