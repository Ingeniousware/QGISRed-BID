# Third-party imports
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (QDialog, QMessageBox, QWidget, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QComboBox, QLineEdit, QPushButton,
                             QCheckBox, QHBoxLayout, QAbstractItemView, QDialogButtonBox, 
                             QDoubleSpinBox, QLabel, QVBoxLayout)

# Third-party imports
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QHBoxLayout

# QGIS imports
from qgis.core import QgsFillSymbol
from qgis.gui import QgsSymbolButton, QgsColorButton

# Third-party imports
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QHBoxLayout

# QGIS imports
from qgis.core import QgsSymbol, QgsFillSymbol, QgsMarkerSymbol, QgsLineSymbol
from qgis.gui import QgsSymbolButton, QgsColorButton

class RangeEditDialog(QDialog):
    """A simple dialog for editing a numeric range (lower and upper bounds)."""
    def __init__(self, lowerValue, upperValue, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Edit Range"))
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(self.tr("Lower Value:")))
        self.lowerSpinBox = QDoubleSpinBox()
        self.lowerSpinBox.setRange(-1e12, 1e12)
        self.lowerSpinBox.setDecimals(4)
        self.lowerSpinBox.setValue(lowerValue)
        layout.addWidget(self.lowerSpinBox)

        layout.addWidget(QLabel(self.tr("Upper Value:")))
        self.upperSpinBox = QDoubleSpinBox()
        self.upperSpinBox.setRange(-1e12, 1e12)
        self.upperSpinBox.setDecimals(4)
        self.upperSpinBox.setValue(upperValue)
        layout.addWidget(self.upperSpinBox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def getValues(self):
        """Returns the current values of the spin boxes."""
        return self.lowerSpinBox.value(), self.upperSpinBox.value()

class SymbolAsColorButton(QWidget):
    """
    A custom widget that displays as a QgsSymbolButton but opens a
    QgsColorButton dialog on click to edit the symbol's color.
    """
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)

        # This internal QgsColorButton handles the color dialog logic.
        # It's not added to the layout, so it remains hidden from the user.
        self.colorButton = QgsColorButton()

        # This is the button the user will see and interact with.
        self.symbolButton = QgsSymbolButton()
        # Ensure the symbol preview is appropriate for a fill symbol
        self.symbolButton.setSymbolType(QgsSymbolButton.Fill)

        # Set up a layout to hold the visible symbol button
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Use all available space
        layout.addWidget(self.symbolButton)
        self.setLayout(layout)

        # --- Connections ---
        # 1. When the visible symbol button is clicked, trigger the hidden color button's dialog.
        self.symbolButton.clicked.connect(self.colorButton.showColorDialog)
        # 2. When the color is changed via the dialog, update the symbol's appearance.
        self.colorButton.colorChanged.connect(self.updateSymbolFromColor)

        # Initialize with a default color, which will also set the initial symbol display
        self.setColor(QColor('red'))

    def updateSymbolFromColor(self, color):
        """Updates the symbol on the QgsSymbolButton based on the selected color."""
        # Create a new simple fill symbol using the chosen color
        symbol = QgsFillSymbol.createSimple({'color': color.name()})
        self.symbolButton.setSymbol(symbol)

    def setColor(self, color):
        """
        Public method to set the current color.
        Accepts a QColor object or a color name string (e.g., 'blue', '#FF0000').
        """
        if isinstance(color, str):
            color = QColor(color)
        self.colorButton.setColor(color)
        # Setting the color on the colorButton automatically triggers its
        # colorChanged signal, which in turn calls our updateSymbolFromColor slot.

    def color(self):
        """Public method to get the current QColor."""
        return self.colorButton.color()

    def symbol(self):
        """Public method to get the current QgsSymbol."""
        return self.symbolButton.symbol()