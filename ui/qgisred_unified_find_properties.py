# -*- coding: utf-8 -*-
import os
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QMessageBox, QLineEdit
from PyQt5.QtWidgets import QListWidgetItem, QTableWidgetItem, QHeaderView, QStyle, QAbstractItemView, QFrame 
from PyQt5.QtCore import Qt, QEvent, pyqtSlot
from qgis.PyQt import uic
from qgis.core import QgsProject, QgsVectorLayer, QgsSettings, QgsGeometry, QgsPointXY, QgsRectangle, QgsFeature, QgsLayerMetadata
from qgis.utils import iface
from qgis.gui import QgsHighlight
from ..tools.qgisred_utils import QGISRedUtils

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_unified_find_properties.ui"))

class QGISRedElementsExplorerDock(QDockWidget, FORM_CLASS):
    _instance = None

    # ------------------------------------------------------------------------- 
    # Singleton & Initialization / Setup 
    # ------------------------------------------------------------------------- 
    @classmethod
    def getInstance(cls, canvas=None, parent=None, show_find_elements=True, show_element_properties=True):
        if cls._instance is None:
            cls._instance = cls(canvas, parent, show_find_elements, show_element_properties)
        else:
            cls._instance.setComponentVisibility(show_find_elements, show_element_properties)
        return cls._instance

    def __init__(self, canvas, parent=None, show_find_elements=True, show_element_properties=True):
        if self._instance is not None:
            raise Exception(f"{self.__class__.__name__} is a singleton! Use getInstance() instead.")
        super(self.__class__, self).__init__(parent)
        self.setupUi(self)
        self.setObjectName(self.__class__.__name__)
        self.setFloating(False)
        if parent:
            parent.addDockWidget(Qt.LeftDockWidgetArea, self)

        self.canvas = canvas
        self.find_elements_visible = show_find_elements
        self.element_properties_visible = show_element_properties

        # Element types, identifiers, and singular forms
        self.element_types = [
            self.tr('Pipes'),
            self.tr('Junctions'),
            self.tr('Multiple Demands'),
            self.tr('Reservoirs'),
            self.tr('Tanks'),
            self.tr('Pumps'),
            self.tr('Valves'),
            self.tr('Sources'),
            self.tr('Service Connections'),
            self.tr('Isolation Valves'),
            self.tr('Meters')
        ]
        
        self.element_identifiers = {
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
        
        # Used for caching element IDs and highlight objects
        self.original_ids = []
        self.adjacent_highlights = []
        self.main_highlight = None
        self.current_selected_highlight = None
        self.findElemetsdock = None
        
        self.currentLayer = None
        self.currentFeature = None
        
        # Layer groups for adjacency purposes
        self.link_layers = ["qgisred_pipes", "qgisred_pumps", "qgisred_valves"]
        self.node_layers = ["qgisred_reservoirs", "qgisred_tanks", "qgisred_junctions", 
                            "qgisred_sources", "qgisred_demands", "qgisred_meters", "qgisred_isolationvalves"]
        self.special_layers = ["qgisred_serviceconnections"]
        self.sources_and_demands = ["qgisred_sources", "qgisred_demands"]
        
        # Setup UI elements if they exist
        if hasattr(self, 'listWidget'):
            self.listWidget.installEventFilter(self)
        
        if hasattr(self, 'labelFoundElement'):
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            self.labelFoundElement.setFont(font)
            self.labelFoundElement.setWordWrap(True)
            self.labelFoundElement.setText("AAA")
        
        # if hasattr(self, 'labelFoundElementProperty'):
        #     font = QFont()
        #     font.setPointSize(12)
        #     font.setBold(True)
        #     self.labelFoundElementProperty.setFont(font)
        #     self.labelFoundElementProperty.setWordWrap(True)
        #     self.labelFoundElementProperty.setText("AAA")
        #     self.labelFoundElementProperty.setVisible(show_element_properties)

        # Set initial component visibility
        self.findElementsDock.setVisible(show_find_elements)
        self.elementPropertiesDock.setVisible(show_element_properties)

        self.setDockStyle()
        self.setupConnections()
        
        if hasattr(self, 'initializeCustomLayerProperties'):
            self.initializeCustomLayerProperties()
        
        if hasattr(self, 'initializeElementTypes'):
            self.initializeElementTypes()
        

        self.placeConnectedElements()

        # Restore geometry if available
        settings = QgsSettings()
        if settings.contains("QGISRed/ElementsExplorer/geometry"):
            self.restoreGeometry(settings.value("QGISRed/ElementsExplorer/geometry"))
    
    def setDockStyle(self):
        self.initFindElementsCustomTitleBar()
        self.initElementPropertiesCustomTitleBar()

        icon_name = 'iconFindElements.png' if 'Find' in self.__class__.__name__ else 'iconElementsProperties.png'
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', icon_name)
        self.setWindowIcon(QIcon(icon_path))
        
        if hasattr(self, 'leElementMask'):
            search_icon = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFilter.png'))
            self.leElementMask.addAction(search_icon, QLineEdit.LeadingPosition)
        
        if hasattr(self, 'cbElementType'):
            self.cbElementType.setStyleSheet("QComboBox { background-color: white; }")
        if hasattr(self, 'cbElementId'):
            self.cbElementId.setStyleSheet("QComboBox { background-color: white; }")

    def clearAll(self):
        self.clearHighlights()
        self.clearAllLayerSelections()
        
        # Clear UI elements if they exist
        if hasattr(self, 'leElementMask'):
            self.leElementMask.clear()
        if hasattr(self, 'cbElementId') and self.cbElementId.count() > 0:
            self.cbElementId.setCurrentIndex(0)
        if hasattr(self, 'labelFoundElement'):
            self.labelFoundElement.setText("")
        if hasattr(self, 'listWidget'):
            self.listWidget.clear()

    def clearAllLayerSelections(self):
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                lyr.removeSelection()

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
    
    def closeEvent(self, event):
        settings = QgsSettings()
        settings.setValue(f"QGISRed/ElementsExplorer/geometry", self.saveGeometry())
        
        # Disconnect signals if available
        # root = QgsProject.instance().layerTreeRoot()
        # inputs_group = root.findGroup("Inputs")
        # if inputs_group and hasattr(self, 'onLayerTreeChanged'):
        #     try:
        #         inputs_group.addedChildren.disconnect(self.onLayerTreeChanged)
        #         inputs_group.removedChildren.disconnect(self.onLayerTreeChanged)
        #         for layer_node in inputs_group.findLayers():
        #             if hasattr(self, 'disconnectLayerSignals'):
        #                 self.disconnectLayerSignals(layer_node.layer())
        #     except Exception:
        #         pass
        
        self.clearHighlights()
        self.clearAllLayerSelections()
        self.__class__._instance = None
        super(self.__class__, self).closeEvent(event)

    def setupConnections(self):
        ...
        # Connect signals for UI elements if they exist
        # if hasattr(self, 'cbElementType'):
        #     self.cbElementType.currentIndexChanged.connect(self.updateElementIds)
        # if hasattr(self, 'leElementMask'):
        #     self.leElementMask.textChanged.connect(self.filterElementIds)
        # if hasattr(self, 'btFind'):
        #     self.btFind.clicked.connect(self.onFindButtonClicked)
        # if hasattr(self, 'listWidget'):
        #     self.listWidget.itemClicked.connect(self.onListItemSingleClicked)
        #     self.listWidget.itemDoubleClicked.connect(self.onListItemDoubleClicked)
        # if hasattr(self, 'btClear'):
        #     self.btClear.clicked.connect(self.clearAll)
        # if hasattr(self, 'cbElementId'):
        #     self.cbElementId.currentIndexChanged.connect(self.onElementIdChanged)

        # Connect project signals
        # project = QgsProject.instance()
        # if hasattr(self, 'onLayerTreeChanged'):
        #     project.layersAdded.connect(self.onLayerTreeChanged)
        #     project.layersRemoved.connect(self.onLayerTreeChanged)
        # if hasattr(self, 'onProjectChanged'):
        #     project.readProject.connect(self.onProjectChanged)
        #     project.cleared.connect(self.onProjectChanged)

        # Connect input group signals
        # root = project.layerTreeRoot()
        # inputs_group = root.findGroup("Inputs")
        # if inputs_group and hasattr(self, 'onLayerTreeChanged'):
        #     inputs_group.addedChildren.connect(self.onLayerTreeChanged)
        #     inputs_group.removedChildren.connect(self.onLayerTreeChanged)
            
        #     # Connect layer signals
        #     if hasattr(self, 'connectLayerSignals'):
        #         for layer_node in inputs_group.findLayers():
        #             self.connectLayerSignals(layer_node)
    
    def getCheckedInputGroupLayers(self):
        inputs_group = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if not inputs_group:
            return []
        checked_layers = inputs_group.checkedLayers()
        ordered_layers = sorted(
            checked_layers,
            key=lambda lyr: self.element_types.index(lyr.name()) if lyr.name() in self.element_types else 999
        )
        return ordered_layers

    def onProjectClosed(self):
        self.clearHighlights()
        self.clearAllLayerSelections()
    
    @pyqtSlot()
    def toggleFloating(self):
        self.setFloating(not self.isFloating())

    # -------------------------------------------------------------------------
    # Signal Connection Helpers
    # -------------------------------------------------------------------------
    def connectLayerSignals(self, layer_node):
        try:
            layer_node.nameChanged.connect(self.onLayerTreeChanged)
            if layer_node.layer():
                layer = layer_node.layer()
                layer.dataChanged.connect(self.onLayerTreeChanged)
                layer.featureAdded.connect(self.updateElementIds)
                layer.featureDeleted.connect(self.updateElementIds)
                layer.visibilityChanged.connect(self.onLayerTreeChanged)
        except Exception:
            pass

    def disconnectLayerSignals(self, layer):
        try:
            if hasattr(layer, 'nameChanged'):
                try:
                    layer.nameChanged.disconnect(self.onLayerTreeChanged)
                except Exception:
                    pass
            if hasattr(layer, 'dataChanged'):
                try:
                    layer.dataChanged.disconnect(self.onLayerTreeChanged)
                except Exception:
                    pass
            if hasattr(layer, 'visibilityChanged'):
                try:
                    layer.visibilityChanged.disconnect(self.onLayerTreeChanged)
                except Exception:
                    pass
        except Exception:
            pass

    def initFindElementsCustomTitleBar(self):
        titleBar = QWidget(self)
        layout = QHBoxLayout(titleBar)
        layout.setContentsMargins(5, 0, 5, 0)

        self.titleLabel = QLabel("Find Elements by Id", titleBar)
        layout.addWidget(self.titleLabel)
        layout.addStretch()

        # # New Identify Button
        # self.identifyButton = QToolButton(titleBar)
        # icon_identify = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', "cursor.png"))
        # self.identifyButton.setIcon(icon_identify)
        # self.identifyButton.setToolTip("Identify Feature")
        # self.identifyButton.clicked.connect(self.openIdentifyForFindDock)
        # layout.addWidget(self.identifyButton)

        epButton = QToolButton(titleBar)
        icon_ep = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', 'iconElementsProperties.png'))
        epButton.setIcon(icon_ep)
        epButton.setToolTip("Element Properties")
        epButton.clicked.connect(self.openElementPropertiesDock)
        epButton.setCheckable(True)
        epButton.setChecked(self.element_properties_visible)
        layout.addWidget(epButton)

        # self.floatButton = QToolButton(titleBar)
        # float_icon = self.style().standardIcon(QStyle.SP_TitleBarNormalButton)
        # self.floatButton.setIcon(float_icon)
        # self.floatButton.setToolTip("Float")
        # self.floatButton.clicked.connect(self.toggleFloating)
        # layout.addWidget(self.floatButton)

        # # Close button for this dock
        # self.closeButton = QToolButton(titleBar)
        # close_icon = self.style().standardIcon(QStyle.SP_TitleBarCloseButton)
        # self.closeButton.setIcon(close_icon)
        # self.closeButton.setToolTip("Close")
        # self.closeButton.clicked.connect(self.toggleFindElementsDockVisibility)
        # layout.addWidget(self.closeButton)

        self.findElementsDock.setTitleBarWidget(titleBar)

    def initElementPropertiesCustomTitleBar(self):
        titleBar = QWidget(self)
        layout = QHBoxLayout(titleBar)
        layout.setContentsMargins(5, 0, 5, 0)

        self.titleLabel = QLabel(self.windowTitle(), titleBar)
        #self.titleLabel.setStyleSheet("font-weight: bold; font-size: 12pt;")
        #self.titleLabel.setStyleSheet("font-size: 12pt;")
        self.titleLabel.setStyleSheet("font-weight: normal")
        self.titleLabel.setText("Element Properties")
        layout.addWidget(self.titleLabel)
        layout.addStretch()

        findButton = QToolButton(titleBar)
        icon_find = QIcon(os.path.join(os.path.dirname(__file__), '..', 'images', 'iconFindElements.png'))
        findButton.setIcon(icon_find)
        findButton.setToolTip("Find Elements by ID")
        findButton.clicked.connect(self.openFindElementsDock)
        findButton.setCheckable(True)
        findButton.setChecked(self.find_elements_visible)
        layout.addWidget(findButton)

        # self.floatButton = QToolButton(titleBar)
        # float_icon = self.style().standardIcon(QStyle.SP_TitleBarNormalButton)
        # self.floatButton.setIcon(float_icon)
        # self.floatButton.setToolTip("Float")
        # self.floatButton.clicked.connect(self.toggleFloating)
        # layout.addWidget(self.floatButton)

        # self.closeButton = QToolButton(titleBar)
        # close_icon = self.style().standardIcon(QStyle.SP_TitleBarCloseButton)
        # self.closeButton.setIcon(close_icon)
        # self.closeButton.setToolTip("Close")
        # self.closeButton.clicked.connect(self.toggleElementPropertiesVisibility)
        # layout.addWidget(self.closeButton)

        self.elementPropertiesDock.setTitleBarWidget(titleBar)

    # @pyqtSlot()
    # def openElementPropertiesDock(self):
    #     from .qgisred_elementproperties_dock import QGISRedElementsPropertyDock
    #     from ..tools.qgisred_identifyFeature import QGISRedIdentifyFeature

    #     existing_docks = self.canvas.findChildren(QGISRedElementsPropertyDock)
    #     self.identifyTool = QGISRedIdentifyFeature(self.canvas)
    #     if existing_docks:
    #         dock = existing_docks[0]
    #         if dock.isVisible():
    #             dock.close()
    #         else:
    #             iface.addDockWidget(Qt.RightDockWidgetArea, dock)
    #             dock.show()
    #             dock.raise_()
    #             dock.loadFeature(self.currentLayer, self.currentFeature)
    #             self.canvas.setMapTool(self.identifyTool)
    #     else:
    #         dock = QGISRedElementsPropertyDock.getInstance()
    #         iface.addDockWidget(Qt.RightDockWidgetArea, dock)
    #         dock.loadFeature(self.currentLayer, self.currentFeature)
    #         dock.show()
    #         self.canvas.setMapTool(self.identifyTool)

    @pyqtSlot()
    def openElementPropertiesDock(self):
        """
        Handle the toggling of the Element Properties dock according to the rules.
        """
        from ..tools.qgisred_identifyFeature import QGISRedIdentifyFeature
        
        self.identifyTool = QGISRedIdentifyFeature(self.canvas)
        
        if not self._instance:
            # If EE dock doesn't exist, create it with EP visible and FE not visible
            self.setComponentVisibility(False, True)
        elif not self.element_properties_visible:
            # If EP dock is not visible, make it visible
            self.element_properties_visible = True
            self.elementPropertiesDock.show()
            self.elementPropertiesDock.raise_()
            self.placeConnectedElements()
        elif self.find_elements_visible and self.element_properties_visible:
            # If both docks are visible, hide EP
            self.element_properties_visible = False
            self.elementPropertiesDock.hide()
            self.placeConnectedElements()
        else:
            # If only EP is visible, close the EE dock entirely
            self.close()
        
        # Set the identify tool active
        self.canvas.setMapTool(self.identifyTool)

    @pyqtSlot()
    def openFindElementsDock(self):
        """
        Handle the toggling of the Find Elements dock according to the rules.
        """
        from ..tools.qgisred_identifyFeature import QGISRedIdentifyFeature
        
        self.identifyTool = QGISRedIdentifyFeature(self.canvas)
        
        if not self._instance:
            # Create new instance with FE visible and EP hidden
            self.setComponentVisibility(True, False)
        else:
            # Get current visibility states
            current_fe = self.find_elements_visible
            current_ep = self.element_properties_visible
            
            if not current_fe and not current_ep:
                # Both hidden: show FE
                self.setComponentVisibility(True, False)
            elif current_fe and current_ep:
                # Both visible: hide FE
                self.setComponentVisibility(False, True)
            elif current_fe and not current_ep:
                # Only FE visible: close entire dock
                self.close()
            else:  # EP visible, FE hidden
                # Show FE
                self.setComponentVisibility(True, True)
        
        # Set the identify tool active
        self.canvas.setMapTool(self.identifyTool)

    def toggleFindElementsDockVisibility(self):
        """
        Toggle the visibility of the Find Elements dock.
        """
        self.find_elements_visible = not self.find_elements_visible
        if self.find_elements_visible:
            self.findElementsDock.show()
        else:
            self.findElementsDock.hide()
        
        # When toggling dock visibility directly, close the entire dock
        # if neither FE nor EP is visible
        if not self.find_elements_visible and not self.element_properties_visible:
            self.close()
        else:
            self.placeConnectedElements()
    
    def toggleElementPropertiesVisibility(self):
        """
        Toggle the visibility of the Element Properties dock.
        """
        self.element_properties_visible = not self.element_properties_visible
        if self.element_properties_visible:
            self.elementPropertiesDock.show()
        else:
            self.elementPropertiesDock.hide()
        
        # When toggling dock visibility directly, close the entire dock
        # if neither FE nor EP is visible
        if not self.find_elements_visible and not self.element_properties_visible:
            self.close()
        else:
            self.placeConnectedElements()

    def removeConnectedElementsFromLayouts(self):
        """Remove connected elements from any layout they might be in"""
        # Temporarily reparent widgets to None
        self.labelAdjacentNodeLinks.setParent(None)
        self.listWidget.setParent(None)
        
        # Clean layouts in both docks
        for dock in [self.findElementsDock, self.elementPropertiesDock]:
            content = dock.widget()
            if not content:
                continue
                
            # Get main layout of dock contents
            main_layout = content.layout()
            if not main_layout:
                continue
                
            # Search through all layout items
            for i in reversed(range(main_layout.count())):
                item = main_layout.itemAt(i)
                if item and item.widget() in [self.labelAdjacentNodeLinks, self.listWidget]:
                    main_layout.removeItem(item)
                    item.widget().setParent(None)

    def placeConnectedElements(self):
        """Place connected elements under the appropriate section"""
        # Remove from any existing layout first
        self.removeConnectedElementsFromLayouts()
        
        # Determine target dock and position
        if self.element_properties_visible:
            target_dock = self.elementPropertiesDock
            position = 2  # After properties content
        else:
            target_dock = self.findElementsDock
            position = 1  # Position after labelFoundElement in findElementsDock's verticalLayout_3
            
        # Get the target layout
        content = target_dock.widget()
        main_layout = content.layout()
        
        # Create container layout
        container = QVBoxLayout()
        container.addWidget(self.labelAdjacentNodeLinks)
        container.addWidget(self.listWidget)
        
        # Insert into correct position
        main_layout.insertLayout(position, container)

        # Adjust labelFoundElement position below the line in findElementsDock when elementPropertiesDock is hidden
        if target_dock == self.findElementsDock and not self.element_properties_visible:
            # Find the line widget (assuming it's a QFrame named 'line')
            line = content.findChild(QFrame, "line")
            if line:
                line_index = main_layout.indexOf(line)
                if line_index != -1:
                    # Remove labelFoundElement from current position
                    main_layout.removeWidget(self.labelFoundElement)
                    # Insert it immediately after the line
                    main_layout.insertWidget(line_index + 1, self.labelFoundElement)
                    # Ensure the line and label are visible
                    line.show()
                    self.labelFoundElement.show()

    def setComponentVisibility(self, show_find_elements, show_element_properties):
        self.find_elements_visible = show_find_elements
        self.element_properties_visible = show_element_properties
        
        self.findElementsDock.setVisible(show_find_elements)
        self.elementPropertiesDock.setVisible(show_element_properties)
        
        self.placeConnectedElements()

    def openIdentifyForFindDock(self):
        from ..tools.qgisred_identifyFeature import QGISRedIdentifyFeature
        self.identifyTool = QGISRedIdentifyFeature(self.canvas, useFindDock=True)
        self.canvas.setMapTool(self.identifyTool)

