# -*- coding: utf-8 -*-
import os
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtWidgets import QDockWidget, QMessageBox, QLineEdit
from qgis.PyQt import uic
from PyQt5.QtCore import Qt
from qgis.PyQt.QtCore import pyqtSlot
from qgis.core import QgsProject, QgsGeometry, QgsPointXY, QgsRectangle, QgsVectorLayer, QgsSettings
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView
from qgis.utils import iface
from qgis.gui import QgsHighlight
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_elementsproperty_dialog.ui"))

class QGISRedElementsPropertyDock(QDockWidget, FORM_CLASS):
    _instance = None
    
    @classmethod
    def getInstance(cls, parent=None):
        if cls._instance is None:
            cls._instance = cls(parent)
        else:
            print("[DEBUG] QGISRedElementsPropertyDock instance already exists. Returning the same instance.")
        return cls._instance

    def __init__(self, parent=None):
        if QGISRedElementsPropertyDock._instance is not None:
            raise Exception("QGISRedElementsPropertyDock is a singleton! Use getInstance() instead.")
            
        super(QGISRedElementsPropertyDock, self).__init__(parent)
        self.setupUi(self)
        
        self.setObjectName("QGISRedElementsPropertyDock")
        self.setFloating(False)
        
        print("[DEBUG] QGISRedElementsPropertyDock initialized.")

        self.singular_forms = {
            self.tr("Pipes"): self.tr("Pipe"),
            self.tr("Junctions"): self.tr("Junction"),
            self.tr("Multiple Demands"): self.tr("Multiple Demand"),
            self.tr("Reservoirs"): self.tr("Reservoir"),
            self.tr("Tanks"): self.tr("Tank"),
            self.tr("Pumps"): self.tr("Pump"),
            self.tr("Valves"): self.tr("Valve"),
            self.tr("Sources"): self.tr("Source"),
            self.tr("Service Connections"): self.tr("Service Connection"),
            self.tr("Isolation Valves"): self.tr("Isolation Valve"),
            self.tr("Meters"): self.tr("Meter")
        }

        self.original_ids = []
        self.adjacent_highlights = []
        self.main_highlight = None
        self.current_selected_highlight = None 
        
        self.setDockStyle()
        
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)

        self.setupConnections()

        settings = QgsSettings()
        if settings.contains("QGISRed/ElementsData/geometry"):
            print("[DEBUG] Restoring geometry for QGISRedElementsPropertyDock.")
            self.restoreGeometry(settings.value("QGISRed/ElementsData/geometry"))
    
    def setDockStyle(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconElementsProperties.png')
        self.setWindowIcon(QIcon(icon_path))

    def setupConnections(self):
        print("[DEBUG] Setup connections in QGISRedElementsPropertyDock.")
        # Add signal/slot connections here if needed

    def clearHighlights(self):
        # Placeholder for highlight cleanup
        print("[DEBUG] clearHighlights called in QGISRedElementsPropertyDock.")

    def clearAllLayerSelections(self):
        print("[DEBUG] clearAllLayerSelections called.")
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                lyr.removeSelection()

    def loadFeature(self, layer, feature):
        print(f"[DEBUG] loadFeature called. Layer: {layer.name()}, Feature ID: {feature.id()}")
        self.currentLayer = layer
        self.currentFeature = feature
        
        # Select the feature in its layer
        layer.selectByIds([feature.id()])
        
        # Populate the data table widget with feature attributes
        self.populatedataTableWidget()

        # Determine the singular form of the layer name if available
        singular_layer_name = self.singular_forms.get(layer.name(), layer.name())
        
        # Update the dock widget's title to "SingularName <feature id>"
        feature_id = feature.attribute("Id")
        self.setWindowTitle(f"{singular_layer_name} {feature_id}")

    def setupTabs(self, visible_tabs):
        print("[DEBUG] setupTabs called with visible_tabs:", visible_tabs)

        # Map from your attribute name to the actual tab widget instance
        # (assuming self.tabData, self.tabResults, etc. are pages added to self.tabWidget)
        tabs_info = {
            "tabData": self.tabData,
            "tabResults": self.tabResults,
            "tabCurves": self.tabCurves,
            "tabPatterns": self.tabPatterns,
            "tabControls": self.tabControls
        }

        # Iterate over each known tab name and its corresponding widget
        for tab_name, tab_widget in tabs_info.items():
            if tab_widget is None:
                print(f"[DEBUG] No widget found for '{tab_name}'. Skipping.")
                continue
            
            # Find the tab's index in the QTabWidget
            tab_index = self.tabWidget.indexOf(tab_widget)
            if tab_index == -1:
                print(f"[DEBUG] Widget '{tab_name}' not found in tabWidget. Skipping.")
                continue
            
            # Determine desired visibility based on whether the tab_name is in visible_tabs
            is_visible = tab_name in visible_tabs
            
            # Use QTabWidget's built-in method to show/hide the tab
            self.tabWidget.setTabVisible(tab_index, is_visible)
            
            print(f"[DEBUG] Setting tab '{tab_name}' visibility to {is_visible}")


    def handlePipes(self, layer, feature, tabs):
        print("[DEBUG] handlePipes called.")
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)
    
    def handleValves(self, layer, feature, tabs):
        print("[DEBUG] handleValves called.")
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)

    def handlePumps(self, layer, feature, tabs):
        print("[DEBUG] handlePumps called.")
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)
    
    def handleJunctions(self, layer, feature, tabs):
        print("[DEBUG] handleJunctions called.")
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)
    
    def handleTanks(self, layer, feature, tabs):
        print("[DEBUG] handleTanks called.")
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)
    
    def handleReservoirs(self, layer, feature, tabs):
        print("[DEBUG] handleReservoirs called.")
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)

    def populatedataTableWidget(self):
        # Check that the widget exists
        if not hasattr(self, 'dataTableWidget'):
            print("[DEBUG] dataTableWidget widget not found!")
            return

        # Clear any existing content
        self.dataTableWidget.clearContents()

        # Get the fields and corresponding attribute values
        fields = self.currentLayer.fields()  # QgsFields object
        attributes = self.currentFeature.attributes()  # List of attribute values

        # Set up the table: two columns ("Field" and "Value")
        num_fields = len(fields)
        self.dataTableWidget.setRowCount(num_fields)
        self.dataTableWidget.setColumnCount(2)
        self.dataTableWidget.setHorizontalHeaderLabels(["Field", "Value"])

        # Ensure columns stretch to occupy available horizontal space
        self.dataTableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Hide vertical header indexes
        self.dataTableWidget.verticalHeader().setVisible(False)

        # Loop over the fields and populate the table rows
        for row, field in enumerate(fields):
            field_name = field.name()
            field_value = attributes[row]

            # Create table items for each column
            field_item = QTableWidgetItem(field_name)
            value_item = QTableWidgetItem(str(field_value))

            # Add items to the table widget
            self.dataTableWidget.setItem(row, 0, field_item)
            self.dataTableWidget.setItem(row, 1, value_item)
            
    def closeEvent(self, event):
        print("[DEBUG] closeEvent triggered in QGISRedElementsPropertyDock.")
        settings = QgsSettings()
        settings.setValue("QGISRed/ElementsData/geometry", self.saveGeometry())
        
        self.clearHighlights()
        self.clearAllLayerSelections()
        
        QGISRedElementsPropertyDock._instance = None
        super(QGISRedElementsPropertyDock, self).closeEvent(event)

    def onProjectClosed(self):
        print("[DEBUG] onProjectClosed slot called.")
        self.clearHighlights()
        self.clearAllLayerSelections()

    @pyqtSlot()
    def clearAll(self):
        print("[DEBUG] clearAll slot triggered.")
        self.clearHighlights()
        self.clearAllLayerSelections()
