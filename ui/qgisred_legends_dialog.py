# -*- coding: utf-8 -*-

# Standard library imports
import os

# Third-party imports
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget
from PyQt5 import sip
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QVariant

# QGIS imports
from qgis.core import (QgsLayerTreeGroup, QgsLayerTreeLayer, QgsLayerTreeNode, 
                       QgsProject, QgsVectorFileWriter, QgsVectorLayer, 
                       QgsMessageLog, Qgis, QgsPalLayerSettings, 
                       QgsVectorLayerSimpleLabeling, QgsTextFormat,
                       QgsFeatureRenderer, QgsGraduatedSymbolRenderer,
                       QgsCategorizedSymbolRenderer)
from qgis.utils import iface

# Local imports
from ..tools.qgisred_utils import QGISRedUtils

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_legends_dialog.ui"))

class QGISRedLegendsDialog(QDialog, FORM_CLASS):
    # Class constants for field types
    FIELD_TYPE_NUMERIC = 'numeric'
    FIELD_TYPE_CATEGORICAL = 'categorical'
    FIELD_TYPE_UNKNOWN = 'unknown'
    
    def __init__(self, parent=None):
        """Constructor."""
        super(QGISRedLegendsDialog, self).__init__(parent)
        self.setupUi(self)
        
        # Initialize class variables for field type control
        self.current_field_type = self.FIELD_TYPE_UNKNOWN
        self.current_field_name = None
        self.current_layer = None
        
        self.config()
        
        # Set initial UI state
        self.gbLegends.setEnabled(bool(self.cbLegendLayer.currentLayer()))
        self.initializeUIVisibility()

        # --- Connect signals for widgets ON THIS TAB ---
        self.cbLegendLayer.layerChanged.connect(self.onLayerChanged)
        self.btApplyLegend.clicked.connect(self.applyLegend)
        self.btCancelLegend.clicked.connect(self.reject) # Closes the whole dialog

        # Connect classification buttons (numeric only)
        self.btIntervals.clicked.connect(self.classifyEqualInterval)
        self.btQuantiles.clicked.connect(self.classifyQuantiles)
        self.btBreaks.clicked.connect(self.classifyNaturalBreaks)
        
        # Connect class management buttons (both numeric and categorical)
        self.btClassPlus.clicked.connect(self.addClass)
        self.btClassMinus.clicked.connect(self.removeClass)
        
        # Add connections for other buttons as needed...
        self.btLoadDefault.clicked.connect(self.loadDefaultStyle)
        self.btSaveGlobal.clicked.connect(self.saveGlobalStyle)

    def config(self):
        iconPath = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconThematicMaps.png')
        self.setWindowIcon(QIcon(iconPath))
    
    def initializeUIVisibility(self):
        """
        Initialize the visibility of UI elements at startup.
        All classification-related buttons should be hidden initially.
        """
        # Hide all classification buttons initially
        if hasattr(self, 'btIntervals'):
            self.btIntervals.setVisible(False)
        if hasattr(self, 'btQuantiles'):
            self.btQuantiles.setVisible(False)
        if hasattr(self, 'btBreaks'):
            self.btBreaks.setVisible(False)
        if hasattr(self, 'btClassPlus'):
            self.btClassPlus.setVisible(False)
        if hasattr(self, 'btClassMinus'):
            self.btClassMinus.setVisible(False)
        if hasattr(self, 'labelClass'):
            self.labelClass.setVisible(False)
    
    def detectFieldType(self, layer):
        """
        Detect if the layer's symbology field is numeric or categorical.
        Also detects the field being used for symbology if any.
        
        Args:
            layer: QgsVectorLayer object
            
        Returns:
            tuple: (field_type, field_name)
        """
        if not layer:
            return self.FIELD_TYPE_UNKNOWN, None
            
        renderer = layer.renderer()
        field_name = None
        field_type = self.FIELD_TYPE_UNKNOWN
        
        # Check if it's a graduated renderer (numeric)
        if isinstance(renderer, QgsGraduatedSymbolRenderer):
            field_name = renderer.classAttribute()
            field_type = self.FIELD_TYPE_NUMERIC
            QgsMessageLog.logMessage(
                f"Detected graduated symbology on field '{field_name}'", 
                "QGISRed", Qgis.Info
            )
            
        # Check if it's a categorized renderer (categorical)
        elif isinstance(renderer, QgsCategorizedSymbolRenderer):
            field_name = renderer.classAttribute()
            # Further check if the field itself is numeric or not
            if field_name:
                fields = layer.fields()
                field = fields.field(field_name)
                if field:
                    field_type_variant = field.type()
                    if field_type_variant in [QVariant.Int, QVariant.Double, 
                                             QVariant.LongLong]:
                        # Numeric field but with categorized renderer
                        field_type = self.FIELD_TYPE_NUMERIC
                    else:
                        field_type = self.FIELD_TYPE_CATEGORICAL
            else:
                field_type = self.FIELD_TYPE_CATEGORICAL
                
            QgsMessageLog.logMessage(
                f"Detected categorized symbology on field '{field_name}' (type: {field_type})", 
                "QGISRed", Qgis.Info
            )
        else:
            # Single symbol or other renderer type
            QgsMessageLog.logMessage(
                "No graduated or categorized symbology detected", 
                "QGISRed", Qgis.Info
            )
            
        return field_type, field_name
    
    def detectFieldTypeFromAttribute(self, layer, field_name):
        """
        Detect if a specific field is numeric or categorical based on its data type.
        
        Args:
            layer: QgsVectorLayer object
            field_name: Name of the field to check
            
        Returns:
            str: Field type (numeric, categorical, or unknown)
        """
        if not layer or not field_name:
            return self.FIELD_TYPE_UNKNOWN
            
        fields = layer.fields()
        field_idx = fields.indexOf(field_name)
        
        if field_idx >= 0:
            field = fields.field(field_idx)
            field_type = field.type()
            
            # Check if it's a numeric type
            if field_type in [QVariant.Int, QVariant.Double, QVariant.LongLong]:
                return self.FIELD_TYPE_NUMERIC
            # Check if it's a string/text type
            elif field_type in [QVariant.String]:
                return self.FIELD_TYPE_CATEGORICAL
            # Check if it's a boolean
            elif field_type == QVariant.Bool:
                return self.FIELD_TYPE_CATEGORICAL
            else:
                return self.FIELD_TYPE_UNKNOWN
        
        return self.FIELD_TYPE_UNKNOWN
    
    def updateUIBasedOnFieldType(self):
        """
        Show/hide UI elements based on the current field type.
        Numeric: shows btIntervals, btQuantiles, btBreaks, btClassPlus, btClassMinus, labelClass
        Categorical: shows only btClassPlus, btClassMinus, labelClass
        """
        is_numeric = (self.current_field_type == self.FIELD_TYPE_NUMERIC)
        is_categorical = (self.current_field_type == self.FIELD_TYPE_CATEGORICAL)
        has_field = is_numeric or is_categorical
        
        # Classification method buttons - visible only for numeric
        if hasattr(self, 'btIntervals'):
            self.btIntervals.setVisible(is_numeric)
            self.btIntervals.setEnabled(is_numeric)
            
        if hasattr(self, 'btQuantiles'):
            self.btQuantiles.setVisible(is_numeric)
            self.btQuantiles.setEnabled(is_numeric)
            
        if hasattr(self, 'btBreaks'):
            self.btBreaks.setVisible(is_numeric)
            self.btBreaks.setEnabled(is_numeric)
        
        # Class management buttons - visible for both numeric and categorical
        if hasattr(self, 'btClassPlus'):
            self.btClassPlus.setVisible(has_field)
            self.btClassPlus.setEnabled(has_field)
            
        if hasattr(self, 'btClassMinus'):
            self.btClassMinus.setVisible(has_field)
            self.btClassMinus.setEnabled(has_field)
            
        if hasattr(self, 'labelClass'):
            self.labelClass.setVisible(has_field)
            # Update label text based on field type
            if is_numeric:
                self.labelClass.setText(self.tr("Classes (Numeric)"))
            elif is_categorical:
                self.labelClass.setText(self.tr("Classes (Categorical)"))
            else:
                self.labelClass.setText(self.tr("Classes"))
        
        # Update status message
        status_msg = f"Field type: {self.current_field_type}"
        if self.current_field_name:
            status_msg += f" (Field: {self.current_field_name})"
        
        QgsMessageLog.logMessage(status_msg, "QGISRed", Qgis.Info)
    
    def onLayerChanged(self, layer):
        """
        Handle layer change event. Detects field type and updates UI accordingly.
        """
        if layer and isinstance(layer, QgsVectorLayer):
            QgsMessageLog.logMessage(
                f"Legend tab: Layer '{layer.name()}' selected.", 
                "QGISRed", Qgis.Info
            )
            
            # Store current layer
            self.current_layer = layer
            
            # Detect field type from current symbology
            self.current_field_type, self.current_field_name = self.detectFieldType(layer)
            
            # Enable legend group and update title
            self.gbLegends.setEnabled(True)
            self.gbLegends.setTitle(self.tr(f"Legend for {layer.name()}"))
            
            # Update UI based on detected field type
            self.updateUIBasedOnFieldType()
            
            # Log the detection results
            print(f"Legend tab: Layer '{layer.name()}' selected.")
            print(f"Field type: {self.current_field_type}, Field name: {self.current_field_name}")
            
            # TODO: Add logic to populate the table view (self.tableView)
            # You might want to populate different data based on field type
            if self.current_field_type == self.FIELD_TYPE_NUMERIC:
                self.populateNumericLegend()
            elif self.current_field_type == self.FIELD_TYPE_CATEGORICAL:
                self.populateCategoricalLegend()
            else:
                # Hide all classification-related buttons when no proper symbology is detected
                self.hideAllClassificationButtons()
        else:
            self.gbLegends.setEnabled(False)
            self.gbLegends.setTitle(self.tr("Legend"))
            self.current_layer = None
            self.current_field_type = self.FIELD_TYPE_UNKNOWN
            self.current_field_name = None
            self.updateUIBasedOnFieldType()
    
    def hideAllClassificationButtons(self):
        """
        Hide all classification buttons when no graduated or categorized symbology is detected.
        This is called when a layer has single symbol or other renderer types.
        """
        # Hide numeric-only buttons
        if hasattr(self, 'btIntervals'):
            self.btIntervals.setVisible(False)
        if hasattr(self, 'btQuantiles'):
            self.btQuantiles.setVisible(False)
        if hasattr(self, 'btBreaks'):
            self.btBreaks.setVisible(False)
        
        # Hide class management buttons
        if hasattr(self, 'btClassPlus'):
            self.btClassPlus.setVisible(False)
        if hasattr(self, 'btClassMinus'):
            self.btClassMinus.setVisible(False)
        if hasattr(self, 'labelClass'):
            self.labelClass.setVisible(False)
        
        QgsMessageLog.logMessage(
            "Layer has no graduated or categorized symbology - hiding classification controls", 
            "QGISRed", Qgis.Info
        )
    
    def populateNumericLegend(self):
        """
        Populate the legend table for numeric fields.
        Shows ranges, colors, and labels for graduated symbology.
        """
        if not self.current_layer:
            return
            
        renderer = self.current_layer.renderer()
        if isinstance(renderer, QgsGraduatedSymbolRenderer):
            # Get the ranges
            ranges = renderer.ranges()
            QgsMessageLog.logMessage(
                f"Populating numeric legend with {len(ranges)} classes", 
                "QGISRed", Qgis.Info
            )
            # TODO: Populate your table view with the ranges
            # Each range has: range.lowerValue(), range.upperValue(), 
            # range.label(), range.symbol()
    
    def populateCategoricalLegend(self):
        """
        Populate the legend table for categorical fields.
        Shows categories, colors, and labels for categorized symbology.
        """
        if not self.current_layer:
            return
            
        renderer = self.current_layer.renderer()
        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            # Get the categories
            categories = renderer.categories()
            QgsMessageLog.logMessage(
                f"Populating categorical legend with {len(categories)} classes", 
                "QGISRed", Qgis.Info
            )
            # TODO: Populate your table view with the categories
            # Each category has: category.value(), category.label(), 
            # category.symbol()

    def applyLegend(self):
        """Apply legend settings to the selected layer."""
        selectedLayer = self.cbLegendLayer.currentLayer()
        if not selectedLayer:
            QMessageBox.warning(self, "No Layer", "Please select a layer first.")
            return
            
        QgsMessageLog.logMessage(
            f"Applying legend to '{selectedLayer.name()}' (Field type: {self.current_field_type})...", 
            "QGISRed", Qgis.Info
        )
        
        # Different logic based on field type
        if self.current_field_type == self.FIELD_TYPE_NUMERIC:
            self.applyNumericLegend(selectedLayer)
        elif self.current_field_type == self.FIELD_TYPE_CATEGORICAL:
            self.applyCategoricalLegend(selectedLayer)
        else:
            QMessageBox.information(
                self, 
                "No Symbology", 
                "The selected layer doesn't have graduated or categorized symbology."
            )
        
        print(f"Apply Legend button clicked! Field type: {self.current_field_type}")
    
    def applyNumericLegend(self, layer):
        """Apply numeric (graduated) legend to the layer."""
        # TODO: Implement the logic to apply graduated symbology
        QgsMessageLog.logMessage("Applying numeric legend...", "QGISRed", Qgis.Info)
    
    def applyCategoricalLegend(self, layer):
        """Apply categorical legend to the layer."""
        # TODO: Implement the logic to apply categorized symbology
        QgsMessageLog.logMessage("Applying categorical legend...", "QGISRed", Qgis.Info)

    def classifyEqualInterval(self):
        """Apply equal interval classification (only for numeric fields)."""
        if self.current_field_type != self.FIELD_TYPE_NUMERIC:
            QMessageBox.warning(
                self, 
                "Invalid Field Type", 
                "Equal interval classification requires a numeric field."
            )
            return
        # TODO: Implement equal interval classification
        QgsMessageLog.logMessage("Applying equal interval classification...", "QGISRed", Qgis.Info)
        
    def classifyQuantiles(self):
        """Apply quantile classification (only for numeric fields)."""
        if self.current_field_type != self.FIELD_TYPE_NUMERIC:
            QMessageBox.warning(
                self, 
                "Invalid Field Type", 
                "Quantile classification requires a numeric field."
            )
            return
        # TODO: Implement quantile classification
        QgsMessageLog.logMessage("Applying quantile classification...", "QGISRed", Qgis.Info)

    def classifyNaturalBreaks(self):
        """Apply natural breaks classification (only for numeric fields)."""
        if self.current_field_type != self.FIELD_TYPE_NUMERIC:
            QMessageBox.warning(
                self, 
                "Invalid Field Type", 
                "Natural breaks classification requires a numeric field."
            )
            return
        # TODO: Implement natural breaks classification
        QgsMessageLog.logMessage("Applying natural breaks classification...", "QGISRed", Qgis.Info)

    def saveGlobalStyle(self):
        """Save the current style as global default."""
        if not self.current_layer:
            QMessageBox.warning(self, "No Layer", "Please select a layer first.")
            return
        # TODO: Implement save global style
        QgsMessageLog.logMessage(
            f"Saving global style for field type: {self.current_field_type}", 
            "QGISRed", Qgis.Info
        )

    def loadDefaultStyle(self):
        """Load the default style for the current field type."""
        if not self.current_layer:
            QMessageBox.warning(self, "No Layer", "Please select a layer first.")
            return
        # TODO: Implement load default style based on field type
        QgsMessageLog.logMessage(
            f"Loading default style for field type: {self.current_field_type}", 
            "QGISRed", Qgis.Info
        )
    
    def addClass(self):
        """
        Add a new class to the legend.
        Works for both numeric (adds a range) and categorical (adds a category) fields.
        """
        if not self.current_layer:
            QMessageBox.warning(self, "No Layer", "Please select a layer first.")
            return
        
        if self.current_field_type == self.FIELD_TYPE_NUMERIC:
            # Add a new numeric range
            QgsMessageLog.logMessage("Adding new numeric class/range...", "QGISRed", Qgis.Info)
            # TODO: Implement logic to add a new range to the table
            # This might involve:
            # - Getting current ranges from the table
            # - Adding a new row with default values
            # - Updating the table view
            
        elif self.current_field_type == self.FIELD_TYPE_CATEGORICAL:
            # Add a new category
            QgsMessageLog.logMessage("Adding new categorical class...", "QGISRed", Qgis.Info)
            # TODO: Implement logic to add a new category to the table
            # This might involve:
            # - Prompting for a new category value
            # - Adding a new row to the table
            # - Assigning a default color
            
        else:
            QMessageBox.information(
                self,
                "No Field Selected",
                "Please select a layer with graduated or categorized symbology first."
            )
    
    def removeClass(self):
        """
        Remove a selected class from the legend.
        Works for both numeric (removes a range) and categorical (removes a category) fields.
        """
        if not self.current_layer:
            QMessageBox.warning(self, "No Layer", "Please select a layer first.")
            return
        
        if self.current_field_type == self.FIELD_TYPE_NUMERIC:
            # Remove selected numeric range
            QgsMessageLog.logMessage("Removing numeric class/range...", "QGISRed", Qgis.Info)
            # TODO: Implement logic to remove selected range from the table
            # This might involve:
            # - Getting selected row from table
            # - Confirming deletion
            # - Removing the row
            # - Recalculating ranges if needed
            
        elif self.current_field_type == self.FIELD_TYPE_CATEGORICAL:
            # Remove selected category
            QgsMessageLog.logMessage("Removing categorical class...", "QGISRed", Qgis.Info)
            # TODO: Implement logic to remove selected category from the table
            # This might involve:
            # - Getting selected row from table
            # - Confirming deletion
            # - Removing the row
            
        else:
            QMessageBox.information(
                self,
                "No Field Selected",
                "Please select a layer with graduated or categorized symbology first."
            )