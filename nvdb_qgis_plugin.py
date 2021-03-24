# -*- coding: utf-8 -*-
import os.path
import os
from nvdbapiv3 import nvdbFagdata
from qgis._core import QgsProject, QgsWkbTypes, QgsProcessingException
from qgis.core import *
from qgis.utils import iface
from qgis import processing
from nvdbapiV3qgis3 import nvdbsok2qgis
from .nvdbobjects import *
from .nvdbareas import *
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from PyQt5.QtWidgets import QListView, QMessageBox
from PyQt5 import QtGui, QtCore

import csvdiff
import itertools as itools
from datetime import date

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .nvdb_qgis_plugin_dialog import NvdbQgisPluginDialog


class NvdbQgisPlugin:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.dlg = NvdbQgisPluginDialog()
        self.iface = iface
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
        self.dlg.dirOldButton.clicked.connect(self.select_oldDir)
        self.dlg.dirNewButton.clicked.connect(self.select_newDir)
        self.dlg.dirResultButton.clicked.connect(self.select_dirResult)
        self.dlg.skrivtilcsvButton.clicked.connect(self.exportLayers)
        self.dlg.compareButton.clicked.connect(self.comparefiles)
        self.dlg.comboBox.currentIndexChanged[str].connect(self.comboBox_itemChanged)
        self.dlg.addButton.clicked.connect(self.addItem)
        self.dlg.removeButton.clicked.connect(self.removeItem)
        self.dlg.clearButton.clicked.connect(self.clearSelection)
        self.dlg.individCheck.toggled.connect(self.individualSelected)
        self.dlg.kommuneCheck.toggled.connect(self.kommuneSelected)
        self.dlg.kontraktCheck.toggled.connect(self.kontraktSelected)
        self.dlg.fylkeBox.currentIndexChanged[str].connect(self.getKommune)
        self.dlg.fylkeBox.currentIndexChanged[str].connect(self.getKontrakt)
        self.dlg.mergeButton.clicked.connect(self.mergeLayers)
        self.dlg.selectdirButton.clicked.connect(self.select_output_dir)
        # Get filterdata
        # TODO: Get catagories
        getAllData()

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


    def select_oldDir(self):
        selectedDirOld = QFileDialog.getExistingDirectory(self.dlg, "Velg filsti", "")
        self.dlg.lineEdit_dirOld.setText(selectedDirOld)
    def select_newDir(self):
        selectedDirNew = QFileDialog.getExistingDirectory(self.dlg, "Velg filsti", "")
        self.dlg.lineEdit_dirNew.setText(selectedDirNew)
    def select_dirResult(self):
        output_dirResult = QFileDialog.getExistingDirectory(self.dlg, "Velg filsti", "")
        self.dlg.lineEdit_dirResult.setText(output_dirResult)

    def comparefiles(self):
        dirOldFiles = []
        dirNewFiles = []

        selectedDirOld = self.dlg.lineEdit_dirOld.text().strip()
        selectedDirNew = self.dlg.lineEdit_dirNew.text().strip()
        selectedOutPutDir = self.dlg.lineEdit_dirResult.text().strip()

        outputFilename = ('Resultat' + '_' + str(date.today()) + '.txt')

        file_path = os.path.join(selectedOutPutDir, outputFilename)
        if not os.path.isdir(selectedOutPutDir):
            os.makedirs(selectedOutPutDir)

        for filenameOld in os.listdir(selectedDirOld):
            if filenameOld.endswith(".csv"):
                dirOldFiles.append(filenameOld)
                #print(dirOldFiles)
            else:
                print("Mappen inneholder noen filer som ikke er .csv filer, disse blir ignorert")

        for filenameNew in os.listdir(selectedDirNew):
            if filenameNew.endswith(".csv"):
                dirNewFiles.append(filenameNew)
                #print(dirNewFiles)
            else:
                print("Mappen inneholder noen filer som ikke er .csv filer, disse blir ignorert")

        #Sjekker etter filer som har samme nanv, de filene som ikke har same navn vil bli lagt i en liste og
        #brukeren vil se hvilken filer som ikke ligger i sjekkmappen, diroldfiles.
        filter_listold = [string for string in dirOldFiles if string not in dirNewFiles]
        if not filter_listold:
            pass
        else:
            #print('Disse filene: ', filter_listold, 'finnes ikke i sjekk mappen, disse vil bli fjernet fra sammenligningen.')
            for i in filter_listold:
                dirOldFiles.remove(i)

        filter_listnew = [string for string in dirNewFiles if string not in dirOldFiles]
        if not filter_listnew:
            pass
        else:
            #print('Disse filene: ', filter_listnew, 'finnes ikke i sjekk mappen, disse vil bli fjernet fra sammenligningen.')

            for i in filter_listnew:
                dirNewFiles.remove(i)

        checkfile = []
        newcheck = []
        fileResult = open(file_path,'w')
        for oldfile in dirOldFiles:
            checkfile.append(oldfile)

        for newfile in dirNewFiles:
            newcheck.append(newfile)

        fileResult.write("Resultat av sammenligning, " + "Dato: " + str(date.today()) + '\n')

        for old, new in zip(checkfile, newcheck):
            print('{} {}'.format(old, new))

            patch  = csvdiff.diff_files(selectedDirOld + '/' + old,
                                        selectedDirNew + '/' + new,
                                        ['nvdbid'])
            #print(patch)
            if patch["changed"]: #Om nøkkelen "changed" har en verdi vil den returnere true og gjennomføre utskriften til fileResult.
                fileResult.write('\n' + "Endringer i fil: " + new + '\n')
                for c in (patch['changed']):
                    fileResult.write(str(c) + '\n')
            else:
                self.dlg.plainTextEdit.appendPlainText("Ingen felt er endret i filen: " + new)

            if patch["removed"]:#Om nøkkelen "removed" har en verdi vil den returnere true og gjennomføre utskriften til fileResult.
                fileResult.write('\n' + "Objekter fjernet i fil: " + new + '\n')
                for r in (patch['removed']):
                    fileResult.write(str(r) + '\n')
            else:
                self.dlg.plainTextEdit.appendPlainText("Ingen objekter er fjernet i fil: " + new)

            if patch["added"]:#Om nøkkelen "added" har en verdi vil den returnere true og gjennomføre utskriften til fileResult.
                fileResult.write('\n' + "Objekter lagt til i fil: " + new + '\n')
                for a in (patch['added']):
                    fileResult.write(str(a) + '\n')
            else:
                self.dlg.plainTextEdit.appendPlainText("Ingen objekter er lagt til i fil: " + new)

            if patch:
                self.dlg.plainTextEdit.appendPlainText("Sammenligning av fil: " + new + " er ferdig")
        fileResult.close()

    def exportLayers(self):
        today = date.today()
        dmy = today.strftime("_%d%m%y")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "CSV"

        #Henter filsti navn
        output_dir = self.dlg.lineEdit_dir.text().strip()

        for layer in self.iface.mapCanvas().layers():
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.plainTextEdit.appendPlainText('Skriver: ' + layer.name() + ' til CSV')
                layer_filename = os.path.join(output_dir, layer.name())
                writer = QgsVectorFileWriter.writeAsVectorFormatV2(layer,
                                                                   layer_filename + dmy,
                                                                   QgsCoordinateTransformContext(), options)
                if writer[0]:
                    self.iface.messageBar().pushMessage("NVDB Utskrift Error", "Klarte ikke å skrive ut: " + layer.name() + " Status: " + str(writer), level=Qgis.Critical)
        self.dlg.plainTextEdit.appendPlainText('Utskrift fullført!')

    def select_output_dir(self):
        output_dir = QFileDialog.getExistingDirectory(self.dlg, "Velg filsti", "")
        self.dlg.lineEdit_dir.setText(output_dir)

    def individualSelected(self):
        if self.dlg.individCheck.isChecked():
            self.dlg.kommuneCheck.setEnabled(False)
            self.dlg.kontraktCheck.setEnabled(False)
            self.dlg.fylkeBox.setEnabled(False)
            self.dlg.kommuneBox.setEnabled(False)
            self.dlg.kontraktBox.setEnabled(False)
        else:
            self.dlg.kontraktCheck.setEnabled(True)
            self.dlg.kommuneCheck.setEnabled(True)
            self.dlg.fylkeBox.setEnabled(True)

    def kommuneSelected(self):
        if self.dlg.kommuneCheck.isChecked():
            self.dlg.kommuneBox.setEnabled(True)
            self.dlg.individCheck.setEnabled(False)
            self.dlg.kontraktCheck.setEnabled(False)
            self.dlg.kontraktBox.setEnabled(False)
        else:
            self.dlg.kommuneBox.setEnabled(False)
            self.dlg.individCheck.setEnabled(True)
            self.dlg.kontraktCheck.setEnabled(True)

    def kontraktSelected(self):
        if self.dlg.kontraktCheck.isChecked():
            self.dlg.kontraktBox.setEnabled(True)
            self.dlg.individCheck.setEnabled(False)
            self.dlg.kommuneCheck.setEnabled(False)
            self.dlg.kommuneBox.setEnabled(False)
        else:
            self.dlg.kontraktBox.setEnabled(False)
            self.dlg.individCheck.setEnabled(True)
            self.dlg.kommuneCheck.setEnabled(True)

    def comboBox_itemChanged(self, index):
        items = getObjInCat(index)
        self.dlg.plainTextEdit.appendPlainText("Kategori: " + index)
        self.dlg.listWidgetObjects.clear()
        self.dlg.listWidgetObjects.addItems(items)

    def addItem(self):
        all_items = self.dlg.listWidgetObjects.selectedItems()
        for i in range(len(all_items)):
            self.dlg.listWidget.addItem(all_items[i].text())
            self.dlg.plainTextEdit.appendPlainText("Lagt til " + all_items[i].text())
        self.dlg.listWidgetObjects.clearSelection()

    def removeItem(self):
        selected_items = self.dlg.listWidget.selectedItems()
        if not selected_items:
            pass
        else:
            for i in range(len(selected_items)):
                r = self.dlg.listWidget.row(selected_items[i])
                self.dlg.plainTextEdit.appendPlainText("Fjernet " + selected_items[i].text())
                self.dlg.listWidget.takeItem(r)

    def clearSelection(self):
        self.dlg.listWidgetObjects.clearSelection()

    def getKommune(self, index):
        self.dlg.plainTextEdit.appendPlainText("Fylke: " + index)
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

                # TODO: Finn ut hvorfor noen vegobjekter ikke vil slås sammen i algoritmen (Leskur)

                if secondLayerName in currentLayerName and currentLayerType != secondLayerType and (currentLayerName == parameter1 or currentLayerName == parameter2 or currentLayerName == parameter3) and parameter5 == parameter6:
                    self.dlg.plainTextEdit.appendPlainText("Slår sammen: " + currentLayerName + " " + str(currentLayerType) + " " + str(secondLayerType) + " "+ secondLayerName)
                    layerList = [layer, layer_2]
                    completeLayerList.append(layer)
                    completeLayerList.append(layer_2)
                    if len(currentLayerName) > len(secondLayerName):
                        completeLayerName = currentLayerName[:-3]
                    else:
                        completeLayerName = secondLayerName[:-3]
                    try:
                        processing.runAndLoadResults("qgis:mergevectorlayers", {'LAYERS':layerList,
                                'OUTPUT':completeLayerName + " " + QgsWkbTypes.displayString(currentLayerType)})
                    except QgsProcessingException:
                        completeLayerList = completeLayerList[:-2]
                        self.dlg.plainTextEdit.appendPlainText("Fikk problemer med å slå sammen " + str(currentLayerName) + " og " + str(secondLayerName))
                        self.dlg.plainTextEdit.appendPlainText(str(QgsProcessingException))

                    break
                else:
                    pass

        for i in completeLayerList:
            project.removeMapLayers([i.id()])

    def run(self):
        if self.first_start:
            self.first_start = False
        self.dlg.comboBox.clear()
        self.dlg.comboBox.addItems(sortCategories())
        self.dlg.fylkeBox.addItems(getFylkeNavn())
        self.dlg.kommuneBox.setEnabled(False)
        self.dlg.kontraktBox.setEnabled(False)
        self.dlg.filterButton.setEnabled(False)

        self.openLayers = openLayers = QgsProject.instance().layerTreeRoot().children()
        self.dlg.listWidget_layers.clear()
        self.dlg.listWidget_layers.addItems([layer.name() for layer in openLayers])

        self.dlg.show()
        result = self.dlg.exec_()
        if result:

            """ Visualize selected layers """

            objList = [str(self.dlg.listWidget.item(i).text()) for i in range(self.dlg.listWidget.count())]
            for item in objList:
                item_text = item
                item_id = getID(item)
                item = nvdbFagdata(item_id)
                if self.dlg.kommuneCheck.isChecked():
                    kommuneID = getKommuneID(str(self.dlg.kommuneBox.currentText()))
                    item.filter({'kommune': kommuneID})
                elif self.dlg.kontraktCheck.isChecked():
                    item.filter({'kontraktsomrade': str(self.dlg.kontraktBox.currentText())})
                else:
                    fylkeID = getFylkeID(str(self.dlg.fylkeBox.currentText()))
                    item.filter({'fylke': fylkeID})
                nvdbsok2qgis(item, lagnavn=item_text)
            self.dlg.listWidget.clear()
