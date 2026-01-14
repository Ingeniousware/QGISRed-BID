# -*- coding: utf-8 -*-
from PyQt5.QtGui import QColor, QPixmap, QPainter, QIcon
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QDoubleSpinBox, QLabel,
                             QVBoxLayout, QWidget, QHBoxLayout, QCheckBox,
                             QToolButton, QPushButton, QMenu, QAction)
from PyQt5.QtCore import pyqtSignal, Qt, QEvent, QSize
from qgis.gui import QgsSymbolButton, QgsColorDialog
from qgis.core import QgsMarkerSymbol, QgsLineSymbol, QgsFillSymbol, QgsColorRamp

class QGISRedRangeEditDialog(QDialog):
    def __init__(self, lowerValue, upperValue, parent=None, unitAbbr=""):
        super().__init__(parent)
        self.unitAbbr = unitAbbr
        self.setWindowTitle(self.tr("Edit Range"))
        self.lowerSpinBox = None
        self.upperSpinBox = None
        self.initUi(lowerValue, upperValue)

    def initUi(self, lower, upper):
        layout = QVBoxLayout(self)
        lowerLabelText = self.buildLabel("Lower Value")
        upperLabelText = self.buildLabel("Upper Value")
        layout.addWidget(QLabel(lowerLabelText))

        self.lowerSpinBox = self.createSpinBox(lower)
        layout.addWidget(self.lowerSpinBox)
        layout.addWidget(QLabel(upperLabelText))

        self.upperSpinBox = self.createSpinBox(upper)
        layout.addWidget(self.upperSpinBox)
        self.addDialogButtons(layout)

    def buildLabel(self, baseText):
        if self.unitAbbr:
            return self.tr(f"{baseText} ({self.unitAbbr}):")
        return self.tr(f"{baseText}:")

    def createSpinBox(self, value):
        spinBox = QDoubleSpinBox()
        spinBox.setRange(-1e12, 1e12)
        spinBox.setDecimals(4)
        spinBox.setValue(value)
        return spinBox

    def addDialogButtons(self, layout):
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def getValues(self):
        return self.lowerSpinBox.value(), self.upperSpinBox.value()

