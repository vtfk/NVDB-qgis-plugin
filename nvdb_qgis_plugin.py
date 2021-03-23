# -*- coding: utf-8 -*-
import os.path
from nvdbapiv3 import nvdbFagdata
from qgis._core import QgsProject, QgsWkbTypes, QgsProcessingException
from qgis import processing
from nvdbapiV3qgis3 import nvdbsok2qgis
from .nvdbobjects import *
from .nvdbareas import *
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtWidgets import QDockWidget

from qgis.core import (QgsApplication, QgsTask, QgsMessageLog, Qgis)
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .nvdb_qgis_plugin_dialog import NvdbQgisPluginDialog

import random
from time import sleep


class NvdbQgisPlugin:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.dlg = NvdbQgisPluginDialog()
        self.iface = iface
        self.tm = QgsApplication.taskManager()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'NvdbQgisPlugin_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&NVDB QGIS')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('NvdbQgisPlugin', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)
        # Connect all actions
        self.dlg.comboBox.currentIndexChanged[str].connect(self.comboBox_itemChanged)
        self.dlg.addButton.clicked.connect(self.addItem)
        self.dlg.removeButton.clicked.connect(self.removeItem)
        self.dlg.clearButton.clicked.connect(self.clearSelection)
        self.dlg.kommuneCheck.toggled.connect(self.kommuneSelected)
        self.dlg.kontraktCheck.toggled.connect(self.kontraktSelected)
        self.dlg.fylkeBox.currentIndexChanged[str].connect(self.getKommune)
        self.dlg.fylkeBox.currentIndexChanged[str].connect(self.getKontrakt)
        self.dlg.mergeButton.clicked.connect(self.mergeLayers)
        self.dlg.kjorButton.clicked.connect(self.runTask)
        self.dlg.vegsystemBox.currentIndexChanged[str].connect(self.vegsystemBox_itemChanged)
        # Get filterdata
        # TODO: Get catagories
        getAllAreaData()
        getAllObjectData()
        self.dlg.vegsystemBox.addItems(returnVegreferanseData())
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/nvdb_qgis_plugin/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'NVDB QGIS'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&NVDB QGIS'),
                action)
            self.iface.removeToolBarIcon(action)

    def kommuneSelected(self):
        if self.dlg.kommuneCheck.isChecked():
            self.dlg.kommuneBox.setEnabled(True)
            self.dlg.kontraktCheck.setChecked(False)
            self.dlg.kontraktBox.setEnabled(False)
        else:
            self.dlg.kommuneBox.setEnabled(False)

    def kontraktSelected(self):
        if self.dlg.kontraktCheck.isChecked():
            self.dlg.kontraktBox.setEnabled(True)
            self.dlg.kommuneCheck.setChecked(False)
            self.dlg.kommuneBox.setEnabled(False)
        else:
            self.dlg.kontraktBox.setEnabled(False)

    def comboBox_itemChanged(self, index):
        self.dlg.listWidgetObjects.clear()
        self.dlg.textEdit.append("Kategori: " + index)
        if index == "Alle":
            items = getNames()
            self.dlg.listWidgetObjects.addItems(items)
        else:
            items = getObjInCat(index)
            self.dlg.listWidgetObjects.addItems(items)

    def vegsystemBox_itemChanged(self, index):
        self.dlg.textEdit.append("Vegsystemreferanse: " + index)
        selectedVegreferanse(index)

    def addItem(self):
        all_items = self.dlg.listWidgetObjects.selectedItems()
        for i in range(len(all_items)):
            self.dlg.listWidget.addItem(all_items[i].text())
            self.dlg.textEdit.append("Lagt til " + all_items[i].text())
        self.dlg.listWidgetObjects.clearSelection()

    def removeItem(self):
        selected_items = self.dlg.listWidget.selectedItems()
        if not selected_items:
            pass
        else:
            for i in range(len(selected_items)):
                r = self.dlg.listWidget.row(selected_items[i])
                self.dlg.textEdit.append("Fjernet " + selected_items[i].text())
                self.dlg.listWidget.takeItem(r)

    def successMessage(self, message):
        successText = "<span style=\" color:#2ECC71;\" >"
        successText += message
        successText += "</span>"
        self.dlg.textEdit.append(successText)

    def errorMessage(self, message):
        errorText = "<span style=\" color:#ff0000;\" >"
        errorText += message
        errorText += "</span>"
        self.dlg.textEdit.append(errorText)

    def clearSelection(self):
        self.dlg.listWidgetObjects.clearSelection()

    def getKommune(self, index):
        self.dlg.textEdit.append("Fylke: " + index)
        self.dlg.kommuneBox.clear()
        self.dlg.kommuneBox.addItems(getKommuneNavn(index))

    def getKontrakt(self, index):
        self.dlg.kontraktBox.clear()
        self.dlg.kontraktBox.addItems(getKontraktNavn(index))

    def mergeLayers(self):
        project = QgsProject.instance()
        completeLayerList = []
        for id, layer in project.mapLayers().items():
            currentLayerName = layer.name()
            currentLayerType = int(layer.wkbType())
            for id_2, layer_2 in project.mapLayers().items():
                secondLayerName = layer_2.name()
                secondLayerType = int(layer_2.wkbType())
                parameter1 = secondLayerName + "_2d"
                parameter2 = secondLayerName[:-3]
                parameter3 = secondLayerName + "_3d"
                parameter5 = int(repr(currentLayerType)[-1])
                parameter6 = int(repr(secondLayerType)[-1])

                if secondLayerName in currentLayerName and currentLayerType != secondLayerType and (
                        currentLayerName == parameter1 or currentLayerName == parameter2 or currentLayerName == parameter3) and parameter5 == parameter6:
                    self.dlg.textEdit.append(
                        "Slår sammen: " + currentLayerName + " " + str(currentLayerType) + " " + str(
                            secondLayerType) + " " + secondLayerName)
                    layerList = [layer, layer_2]
                    completeLayerList.append(layer)
                    completeLayerList.append(layer_2)
                    if len(currentLayerName) > len(secondLayerName):
                        completeLayerName = currentLayerName[:-3]
                    else:
                        completeLayerName = secondLayerName[:-3]
                    try:
                        processing.runAndLoadResults("qgis:mergevectorlayers", {'LAYERS': layerList,
                                                                                'OUTPUT': completeLayerName + " " +
                                                                                QgsWkbTypes.displayString(
                                                                                              currentLayerType)})
                    except QgsProcessingException:
                        completeLayerList = completeLayerList[:-2]
                        self.errorMessage(
                            "Fikk problemer med å slå sammen " + str(currentLayerName) + " og " + str(secondLayerName))
                        self.dlg.textEdit.append(str(QgsProcessingException))

                    break
                else:
                    pass

        for i in completeLayerList:
            project.removeMapLayers([i.id()])


    def runTask(self):
        pythonConsole = self.iface.mainWindow().findChild(QDockWidget, 'PythonConsole')
        if not pythonConsole or not pythonConsole.isVisible():
            self.iface.actionShowPythonDialog().trigger()
        objList = [str(self.dlg.listWidget.item(i).text()) for i in range(self.dlg.listWidget.count())]
        for item in objList:
            task = QgsTask.fromFunction("Henter: " + item, getLayers, on_finished=completed, item=item, qtGui=self.dlg)
            self.tm.addTask(task)
            self.dlg.listWidget.clear()
        print("DONE")
        if self.tm.allTasksFinished():
            print("all tasks finished")

    def run(self):
        if self.first_start:
            self.first_start = False
        self.dlg.comboBox.clear()
        self.dlg.comboBox.addItems(sortCategories())
        self.dlg.fylkeBox.addItems(getFylkeNavn())
        self.dlg.kommuneBox.setEnabled(False)
        self.dlg.kontraktBox.setEnabled(False)
        self.dlg.show()
        result = self.dlg.exec_()
        if result:
            """ Close """


