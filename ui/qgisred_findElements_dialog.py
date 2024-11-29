# # -*- coding: utf-8 -*-

# # Standard library imports
# import os

# # Third-party imports
# from PyQt5.QtGui import QIcon
# from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget
# from PyQt5 import sip
# from qgis.PyQt import uic
# from qgis.PyQt.QtCore import QVariant

# # QGIS imports
# from qgis.core import QgsLayerTreeGroup, QgsLayerTreeLayer, QgsLayerTreeNode, QgsProject
# from qgis.core import QgsVectorFileWriter, QgsVectorLayer
# from qgis.core import QgsProject, QgsVectorLayer, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat
# from qgis.utils import iface

# # Local imports
# from ..tools.qgisred_utils import QGISRedUtils

# FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "qgisred_findElements_dialog.ui"))

# class QGISRedFindElementsDialog(QDialog, FORM_CLASS):
#     def __init__(self, parent=None):
#         """Constructor."""
#         super(QGISRedFindElementsDialog, self).__init__(parent)
#         self.setupUi(self)
#         self.setDialogStyle()
#         self.btAccept.clicked.connect(self.accept)
#         self.btCancel.clicked.connect(self.reject)
#         self.updateCheckboxStates()

#     def setDialogStyle(self):
#         icon_path = os.path.join(os.path.dirname(__file__), '..', 'images', 'iconThematicMaps.png')
#         self.setWindowIcon(QIcon(icon_path))

#         group_boxes = [
#             self.gbPipes,
#             self.gbJunctions,
#             self.gbValves,
#             self.gbPumps,
#             self.gbTanks,
#             self.gbReservoirs,
#             self.gbService,
#             self.gbIsolation,
#             self.gbMeters
#         ]

#         for group_box in group_boxes:
#             self.setGroupBoxStyle(group_box)

#     def setGroupBoxStyle(self, group_box):
#         group_box.setStyleSheet("font-weight: bold;")
#         for widget in group_box.findChildren(QWidget):
#             widget.setStyleSheet("font-weight: normal;")

#     def accept(self):

#         # Close dialog
#         super(QGISRedFindElementsDialog, self).accept()

#         units = QGISRedUtils().getUnits()
#         queries = []

#         # Tanks and Reservoirs queries (top)
#         # Tanks queries
#         if self.cbTanksElevation.isChecked():
#             queries.append({
#                 'layer_name': 'Tank Elevations',
#                 'field': 'Elevation',
#                 'qml_file': f'tank_elevations_{units}.qml',
#                 'file_name': f'elevation_{units}',
#                 'tooltip_prefix': 'Elev'
#             })

#         if self.cbTanksDiameter.isChecked():
#             queries.append({
#                 'layer_name': 'Tank Diameters',
#                 'field': 'Diameter',
#                 'qml_file': f'tank_diameters_{units}.qml',
#                 'file_name': f'diameter_{units}',
#                 'tooltip_prefix': 'Diam'
#             })

#         if self.cbTanksVolume.isChecked():
#             queries.append({
#                 'layer_name': 'Tank Volumes',
#                 'field': 'Volume',
#                 'qml_file': f'tank_volumes_{units}.qml',
#                 'file_name': f'volume_{units}',
#                 'tooltip_prefix': 'Vol'
#             })

#         if self.cbTanksLevel.isChecked():
#             queries.append({
#                 'layer_name': 'Tank Levels',
#                 'field': 'Level',
#                 'qml_file': f'tank_levels_{units}.qml',
#                 'file_name': f'level_{units}',
#                 'tooltip_prefix': 'Level'
#             })

#         if self.cbTanksInitialQuality.isChecked():
#             queries.append({
#                 'layer_name': 'Tank Initial Quality',
#                 'field': 'InitQuality',
#                 'qml_file': 'tank_init_quality.qml',
#                 'file_name': 'init_quality',
#                 'tooltip_prefix': 'Quality'
#             })

#         if self.cbTanksBulkCoeff.isChecked():
#             queries.append({
#                 'layer_name': 'Tank Bulk Coefficient',
#                 'field': 'BulkCoeff',
#                 'qml_file': 'tank_bulk_coeff.qml',
#                 'file_name': 'bulk_coeff',
#                 'tooltip_prefix': 'Bulk'
#             })