class QGISRedSymbolColorSelector(QgsSymbolButton):
    colorChanged = pyqtSignal(QColor)

    GEOMETRY_MARKER = "marker"
    GEOMETRY_LINE = "line"
    GEOMETRY_FILL = "fill"

    DEFAULT_COLOR = QColor(19, 125, 220, 255)

    def __init__(self, parent=None, geometryHint="fill", initialColor=None,
                 allowAlpha=True, dialogTitle="Pick color", doubleClickOnly=False):
        super().__init__(parent)
        self.geometryHintValue = self.normalizeGeometryHint(geometryHint)
        self.allowAlphaEnabled = bool(allowAlpha)
        self.dialogTitle = dialogTitle
        self.doubleClickOnlyEnabled = doubleClickOnly
        self.currentColor = self.resolveInitialColor(initialColor)
        self.symbolSize = 0.0
        self.configureAppearance()
        self.applySymbol()
        self.installEventFilter(self)

    def resolveInitialColor(self, color):
        if color and isinstance(color, QColor) and color.isValid():
            return QColor(color)
        return QColor(self.DEFAULT_COLOR)

    def configureAppearance(self):
        self.setPopupMode(QToolButton.DelayedPopup)
        self.setStyleSheet(
            "QToolButton::menu-indicator { image: none; width: 0px; }"
            "QToolButton { padding-right: 4px; background-color: transparent; border: none; }"
        )
        self.setToolTip(self.tr("Click to pick a color."))
        try:
            self.setGraphicsEffect(None)
        except Exception:
            pass

    def normalizeGeometryHint(self, geometry):
        normalized = (geometry or "").strip().lower()

        if normalized in ("point", "marker", "pts"):
            return self.GEOMETRY_MARKER
        if normalized in ("line", "polyline", "ln"):
            return self.GEOMETRY_LINE
        return self.GEOMETRY_FILL

    def applySymbol(self):
        symbol = self.createSymbolForGeometry(self.geometryHintValue, self.currentColor)
        if self.symbolSize > 0:
            self.applySizeToSymbol(symbol, self.symbolSize, self.geometryHintValue == self.GEOMETRY_LINE)
        self.setSymbol(symbol)

    def createSymbolForGeometry(self, geometryType, color):
        rgbaString = self.colorToRgbaString(color)
        if geometryType == self.GEOMETRY_MARKER:
            return self.createMarkerSymbol(rgbaString)
        if geometryType == self.GEOMETRY_LINE:
            return self.createLineSymbol(rgbaString)
        return self.createFillSymbol(rgbaString)

    def colorToRgbaString(self, color):
        return f"{color.red()},{color.green()},{color.blue()},{color.alpha()}"

    def createMarkerSymbol(self, rgbaString):
        return QgsMarkerSymbol.createSimple({
            "name": "circle",
            "color": rgbaString,
            "outline_color": "0,0,0,255",
            "outline_width": "0.2"
        })

    def createLineSymbol(self, rgbaString):
        return QgsLineSymbol.createSimple({
            "color": rgbaString,
            "width": "0.8"
        })

    def createFillSymbol(self, rgbaString):
        return QgsFillSymbol.createSimple({
            "color": rgbaString,
            "outline_color": "60,60,60,255",
            "outline_width": "0.3"
        })

    def applySizeToSymbol(self, symbol, size, isWidthMode):
        if isWidthMode:
            symbol.setWidth(size)
        else:
            symbol.setSize(size)

    def updateSymbolSize(self, size, isWidth=False):
        if size <= 0:
            return
        
        self.symbolSize = size
        currentSymbol = self.symbol()
        if currentSymbol:
            clonedSymbol = currentSymbol.clone()
            self.applySizeToSymbol(clonedSymbol, size, isWidth)
            self.setSymbol(clonedSymbol)

    def setColor(self, color):
        if not self.isValidNewColor(color):
            return
        self.currentColor = QColor(color)
        self.applySymbol()
        self.colorChanged.emit(self.currentColor)

    def isValidNewColor(self, color):
        if not isinstance(color, QColor):
            return False
        if not color.isValid():
            return False
        if color == self.currentColor:
            return False
        return True

    def color(self):
        return QColor(self.currentColor)

    def setGeometryHint(self, hint):
        self.geometryHintValue = self.normalizeGeometryHint(hint)
        self.applySymbol()

    def geometryHint(self):
        return self.geometryHintValue

    def setAllowAlpha(self, allowed):
        self.allowAlphaEnabled = bool(allowed)

    def eventFilter(self, obj, event):
        if obj is not self:
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Wheel:
            return True

        if self.doubleClickOnlyEnabled:
            return self.handleDoubleClickMode(event)

        return self.handleSingleClickMode(event)

    def handleDoubleClickMode(self, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            return True
        if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
            self.openColorDialog()
            return True
        return False

    def handleSingleClickMode(self, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.openColorDialog()
            return True
        return False

    def openColorDialog(self):
        chosenColor = QgsColorDialog.getColor(
            self.currentColor, self, self.dialogTitle, self.allowAlphaEnabled
        )
        if chosenColor.isValid():
            self.setColor(chosenColor)

class QGISRedColorRampSelector(QWidget):
    colorRampChanged = pyqtSignal(QgsColorRamp)

    BUTTON_WIDTH = 150
    BUTTON_HEIGHT = 24
    GRADIENT_PREVIEW_WIDTH = 120
    GRADIENT_PREVIEW_HEIGHT = 16
    MENU_ICON_WIDTH = 50
    MENU_ICON_HEIGHT = 16
    ARROW_WIDTH = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ramps = {}
        self.currentRampNameValue = None
        self.button = None
        self.arrowLabel = None
        self.initUi()

    def initUi(self):
        self.setFixedWidth(self.BUTTON_WIDTH)
        self.setFixedHeight(self.BUTTON_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = self.createButton()
        self.arrowLabel = self.createArrowLabel()

        layout.addWidget(self.button)

        self.arrowLabel.setParent(self.button)
        self.positionArrowLabel()
        self.updateButtonDisplay()

    def createButton(self):
        button = QPushButton(self)
        button.clicked.connect(self.showRampMenu)
        button.setFixedWidth(self.BUTTON_WIDTH)
        button.setFixedHeight(self.BUTTON_HEIGHT)
        button.setStyleSheet(
            "QPushButton {"
            "    background-color: white;"
            "    border: 1px solid #ababab;"
            "    border-radius: 2px;"
            "    padding: 2px 20px 2px 4px;"
            "    text-align: left;"
            "}"
            "QPushButton:hover {"
            "    border: 1px solid #0078d4;"
            "}"
            "QPushButton::menu-indicator {"
            "    image: none;"
            "}"
        )
        return button

    def createArrowLabel(self):
        label = QLabel(self)
        label.setText("▼")
        label.setStyleSheet(
            "QLabel {"
            "    color: #666666;"
            "    font-size: 8px;"
            "    background: transparent;"
            "}"
        )
        label.setFixedSize(16, self.BUTTON_HEIGHT)
        label.setAlignment(Qt.AlignCenter)
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        return label

    def positionArrowLabel(self):
        if self.arrowLabel and self.button:
            self.arrowLabel.move(self.button.width() - self.ARROW_WIDTH, 0)

    def addColorRamp(self, name, ramp):
        if not isinstance(ramp, QgsColorRamp):
            return
        self.ramps[name] = ramp.clone()
        if self.currentRampNameValue is None:
            self.setCurrentRamp(name)

    def addColorRamps(self, ramps):
        for name, ramp in ramps.items():
            self.addColorRamp(name, ramp)

    def clearRamps(self):
        self.ramps.clear()
        self.currentRampNameValue = None
        self.updateButtonDisplay()

    def removeRamp(self, name):
        if name not in self.ramps:
            return
        del self.ramps[name]
        if self.currentRampNameValue == name:
            self.selectFirstAvailableRamp()

    def selectFirstAvailableRamp(self):
        if self.ramps:
            firstName = list(self.ramps.keys())[0]
            self.setCurrentRamp(firstName)
        else:
            self.currentRampNameValue = None
            self.updateButtonDisplay()

    def setCurrentRamp(self, name):
        if name not in self.ramps:
            return
        self.currentRampNameValue = name
        self.updateButtonDisplay()
        ramp = self.currentRamp()
        if ramp:
            self.colorRampChanged.emit(ramp)

    def currentRampName(self):
        return self.currentRampNameValue

    def currentRamp(self):
        if self.currentRampNameValue and self.currentRampNameValue in self.ramps:
            return self.ramps[self.currentRampNameValue].clone()
        return None

    def showRampMenu(self):
        if not self.ramps:
            return
        
        menu = QMenu(self)
        for name in sorted(self.ramps.keys()):
            ramp = self.ramps[name]
            icon = self.createRampIcon(ramp, self.MENU_ICON_WIDTH, self.MENU_ICON_HEIGHT)
            action = self.createMenuAction(menu, icon, name)
            menu.addAction(action)
        menuPosition = self.button.mapToGlobal(self.button.rect().bottomLeft())
        menu.exec_(menuPosition)

    def createMenuAction(self, menu, icon, name):
        action = QAction(icon, name, self)
        action.triggered.connect(lambda checked, rampName=name: self.setCurrentRamp(rampName))

        if name == self.currentRampNameValue:
            action.setCheckable(True)
            action.setChecked(True)
        return action

    def updateButtonDisplay(self):
        if self.hasValidCurrentRamp():
            self.displayCurrentRampGradient()
        else:
            self.displayPlaceholder()
        self.positionArrowLabel()

    def hasValidCurrentRamp(self):
        return self.currentRampNameValue and self.currentRampNameValue in self.ramps

    def displayCurrentRampGradient(self):
        ramp = self.ramps[self.currentRampNameValue]
        pixmap = self.renderGradientPreview(ramp, self.GRADIENT_PREVIEW_WIDTH, self.GRADIENT_PREVIEW_HEIGHT)
        self.button.setIcon(QIcon(pixmap))
        self.button.setIconSize(QSize(self.GRADIENT_PREVIEW_WIDTH, self.GRADIENT_PREVIEW_HEIGHT))
        self.button.setText("")

    def displayPlaceholder(self):
        self.button.setIcon(QIcon())
        self.button.setText("No ramp")

    def renderGradientPreview(self, ramp, width, height):
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        self.drawGradientLines(painter, ramp, width, height)
        painter.end()
        return pixmap

    def drawGradientLines(self, painter, ramp, width, height):
        for x in range(width):
            normalizedPosition = x / max(1, width - 1)
            color = ramp.color(normalizedPosition)
            painter.setPen(color)
            painter.drawLine(x, 0, x, height)

    def createRampIcon(self, ramp, width, height):
        pixmap = self.renderGradientPreview(ramp, width, height)
        return QIcon(pixmap)