def getLayers(task, item, qtGui):
    """
    Raises an exception to abort the task.
    Returns a result if success.
    The result will be passed, together with the exception (None in
    the case of success), to the on_finished method.
    If there is an exception, there will be no result.
    """
    item_text = item
    item_id = getID(item)
    item = nvdbFagdata(item_id)
    if qtGui.kommuneCheck.isChecked():
        kommuneID = getKommuneID(str(qtGui.kommuneBox.currentText()))
        item.filter({'kommune': kommuneID})
    elif qtGui.kontraktCheck.isChecked():
        item.filter({'kontraktsomrade': str(qtGui.kontraktBox.currentText())})
    else:
        fylkeID = getFylkeID(str(qtGui.fylkeBox.currentText()))
        item.filter({'fylke': fylkeID})
    if returnSelectedVegreferanse() != "Alle":
        item.filter({'vegsystemreferanse': [returnSelectedVegreferanse()[0]]})
    if task.isCanceled():
        stopped(task)
        return None
    # raise an exception to abort the task
    if task == "Ikke test denne":
        raise Exception('no pls')
    return {'name': task, 'item': item, 'item_text': item_text}


def stopped(task):
    print("Task stopped" + task)


def completed(exception, result=None):
    """This is called when doSomething is finished.
    Exception is not None if doSomething raises an exception.
    result is the return value of doSomething."""

    if exception is None:
        if result is None:
            print('Completed with no exception and no result')
        else:
            nvdbsok2qgis(result['item'], lagnavn=result['item_text'])
    else:
        print("Exception" + str(exception))
        raise exception