#         if self.cbTanksMixingModel.isChecked():
#             queries.append({
#                 'layer_name': 'Tank Mixing Models',
#                 'field': 'MixModel',
#                 'qml_file': 'tank_mixing_model.qml',
#                 'file_name': 'mixing_model',
#                 'tooltip_prefix': 'Mix'
#             })

#         if self.cbTanksTag.isChecked():
#             queries.append({
#                 'layer_name': 'Tank Tags',
#                 'field': 'Tag',
#                 'qml_file': 'tank_tags.qml',
#                 'file_name': 'tags',
#                 'tooltip_prefix': 'Tag'
#             })

#         # Reservoirs queries
#         if self.cbReservoirsTotalHead.isChecked():
#             queries.append({
#                 'layer_name': 'Reservoir Total Head',
#                 'field': 'TotalHead',
#                 'qml_file': f'reservoir_total_head_{units}.qml',
#                 'file_name': f'total_head_{units}',
#                 'tooltip_prefix': 'Head'
#             })

#         if self.cbReservoirsHeadPattern.isChecked():
#             queries.append({
#                 'layer_name': 'Reservoir Head Patterns',
#                 'field': 'HeadPattern',
#                 'qml_file': 'reservoir_head_pattern.qml',
#                 'file_name': 'head_pattern',
#                 'tooltip_prefix': 'Pattern'
#             })

#         if self.cbReservoirsInitialQuality.isChecked():
#             queries.append({
#                 'layer_name': 'Reservoir Initial Quality',
#                 'field': 'InitQuality',
#                 'qml_file': 'reservoir_init_quality.qml',
#                 'file_name': 'init_quality',
#                 'tooltip_prefix': 'Quality'
#             })

#         if self.cbReservoirsTag.isChecked():
#             queries.append({
#                 'layer_name': 'Reservoir Tags',
#                 'field': 'Tag',
#                 'qml_file': 'reservoir_tags.qml',
#                 'file_name': 'tags',
#                 'tooltip_prefix': 'Tag'
#             })

#         # Junctions queries (second from top)
#         if self.cbJunctionsElevation.isChecked():
#             queries.append({
#                 'layer_name': 'Junction Elevations',
#                 'field': 'Elevation',
#                 'qml_file': f'junction_elevation_{units}.qml',
#                 'file_name': f'elevation_{units}',
#                 'tooltip_prefix': 'Elev'
#             })

#         if self.cbJunctionsBaseDemand.isChecked():
#             queries.append({
#                 'layer_name': 'Junction Base Demands',
#                 'field': 'BaseDemand',
#                 'qml_file': 'junction_base_demand.qml',
#                 'file_name': 'base_demand',
#                 'tooltip_prefix': 'Demand'
#             })

#         if self.cbJunctionsPatternDemand.isChecked():
#             queries.append({
#                 'layer_name': 'Junction Pattern Demands',
#                 'field': 'PatternDemand',
#                 'qml_file': 'junction_pattern_demand.qml',
#                 'file_name': 'pattern_demand',
#                 'tooltip_prefix': 'Pattern'
#             })

#         if self.cbJunctionsEmitterCoeff.isChecked():
#             queries.append({
#                 'layer_name': 'Junction Emitter Coefficients',
#                 'field': 'EmitterCoeff',
#                 'qml_file': 'junction_emitter_coeff.qml',
#                 'file_name': 'emitter_coeff',
#                 'tooltip_prefix': 'Emitter'
#             })

#         if self.cbJunctionsInitialQuality.isChecked():
#             queries.append({
#                 'layer_name': 'Junction Initial Quality',
#                 'field': 'InitQuality',
#                 'qml_file': 'junction_init_quality.qml',
#                 'file_name': 'init_quality',
#                 'tooltip_prefix': 'Quality'
#             })

#         if self.cbJunctionsTag.isChecked():
#             queries.append({
#                 'layer_name': 'Junction Tags',
#                 'field': 'Tag',
#                 'qml_file': 'junction_tags.qml',
#                 'file_name': 'tags',
#                 'tooltip_prefix': 'Tag'
#             })

