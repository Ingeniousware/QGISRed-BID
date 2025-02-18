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

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_elementsproperty_dialog.ui"))

class QGISRedElementsPropertyDock(QDockWidget, FORM_CLASS):
    _instance = None
    
    @classmethod
    def getInstance(cls, parent=None):
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance

    def __init__(self, parent=None):
        if QGISRedElementsPropertyDock._instance is not None:
            raise Exception("QGISRedElementsPropertyDock is a singleton! Use getInstance() instead.")
            
        super(QGISRedElementsPropertyDock, self).__init__(parent)
        self.setupUi(self)
        
        self.setObjectName("QGISRedElementsPropertyDock")
        self.setFloating(False)
        
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
            self.restoreGeometry(settings.value("QGISRed/ElementsData/geometry"))
    
    def setupConnections(self):
        pass

    def clearHighlights(self):
        pass
    
    def setDockStyle(self):
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconElementsProperties.png')
        self.setWindowIcon(QIcon(icon_path))
        
    def clearAllLayerSelections(self):
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                lyr.removeSelection()

    def loadFeature(self, layer, feature):
        self.currentLayer = layer
        self.currentFeature = feature
        layer.selectByIds([feature.id()])

    def setupTabs(self, visible_tabs):
        all_tabs = {
            "tabData": getattr(self, "tabData", None),
            "tabResults": getattr(self, "tabResults", None),
            "tabCurves": getattr(self, "tabCurves", None),
            "tabPatterns": getattr(self, "tabPatterns", None),
            "tabControls": getattr(self, "tabControls", None)
        }
        for tab_name, widget in all_tabs.items():
            if widget is not None:
                # Show the tab only if its key is in visible_tabs; otherwise hide it.
                widget.setVisible(tab_name in visible_tabs)

    def handlePipes(self, layer, feature, tabs):
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)
    
    def handleValves(self, layer, feature, tabs):
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)

    def handlePumps(self, layer, feature, tabs):
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)
    
    def handleJunctions(self, layer, feature, tabs):
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)
    
    def handleTanks(self, layer, feature, tabs):
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)
    
    def handleReservoirs(self, layer, feature, tabs):
        self.setupTabs(tabs)
        self.loadFeature(layer, feature)

    def closeEvent(self, event):
        settings = QgsSettings()
        settings.setValue("QGISRed/ElementsData/geometry", self.saveGeometry())
        
        self.clearHighlights()
        self.clearAllLayerSelections()
        
        QGISRedElementsPropertyDock._instance = None
        super(QGISRedElementsPropertyDock, self).closeEvent(event)

    def onProjectClosed(self):
        self.clearHighlights()
        self.clearAllLayerSelections()

    @pyqtSlot()
    def clearAll(self):
        self.clearHighlights()
        self.clearAllLayerSelections()
