# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDockWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QFont  
from qgis.PyQt import uic
from qgis.core import QgsProject, QgsVectorLayer, QgsFeatureRequest
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from datetime import datetime
import csv

from ..tools.qgisred_utils import QGISRedUtils

# load UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),"qgisred_statisticsandgraphs_dock.ui"))

class QGISRedStatisticsAndPlotsDock(QDockWidget, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(QGISRedStatisticsAndPlotsDock, self).__init__(parent or iface.mainWindow())
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()