#         # Valves and Pumps queries (third from top)
#         # Valves queries
#         if self.cbValvesType.isChecked():
#             queries.append({
#                 'layer_name': 'Valve Types',
#                 'field': 'Type',
#                 'qml_file': 'valve_types.qml',
#                 'file_name': 'type',
#                 'tooltip_prefix': 'Type'
#             })

#         if self.cbValvesDiameter.isChecked():
#             queries.append({
#                 'layer_name': 'Valve Diameters',
#                 'field': 'Diameter',
#                 'qml_file': f'valve_diameters_{units}.qml',
#                 'file_name': f'diameter_{units}',
#                 'tooltip_prefix': 'Diam'
#             })

#         if self.cbValvesSetting.isChecked():
#             queries.append({
#                 'layer_name': 'Valve Settings',
#                 'field': 'Setting',
#                 'qml_file': 'valve_settings.qml',
#                 'file_name': 'setting',
#                 'tooltip_prefix': 'Set'
#             })

#         if self.cbValvesInitialStatus.isChecked():
#             queries.append({
#                 'layer_name': 'Valve Initial Status',
#                 'field': 'InitStatus',
#                 'qml_file': 'valve_init_status.qml',
#                 'file_name': 'init_status',
#                 'tooltip_prefix': 'Status'
#             })

#         if self.cbValvesLossCoeff.isChecked():
#             queries.append({
#                 'layer_name': 'Valve Loss Coefficients',
#                 'field': 'LossCoeff',
#                 'qml_file': 'valve_loss_coeff.qml',
#                 'file_name': 'loss_coeff',
#                 'tooltip_prefix': 'Loss'
#             })

#         if self.cbValvesTag.isChecked():
#             queries.append({
#                 'layer_name': 'Valve Tags',
#                 'field': 'Tag',
#                 'qml_file': 'valve_tags.qml',
#                 'file_name': 'tags',
#                 'tooltip_prefix': 'Tag'
#             })

#         # Pumps queries
#         if self.cbPumpsType.isChecked():
#             queries.append({
#                 'layer_name': 'Pump Types',
#                 'field': 'Type',
#                 'qml_file': 'pump_types.qml',
#                 'file_name': 'type',
#                 'tooltip_prefix': 'Type'
#             })

#         if self.cbPumpsPumpCurve.isChecked():
#             queries.append({
#                 'layer_name': 'Pump Curves',
#                 'field': 'PumpCurve',
#                 'qml_file': 'pump_curves.qml',
#                 'file_name': 'pump_curve',
#                 'tooltip_prefix': 'Curve'
#             })

#         if self.cbPumpsPower.isChecked():
#             queries.append({
#                 'layer_name': 'Pump Power',
#                 'field': 'Power',
#                 'qml_file': 'pump_power.qml',
#                 'file_name': 'power',
#                 'tooltip_prefix': 'Power'
#             })

#         if self.cbPumpsInitialStatus.isChecked():
#             queries.append({
#                 'layer_name': 'Pump Initial Status',
#                 'field': 'InitStatus',
#                 'qml_file': 'pump_init_status.qml',
#                 'file_name': 'init_status',
#                 'tooltip_prefix': 'Status'
#             })

#         if self.cbPumpsSpeed.isChecked():
#             queries.append({
#                 'layer_name': 'Pump Speed',
#                 'field': 'Speed',
#                 'qml_file': 'pump_speed.qml',
#                 'file_name': 'speed',
#                 'tooltip_prefix': 'Speed'
#             })

#         if self.cbPumpsEfficiencyCurve.isChecked():
#             queries.append({
#                 'layer_name': 'Pump Efficiency Curves',
#                 'field': 'EffCurve',
#                 'qml_file': 'pump_efficiency_curves.qml',
#                 'file_name': 'efficiency_curve',
#                 'tooltip_prefix': 'Eff'
#             })

#         if self.cbPumpsEnergyPrice.isChecked():
#             queries.append({
#                 'layer_name': 'Pump Energy Price',
#                 'field': 'EnergyPrice',
#                 'qml_file': 'pump_energy_price.qml',
#                 'file_name': 'energy_price',
#                 'tooltip_prefix': 'Price'
#             })

