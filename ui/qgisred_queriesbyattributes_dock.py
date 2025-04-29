# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDockWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon
from qgis.PyQt import uic
from qgis.core import QgsProject, QgsVectorLayer, QgsFeatureRequest
import os

from ..tools.qgisred_utils import QGISRedUtils

# load UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),"qgisred_queriesbyattributes_dock.ui"))

class QGISRedQueriesByAttributesDock(QDockWidget, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(QGISRedQueriesByAttributesDock, self).__init__(parent or iface.mainWindow())
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.initializeQueriesByAttributes()

    def initializeQueriesByAttributes(self):
        self.criteria = []
        self.currentlyReplacingIndex = None

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
            'listed': ['=']
        }

        self.fieldTypeMapping = {
            'int': 'numeric',
            'double': 'numeric',
            'string': 'listed',
            'date': 'numeric',
            'datetime': 'numeric',
            'time': 'numeric',
            'bool': 'listed'
        }

        self.tableWidgetCriteria.setColumnCount(3)
        self.tableWidgetCriteria.setHorizontalHeaderLabels(["Id", "Oper", "Criteria"])
        self.tableWidgetCriteria.verticalHeader().setVisible(False)
        h = self.tableWidgetCriteria.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)  
        h.setSectionResizeMode(2, QHeaderView.Stretch)          

        # set up statistics table
        if self.tableWidgetStatistics.columnCount() == 0:
            self.tableWidgetStatistics.setColumnCount(5)
            self.tableWidgetStatistics.setHorizontalHeaderLabels(
                ["Count", "Sum", "Avg", "Min", "Max"]
            )
            for i in range(5):
                self.tableWidgetStatistics.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.Stretch
                )

        self.initializeElementTypes()
        self.setupConnections()
        self.setupButtonIcons()


    def setupButtonIcons(self):
        self.btImport.setIcon(QIcon(":/plugins/QGISRed/images/iconStatisticsImport.png"))
        self.btExport.setIcon(QIcon(":/plugins/QGISRed/images/iconStatisticsExport.png"))

        self.btCriteriaUp.setIcon(QIcon(":/plugins/QGISRed/images/iconStatisticsArrowUp.png"))
        self.btCriteriaDown.setIcon(QIcon(":/plugins/QGISRed/images/iconStatisticsArrowDown.png"))
        self.btCriteriaClear.setIcon(QIcon(":/plugins/QGISRed/images/iconStatisticsDelete.png"))
        self.btCriteriaEdit.setIcon(QIcon(":/plugins/QGISRed/images/iconStatisticsEdit.png"))

        self.btExcel.setIcon(QIcon(":/plugins/QGISRed/images/iconStatisticsExcel.png"))

    def setupConnections(self):
        # element / property updates
        self.cbElementType.currentIndexChanged.connect(self.updateProperties)
        self.cbProperty.currentIndexChanged.connect(self.updateValues)
        # main buttons
        self.btAdd.clicked.connect(lambda: self.addCriterion('+'))
        self.btSubtract.clicked.connect(lambda: self.addCriterion('-'))
        self.btReplace.clicked.connect(self.replaceCriterion)
        self.btClear.clicked.connect(self.clearCriteria)
        self.btSubmit.clicked.connect(self.runQuery)
        # stats property change
        self.cbStatisticsFor.currentIndexChanged.connect(self.onStatisticsForChanged)
        # initial button state
        self.updateButtonsState()

    def onStatisticsForChanged(self):
        if self.cbStatisticsFor.isEnabled():
            self.calculateStatistics()

    def initializeElementTypes(self):
        self.cbElementType.clear()
        inputsGroup = QgsProject.instance().layerTreeRoot().findGroup("Inputs")
        if inputsGroup:
            checkedLayers = inputsGroup.checkedLayers()
            for element, identifier in self.elementIdentifiers.items():
                for layer in checkedLayers:
                    if layer and layer.customProperty("qgisred_identifier") == identifier:
                        self.cbElementType.addItem(layer.name(), layer)
        self.updateProperties()

    def updateButtonsState(self):
        has = len(self.criteria) > 0
        sel = self.tableWidgetCriteria.currentRow() >= 0
        self.btSubtract.setEnabled(has)
        self.btReplace.setEnabled(has and sel)
        self.btClear.setEnabled(has)
        self.btSubmit.setEnabled(has)
        self.cbElementType.setEnabled(not has)
        self.cbStatisticsFor.setEnabled(has)

    def updateProperties(self):
        layer = self.cbElementType.currentData(Qt.UserRole)
        if not layer:
            return
        self.cbProperty.clear()
        self.cbStatisticsFor.clear()
        #self.cbStatisticsFor.addItem("")
        for field in layer.fields():
            fn = field.name()
            if fn.lower() not in ('id','descrip'):
                self.cbProperty.addItem(fn)
                self.cbStatisticsFor.addItem(fn)
        if self.cbProperty.count():
            self.updateConditions()
            self.updateValues()

    def updateConditions(self):
        self.cbCondition.clear()
        prop = self.cbProperty.currentText()
        layer = self.cbElementType.currentData(Qt.UserRole)
        if not layer or not prop:
            return
        field = layer.fields().field(prop)
        cat = self.fieldTypeMapping.get(field.typeName().lower(), 'text')
        
        self.cbCondition.addItems(self.conditionsByType.get('numeric', [])) #all numeric for now

    def updateValues(self):
        ...
        # self.cbValue.clear()
        # prop = self.cbProperty.currentText()
        # layer = self.cbElementType.currentData(Qt.UserRole)
        # if not layer or not prop:
        #     return
        # field = layer.fields().field(prop)
        # cat = self.fieldTypeMapping.get(field.typeName().lower(), 'text')
        # if cat == 'boolean':
        #     self.cbValue.addItems(['true','false'])
        # elif cat == 'numeric':
        #     mn, mx = self.getFieldMinMax(layer, prop)
        #     if mn is not None and mx is not None:
        #         interval = (mx - mn) / 5.0
        #         for i in range(5):
        #             start = mn + i*interval
        #             end   = mn + (i+1)*interval
        #             if i == 4:
        #                 end = mx
        #             self.cbValue.addItem(f"{start:.2f} - {end:.2f}")
        # else:
        #     vals = self.getUniqueFieldValues(layer, prop)
        #     for v in vals:
        #         if v is not None:
        #             self.cbValue.addItem(str(v))

    def getFieldMinMax(self, layer, name):
        mn = mx = None
        idx = layer.fields().indexFromName(name)
        if idx < 0:
            return None, None
        for f in layer.getFeatures():
            val = f[name]
            if val is not None:
                mn = mx = val
                break
        for f in layer.getFeatures():
            val = f[name]
            if val is not None:
                mn = min(mn, val)
                mx = max(mx, val)
        return mn, mx

    def getUniqueFieldValues(self, layer, name):
        vals = set()
        idx = layer.fields().indexFromName(name)
        if idx < 0:
            return []
        for f in layer.getFeatures():
            vals.add(f[name])
        return sorted(vals)

    def parseValue(self, txt):
        try:
            return int(txt)
        except ValueError:
            try:
                return float(txt)
            except ValueError:
                return txt

    def reloadCriteriaTable(self):
        tbl = self.tableWidgetCriteria
        tbl.setRowCount(len(self.criteria))

        for i, c in enumerate(self.criteria):
            op = c.get('operator', '+')

            id_item = QTableWidgetItem(f"Cr{i+1}")
            id_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            oper_item = QTableWidgetItem(op)
            oper_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            if op == '-':
                oper_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            else:
                oper_item.setTextAlignment(Qt.AlignLeft  | Qt.AlignVCenter)

            crit_txt = f"{c['property']} {c['condition']} {c['value']}"
            crit_item = QTableWidgetItem(crit_txt)
            crit_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            crit_item.setTextAlignment(Qt.AlignCenter)

            expr = self.buildExpression(c)
            crit_item.setData(Qt.UserRole, {'expression': expr, 'operator': op})

            tbl.setItem(i, 0, id_item)
            tbl.setItem(i, 1, oper_item)
            tbl.setItem(i, 2, crit_item)

        self.updateButtonsState()


    def addCriterion(self, operator):
        prop    = self.cbProperty.currentText()
        cond    = self.cbCondition.currentText()
        val_txt = self.cbValue.value()
        if not prop or not cond or not val_txt:
            return
        val  = self.parseValue(val_txt)
        crit = {'property': prop, 'condition': cond, 'value': val, 'operator': operator}
        if self.currentlyReplacingIndex is None:
            self.criteria.append(crit)
        else:
            op = self.criteria[self.currentlyReplacingIndex]['operator']
            crit['operator'] = op
            self.criteria[self.currentlyReplacingIndex] = crit
            self.currentlyReplacingIndex = None
        self.reloadCriteriaTable()

    def replaceCriterion(self):
        row = self.tableWidgetCriteria.currentRow()
        if self.currentlyReplacingIndex is None:
            if row < 0:
                return
            crit = self.criteria[row]
            self.currentlyReplacingIndex = row
            self.cbProperty .setCurrentText(crit['property'])
            self.cbCondition.setCurrentText(crit['condition'])
            self.cbValue.setValue(str(crit['value']))
            self.btAdd.setEnabled(False)
            self.btSubtract.setEnabled(False)
            self.btClear.setEnabled(False)
            self.cbStatisticsFor.setEnabled(False)
        else:
            self.addCriterion(self.criteria[self.currentlyReplacingIndex]['operator'])

    def clearCriteria(self):
        self.criteria = []
        self.currentlyReplacingIndex = None
        self.reloadCriteriaTable()
        layer = self.cbElementType.currentData(Qt.UserRole)
        if layer:
            layer.removeSelection()
        self.tableWidgetStatistics.setRowCount(0)

    def buildExpression(self, crit):
        fld  = f'"{crit["property"]}"'
        cond = crit['condition']
        op_map = {'=':'=', '≠':'<>', 'contains':' LIKE ', 'starts \with':' LIKE ', 'ends with':' LIKE '}
        op   = op_map.get(cond, cond)
        val  = crit['value']
        if isinstance(val, str):
            if cond == 'contains':    val = f"'%{val}%'"
            elif cond == 'starts with': val = f"'{val}%'"
            elif cond == 'ends with':   val = f"'%{val}'"
            else:                       val = f"'{val}'"
        return f"{fld} {op} {val}"

    def runQuery(self):
        property = self.cbProperty.currentText()
        self.labelStatisticsProperty.setText(property)
        self.labelStatisticsPropertyFor.setText(f"Statistics of {property} for selected Elements")
        self.calculateStatistics()

    def calculateStatistics(self):
        layer = self.cbElementType.currentData(Qt.UserRole)
        if not layer:
            return

        field = self.cbStatisticsFor.currentText()
        if not field:
            return

        stats_per_crit = []
        for c in self.criteria:
            expr = self.buildExpression(c)
            req  = QgsFeatureRequest().setFilterExpression(expr)
            vals = [
                feat[field]
                for feat in layer.getFeatures(req)
                if feat[field] is not None
            ]
            stats_per_crit.append(vals)

        plus_exprs  = [self.buildExpression(c) for c in self.criteria if c['operator']=='+']
        minus_exprs = [self.buildExpression(c) for c in self.criteria if c['operator']=='-']
        or_part     = ' OR '.join(plus_exprs)
        nand_part   = ' AND '.join(minus_exprs)
        full_expr   = ' AND '.join(filter(None, [
            or_part,
            f"NOT ({nand_part})" if nand_part else ''
        ]))
        req_all     = QgsFeatureRequest().setFilterExpression(full_expr)
        vals_all    = [
            feat[field]
            for feat in layer.getFeatures(req_all)
            if feat[field] is not None
        ]
        stats_per_crit.append(vals_all)

        def comp(vals):
            cnt   = len(vals)
            total = sum(vals) if cnt else 0
            avg   = total/cnt     if cnt else 0
            mn    = min(vals)     if cnt else None
            mx    = max(vals)     if cnt else None
            return cnt, total, avg, mn, mx

        stats_list = [comp(v) for v in stats_per_crit]

        tbl = self.tableWidgetStatistics
        tbl.setRowCount(len(stats_list))
        tbl.verticalHeader().setVisible(True)

        for i, (cnt, total, avg, mn, mx) in enumerate(stats_list):
            for j, val in enumerate((cnt, total, avg, mn, mx)):
                txt = f"{val:.2f}" if isinstance(val, float) else str(val)
                item = QTableWidgetItem(txt)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                tbl.setItem(i, j, item)

            label = "All" if i == len(stats_list) - 1 else f"Cr{i+1}"
            tbl.setVerticalHeaderItem(i, QTableWidgetItem(label))

    def closeEvent(self, event):
        self.clearCriteria()
        layer = self.cbElementType.currentData(Qt.UserRole)
        if layer:
            layer.removeSelection()
        super(QGISRedQueriesByAttributesDock, self).closeEvent(event)
