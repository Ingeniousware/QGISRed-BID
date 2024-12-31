# -*- coding: utf-8 -*-
import os
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtWidgets import QDockWidget, QMessageBox, QLineEdit
from qgis.PyQt import uic
from PyQt5.QtCore import Qt
from qgis.PyQt.QtCore import pyqtSlot
from qgis.core import QgsProject, QgsGeometry, QgsPointXY, QgsRectangle, QgsVectorLayer, QgsSettings
from qgis.utils import iface
from qgis.gui import QgsHighlight

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_elementsData_dock.ui"))

class QGISRedElementsDataDock(QDockWidget, FORM_CLASS):
    _instance = None
    
    @classmethod
    def getInstance(cls, parent=None):
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance

    def __init__(self, parent=None):
        if QGISRedElementsDataDock._instance is not None:
            raise Exception("QGISRedElementsDataDock is a singleton! Use getInstance() instead.")
            
        super(QGISRedElementsDataDock, self).__init__(parent)
        self.setupUi(self)
        
        # Prevent stacking
        self.setObjectName("QGISRedElementsDataDock")
        
        # Dock widget is not floating by default
        self.setFloating(False)
        
        # if parent:
        #     parent.addDockWidget(Qt.LeftDockWidgetArea, self)
        
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
        self.current_selected_highlight = None 
        
        self.setDockStyle()
        
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)

        self.setupConnections()
        #self.initializeElementTypes()

        settings = QgsSettings()
        if settings.contains("QGISRed/ElementsData/geometry"):
            self.restoreGeometry(settings.value("QGISRed/ElementsData/geometry"))

        
    def setupConnections(self):
        ...

    def clearHighlights(self):
        ...
    
    def setDockStyle(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconElementsProperties.png')
        self.setWindowIcon(QIcon(icon_path))

        # search_icon = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFilter.png'))
        # self.leElementMask.addAction(search_icon, QLineEdit.LeadingPosition)

        # self.cbElementType.setStyleSheet("QComboBox { background-color: white; }")
        # self.cbElementId.setStyleSheet("QComboBox { background-color: white; }")
        
    def clearAllLayerSelections(self):
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                lyr.removeSelection()


    def loadFeature(self, layer, feature):
        self.currentLayer = layer
        self.currentFeature = feature
        
        layer.selectByIds([feature.id()])
        
        #self.clearHighlights()

    def closeEvent(self, event):
        # Save geometry
        settings = QgsSettings()
        settings.setValue("QGISRed/ElementsData/geometry", self.saveGeometry())
        
        self.clearHighlights()
        self.clearAllLayerSelections()
        
        # Clear instance
        QGISRedElementsDataDock._instance = None
        
        super(QGISRedElementsDataDock, self).closeEvent(event)

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