#         if self.cbPumpsTag.isChecked():
#             queries.append({
#                 'layer_name': 'Pump Tags',
#                 'field': 'Tag',
#                 'qml_file': 'pump_tags.qml',
#                 'file_name': 'tags',
#                 'tooltip_prefix': 'Tag'
#             })

#         # Service Connections queries
#         if self.cbPipesDiameter_3.isChecked():
#             queries.append({
#                 'layer_name': 'Service Connection',
#                 'field': 'Temporary',
#                 'qml_file': 'service_connection.qml',
#                 'file_name': 'temporary',
#                 'tooltip_prefix': 'Temp'
#             })

#         # Isolation Valves queries
#         if self.cbTanksElevation_3.isChecked():
#             queries.append({
#                 'layer_name': 'Isolation Valves',
#                 'field': 'Temporary',
#                 'qml_file': 'isolation_valves.qml',
#                 'file_name': 'temporary',
#                 'tooltip_prefix': 'Temp'
#             })

#         # Meters queries
#         if self.cbReservoirsTotalHead_3.isChecked():
#             queries.append({
#                 'layer_name': 'Meters',
#                 'field': 'Temporary',
#                 'qml_file': 'meters.qml',
#                 'file_name': 'temporary',
#                 'tooltip_prefix': 'Temp'
#             })

#         # Pipes queries (bottom)
#         if self.cbPipesDiameter.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Diameters',
#                 'field': 'Diameter',
#                 'qml_file': f'pipe_diameters_{units}.qml',
#                 'file_name': f'diameter_{units}',
#                 'tooltip_prefix': 'Diam'
#             })

#         if self.cbPipesLength.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Lengths',
#                 'field': 'Length',
#                 'qml_file': f'pipe_lengths_{units}.qml',
#                 'file_name': f'length_{units}',
#                 'tooltip_prefix': 'Len'
#             })

#         if self.cbPipesMaterial.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Materials',
#                 'field': 'Material',
#                 'qml_file': 'pipe_materials.qml',
#                 'file_name': 'material',
#                 'tooltip_prefix': 'Mat'
#             })

#         if self.cbPipesRoughness.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Roughness',
#                 'field': 'Roughness',
#                 'qml_file': 'pipe_roughness.qml',
#                 'file_name': 'roughness',
#                 'tooltip_prefix': 'Rough'
#             })

#         if self.cbPipesAge.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Age',
#                 'field': 'Age',
#                 'qml_file': 'pipe_age.qml',
#                 'file_name': 'age',
#                 'tooltip_prefix': 'Age'
#             })

#         if self.cbPipesLossCoeff.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Loss Coefficient',
#                 'field': 'LossCoeff',
#                 'qml_file': 'pipe_loss_coeff.qml',
#                 'file_name': 'loss_coeff',
#                 'tooltip_prefix': 'Loss'
#             })

#         if self.cbPipesInitStatus.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Initial Status',
#                 'field': 'InitStatus',
#                 'qml_file': 'pipe_init_status.qml',
#                 'file_name': 'init_status',
#                 'tooltip_prefix': 'Status'
#             })

#         if self.cbPipesInstallationDate.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Installation Date',
#                 'field': 'InstallDate',
#                 'qml_file': 'pipe_install_date.qml',
#                 'file_name': 'install_date',
#                 'tooltip_prefix': 'Inst'
#             })

#         if self.cbPipesBulkCoeff.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Bulk Coefficient',
#                 'field': 'BulkCoeff',
#                 'qml_file': 'pipe_bulk_coeff.qml',
#                 'file_name': 'bulk_coeff',
#                 'tooltip_prefix': 'Bulk'
#             })

#         if self.cbPipesWallCoeff.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Wall Coefficient',
#                 'field': 'WallCoeff',
#                 'qml_file': 'pipe_wall_coeff.qml',
#                 'file_name': 'wall_coeff',
#                 'tooltip_prefix': 'Wall'
#             })

#         if self.cbPipesTag.isChecked():
#             queries.append({
#                 'layer_name': 'Pipe Tags',
#                 'field': 'Tag',
#                 'qml_file': 'pipe_tags.qml',
#                 'file_name': 'tags',
#                 'tooltip_prefix': 'Tag'
#             })

#         return queries