# -*- coding: utf-8 -*-
import os.path
import csv

from nvdbapiv3 import nvdbFagdata
from qgis.core import *
from qgis import processing
from nvdbapiV3qgis3 import nvdbsok2qgis
from .nvdbobjects import *
from .nvdbareas import *
from .nvdbpresets import *
from .lastsearch import *
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QDockWidget, QTableWidgetItem
from collections import namedtuple

from qgis.PyQt.QtWidgets import QAction, QFileDialog
from PyQt5.QtWidgets import QHeaderView

from .csvdiff import csvdiff
from datetime import date
# Initialize Qt resources from file resources.py
# Denne brukes bare når gui starter, ikke slett
from .resources import *
# Import the code for the dialog
from .nvdb_qgis_plugin_dialog import NvdbQgisPluginDialog


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
        # Connecter alle knapper og andre actions
        self.dlg.dirOldButton.clicked.connect(self.select_oldDir)
        self.dlg.dirNewButton.clicked.connect(self.select_newDir)
        self.dlg.dirResultButton.clicked.connect(self.select_dirResult)
        self.dlg.mengdertilcsvButton.clicked.connect(self.getStats)
        self.dlg.selectdir_MButton.clicked.connect(self.select_output_dirM)
        self.dlg.skrivtilcsvButton.clicked.connect(self.exportLayers)
        self.dlg.compareButton.clicked.connect(self.comparefiles)
        self.dlg.comboBox.currentIndexChanged[str].connect(self.comboBox_itemChanged)
        self.dlg.addButton.clicked.connect(self.addItem)
        self.dlg.removeButton.clicked.connect(self.removeItem)
        self.dlg.clearButton.clicked.connect(self.clearSelection)
        self.dlg.kommuneCheck.toggled.connect(self.kommuneSelected)
        self.dlg.checkBox_fritekst.toggled.connect(self.comp_checkbox_handler_free)
        self.dlg.checkBox_nvdbid.toggled.connect(self.comp_checkbox_handler_nvdbid)
        self.dlg.checkBox_objekt.toggled.connect(self.comp_checkbox_handler_object)
        self.dlg.kontraktCheck.toggled.connect(self.kontraktSelected)
        self.dlg.fylkeBox.currentIndexChanged[str].connect(self.getKommune)
        self.dlg.fylkeBox.currentIndexChanged[str].connect(self.getKontrakt)
        self.dlg.fylkeBox.currentIndexChanged.connect(self.fylkeBox_itemChanged)
        self.dlg.kommuneBox.currentIndexChanged[str].connect(self.kommuneBox_itemChanged)
        self.dlg.kontraktBox.currentIndexChanged[str].connect(self.kontraktBox_itemChanged)
        # self.dlg.mergeButton.clicked.connect(self.mergeLayers)
        self.dlg.selectdirButton.clicked.connect(self.select_output_dir)
        self.dlg.kjorButton.clicked.connect(self.runTask)
        self.dlg.saveButton.clicked.connect(self.saveAsPreset)
        self.dlg.vegsystemBox.currentIndexChanged[str].connect(self.vegsystemBox_itemChanged)
        self.dlg.searchTable.doubleClicked.connect(self.searchPreset)
        self.dlg.deleteButton.clicked.connect(self.deletePreset)
        self.dlg.statsButton.clicked.connect(self.loadStats)
        self.dlg.folderButton.clicked.connect(self.openFolder)
        # Henter filtreringsdata
        getAllAreaData()
        # Henter vegobjekter
        getAllObjectData()
        # Henter alle presets
        getAllPresetData()
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
        """
        Funksjonen sammenligner csv filer.
        Funksjonen tar filer fra to mapper, leser igjennom mappen og sammenligner
        De filene som har likt navn.
        Om det finnes filer i en mappe og ikke i den andre mappen vil disse filene fjernes fra sammenligningen.
        """

        dirOldFiles = []
        dirNewFiles = []

        selectedDirOld = self.dlg.lineEdit_dirOld.text().strip()
        selectedDirNew = self.dlg.lineEdit_dirNew.text().strip()
        selectedOutPutDir = self.dlg.lineEdit_dirResult.text().strip()

        filnameInp = self.dlg.lineEdit_resNavn.text().strip()

        colval = self.comp_checkbox_handler_nvdbid(), self.comp_checkbox_handler_object(), self.comp_checkbox_handler_free()

        col = ''
        i = 0
        """
        Itererer gjennom colval listen, og gir col en gyldig verdi.
        Verdien brukes til å sammenligne koloner. 
        """
        while colval[i] is None:
            i += 1
            if i == 3:
                self.errorMessage("Du må angi en kolone!")
                break
        else:
            col = colval[i]

        if filnameInp:
            outputFilename = ('Resultat' + '_' + filnameInp + '_' + str(date.today()) + '.csv')

            file_path = os.path.join(selectedOutPutDir, outputFilename)
            if not os.path.isdir(selectedOutPutDir):
                os.makedirs(selectedOutPutDir)
            # Ignorerer filer som ikke er csv filer
            for filenameOld in os.listdir(selectedDirOld):
                if filenameOld.endswith(".csv"):
                    dirOldFiles.append(filenameOld)
                else:
                    print("Mappen inneholder noen filer som ikke er .csv filer, disse blir ignorert")
            # Ignorerer filer som ikke er csv filer
            for filenameNew in os.listdir(selectedDirNew):
                if filenameNew.endswith(".csv"):
                    dirNewFiles.append(filenameNew)

                else:
                    print("Mappen inneholder noen filer som ikke er .csv filer, disse blir ignorert")
            """
            Sjekker etter filer som har samme navn, de filene som ikke har same navn vil bli lagt i en liste og
            brukeren vil se hvilken filer som ikke ligger i sjekkmappen, diroldfiles.
            """
            filter_listold = [string for string in dirOldFiles if string not in dirNewFiles]
            if not filter_listold:
                pass
            else:
                print('Disse filene: ', filter_listold,
                      'finnes ikke i sjekk mappen, disse vil bli fjernet fra sammenligningen.')
                for i in filter_listold:
                    dirOldFiles.remove(i)

            filter_listnew = [string for string in dirNewFiles if string not in dirOldFiles]
            if not filter_listnew:
                pass
            else:
                print('Disse filene: ', filter_listnew,
                      'finnes ikke i sjekk mappen, disse vil bli fjernet fra sammenligningen.')

                for i in filter_listnew:
                    dirNewFiles.remove(i)

            checkfile = []
            newcheck = []
            fileResult = open(file_path, 'w')
            for oldfile in dirOldFiles:
                checkfile.append(oldfile)

            for newfile in dirNewFiles:
                newcheck.append(newfile)

            fileResult.write("Resultat av sammenligning, " + "Dato: " + str(date.today()) + '\n')

            for old, new in zip(checkfile, newcheck):
                # print('{} {}'.format(old, new))
                patch = csvdiff.diff_files(selectedDirOld + '/' + old,
                                           selectedDirNew + '/' + new,
                                           [col])
                if patch[
                    "changed"]:  # Om nøkkelen "changed" har en verdi vil den returnere true og gjennomføre utskriften til fileResult.
                    fileResult.write('\n' + "Endringer i fil: " + new + '\n')
                    for c in (patch['changed']):
                        fileResult.write(str(c) + '\n')
                else:
                    self.dlg.textEdit.append("Ingen felt er endret i filen: " + new)

                if patch[
                    "removed"]:  # Om nøkkelen "removed" har en verdi vil den returnere true og gjennomføre utskriften til fileResult.
                    fileResult.write('\n' + "Objekter fjernet i fil: " + new + '\n')
                    for r in (patch['removed']):
                        fileResult.write(str(r) + '\n')
                else:
                    self.dlg.textEdit.append("Ingen objekter er fjernet i fil: " + new)

                if patch[
                    "added"]:  # Om nøkkelen "added" har en verdi vil den returnere true og gjennomføre utskriften til fileResult.
                    fileResult.write('\n' + "Objekter lagt til i fil: " + new + '\n')
                    for a in (patch['added']):
                        fileResult.write(str(a) + '\n')
                else:
                    self.dlg.textEdit.append("Ingen objekter er lagt til i fil: " + new)

                if patch:
                    self.successMessage("Sammenligning av fil: " + new + " er ferdig")
            fileResult.close()
            self.successMessage("Navn på resultatfil: " + outputFilename)
        else:
            self.errorMessage("Du må gi filen et navn!")

    def exportLayers(self):
        today = date.today()
        dmy = today.strftime("_%d%m%y")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "CSV"

        # Henter filsti
        output_dir_path = self.dlg.lineEdit_dir.text().strip()
        output_dir_input = self.dlg.lineEdit_newDirName.text().strip()

        if output_dir_input and output_dir_path:
            output_dir = (output_dir_path + '/' + output_dir_input + dmy)
            try:
                os.makedirs(output_dir)
            except OSError:
                self.errorMessage("Klarte ikke å lagre ny mappe")
            else:
                for layer in self.iface.mapCanvas().layers():
                    if layer.type() == QgsMapLayer.VectorLayer:

                        self.dlg.textEdit.append('Skriver: ' + layer.name() + ' til CSV')
                        layer_filename = os.path.join(output_dir, layer.name())
                        writer = QgsVectorFileWriter.writeAsVectorFormatV2(layer,
                                                                           layer_filename,
                                                                           QgsCoordinateTransformContext(),
                                                                           options)
                        self.successMessage("Utskrift av lag: " + layer.name() + " er fullført")
                        if writer[0]:
                            self.iface.messageBar().pushMessage("NVDB Utskrift Error",
                                                                "Klarte ikke å skrive ut: " +
                                                                layer.name() +
                                                                " Status: " +
                                                                str(writer),
                                                                level=Qgis.Critical)
                self.successMessage('Utskrift fullført!')
        elif not output_dir_input:
            self.errorMessage("Du må gi den nye mappen et navn!")
        elif not output_dir_path:
            self.errorMessage("Du må velge en filsti!")

    def select_output_dir(self):
        output_dir = QFileDialog.getExistingDirectory(self.dlg, "Velg filsti", "")
        self.dlg.lineEdit_dir.setText(output_dir)

    def comp_checkbox_handler_free(self):
        """
        Om checkboxen for fritekst er checket og den inneholder en verdi vil den returnere
        denne verdien til colval.
        """
        colval = ''
        if self.dlg.checkBox_fritekst.isChecked():
            colval = self.dlg.lineEdit_fritekst.text().strip()
            self.dlg.checkBox_nvdbid.setEnabled(False)
            self.dlg.checkBox_objekt.setEnabled(False)
            if self.dlg.lineEdit_fritekst.text().strip() is '':
                self.errorMessage("Du må angi en kolone!")
                self.dlg.lineEdit_fritekst.setText("Angi en Kolone!")
        else:
            self.dlg.checkBox_nvdbid.setEnabled(True)
            self.dlg.checkBox_objekt.setEnabled(True)
        return colval

    def comp_checkbox_handler_nvdbid(self):
        """
        Om checkboxen for nvdbid er checket vil den returnere nvdbid til colval.
        Denne verdien brukes for å sammenligne koloner i csvfiler generert av utskriften til
        attributt tabellen til lagene i qgis.
        """
        if self.dlg.checkBox_nvdbid.isChecked():
            colval = 'nvdbid'
            self.dlg.checkBox_objekt.setEnabled(False)
            self.dlg.checkBox_fritekst.setEnabled(False)
            return colval
        else:
            self.dlg.checkBox_objekt.setEnabled(True)
            self.dlg.checkBox_fritekst.setEnabled(True)

    def comp_checkbox_handler_object(self):
        """
        Om checkboxen for objekt er checked vil den returnere Objekt til colval.
        Denne verdien brukes for å sammenligne koloner i csvfiler generert av utskrift av mengder.
        Disse mengdene blir hentet fra NVDB.
        """
        if self.dlg.checkBox_objekt.isChecked():
            colval = 'Objekt'
            self.dlg.checkBox_nvdbid.setEnabled(False)
            self.dlg.checkBox_fritekst.setEnabled(False)
            return colval
        else:
            self.dlg.checkBox_nvdbid.setEnabled(True)
            self.dlg.checkBox_fritekst.setEnabled(True)

    def kommuneSelected(self):
        """
        Sjekker om kommune er valgt som filter.
        Bare en av checkboxene skal kunne velges samtidig.
        Derfor uncheckes andre når en er trykket
        """
        if self.dlg.kommuneCheck.isChecked():
            self.displayFilters()
            self.dlg.kommuneBox.setEnabled(True)
            self.dlg.kontraktCheck.setChecked(False)
            self.dlg.kontraktBox.setEnabled(False)
        else:
            self.displayFilters()
            self.dlg.kommuneBox.setEnabled(False)

    def kontraktSelected(self):
        if self.dlg.kontraktCheck.isChecked():
            self.displayFilters()
            self.dlg.kontraktBox.setEnabled(True)
            self.dlg.kommuneCheck.setChecked(False)
            self.dlg.kommuneBox.setEnabled(False)
        else:
            self.displayFilters()
            self.dlg.kontraktBox.setEnabled(False)

    def fylkeBox_itemChanged(self):
        self.displayFilters()

    def kommuneBox_itemChanged(self, index):
        self.dlg.textEdit.append("Kommune: " + index)
        self.displayFilters()

    def kontraktBox_itemChanged(self, index):
        self.dlg.textEdit.append("Kontraktsområde: " + index)
        self.displayFilters()

    def vegsystemBox_itemChanged(self, index):
        self.dlg.textEdit.append("Vegsystemreferanse: " + index)
        selectedVegreferanse(index)
        self.displayFilters()

    def comboBox_itemChanged(self, index):
        """
        Henter vegobjekter når kategori endres.
        """
        self.dlg.listWidgetObjects.clear()
        self.dlg.textEdit.append("Kategori: " + index)
        if index == "Alle":
            items = getNames()
            self.dlg.listWidgetObjects.addItems(sorted(items))
        else:
            items = getObjInCat(index)
            self.dlg.listWidgetObjects.addItems(items)

    def addItem(self):
        """
        Legger valgte vegobjekter i listene
        """
        all_items = self.dlg.listWidgetObjects.selectedItems()
        for i in range(len(all_items)):
            self.dlg.listWidget.addItem(all_items[i].text())
            self.dlg.objectsList_Search.addItem(all_items[i].text())
            self.dlg.listWidget_layers.addItem(all_items[i].text())
            self.dlg.textEdit.append("Lagt til " + all_items[i].text())
        self.dlg.listWidgetObjects.clearSelection()

    def removeItem(self):
        """
        Fjerner vegobjekter fra listene
        """
        selected_items = self.dlg.listWidget.selectedItems()
        if not selected_items:
            pass
        else:
            for i in range(len(selected_items)):
                r = self.dlg.listWidget.row(selected_items[i])
                self.dlg.textEdit.append("Fjernet " + selected_items[i].text())
                self.dlg.listWidget.takeItem(r)
                self.dlg.objectsList_Search.takeItem(r)
                self.dlg.listWidget_layers.takeItem(r)

    def successMessage(self, message):
        """
        Grønn tekst i textbox
        """
        successText = "<span style=\" color:#4cc27e;\" >"
        successText += message
        successText += "</span>"
        self.dlg.textEdit.append(successText)

    def errorMessage(self, message):
        """
        Rød tekst i textbox
        """
        errorText = "<span style=\" color:#ff0000;\" >"
        errorText += message
        errorText += "</span>"
        self.dlg.textEdit.append(errorText)

    def boldText(self, message):
        """
        Fet tekst i textbox
        """
        boldText = "<span style=\" font-weight:bold;\" >"
        boldText += message
        boldText += "</span>"
        return boldText

    def clearSelection(self):
        self.dlg.listWidgetObjects.clearSelection()

    def getKommune(self, index):
        self.dlg.textEdit.append("Fylke: " + index)
        self.dlg.kommuneBox.clear()
        self.dlg.kommuneBox.addItems(getKommuneNavn(index))

    def getKontrakt(self, index):
        self.dlg.kontraktBox.clear()
        self.dlg.kontraktBox.addItems(getKontraktNavn(index))

    def displayFilters(self):
        """
        Viser valgte filtre i textboxer
        """
        self.dlg.searchEdit.clear()
        self.dlg.filterEdit.clear()
        if self.dlg.kommuneCheck.isChecked():
            self.dlg.searchEdit.append(self.boldText("Kommune"))
            self.dlg.searchEdit.append(self.dlg.kommuneBox.currentText())
            self.dlg.filterEdit.append(self.boldText("Kommune"))
            self.dlg.filterEdit.append(self.dlg.kommuneBox.currentText())
        if self.dlg.kontraktCheck.isChecked():
            self.dlg.searchEdit.append(self.boldText("Kontraktsområde"))
            self.dlg.searchEdit.append(self.dlg.kontraktBox.currentText())
            self.dlg.filterEdit.append(self.boldText("Kontraktsområde"))
            self.dlg.filterEdit.append(self.dlg.kontraktBox.currentText())
        else:
            self.dlg.searchEdit.append(self.boldText("Fylke"))
            self.dlg.searchEdit.append(self.dlg.fylkeBox.currentText())
            self.dlg.filterEdit.append(self.boldText("Fylke"))
            self.dlg.filterEdit.append(self.dlg.fylkeBox.currentText())
        self.dlg.searchEdit.append(" ")
        self.dlg.searchEdit.append(self.boldText("Vegsystemreferanse"))
        self.dlg.searchEdit.append(self.dlg.vegsystemBox.currentText())
        self.dlg.filterEdit.append(" ")
        self.dlg.filterEdit.append(self.boldText("Vegsystemreferanse"))
        self.dlg.filterEdit.append(self.dlg.vegsystemBox.currentText())

    """
    def mergeLayers(self):
    
        Denne funskjonen slo sammen lag av samme vegobjektstype der
        det var mulig.
        Fungerer fint i QGIS 3.10, men nyere versjoner har problemer.
        Kan kanskje brukes senere om en finner en måte å løse problemene på.
        
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
    """

    def saveAsPreset(self):
        """
        Lagrer valgte vegobjekter og valgt filtrering
        som ett preset
        """
        objList = [str(self.dlg.listWidget.item(i).text()) for i in range(self.dlg.listWidget.count())]
        areaType = None
        area = None
        if self.dlg.kommuneCheck.isChecked():
            area = str(self.dlg.kommuneBox.currentText())
            areaType = "kommune"
        elif self.dlg.kontraktCheck.isChecked():
            area = str(self.dlg.kontraktBox.currentText())
            areaType = "kontraktsomrade"
        else:
            area = str(self.dlg.fylkeBox.currentText())
            areaType = "fylke"
        road = returnSelectedVegreferanse()
        filename = self.dlg.nameField.text()
        relPath = os.path.dirname(os.path.abspath(__file__))
        presetPath = os.path.join(relPath, "presets")
        path = os.path.join(presetPath, filename + ".txt")
        file = open(path, "w")
        file.write(str(objList) + ";" + areaType + ";" + area + ";" + road)
        file.close()
        # Laster inn alle presets på nytt
        getAllPresetData()
        self.loadPresets()
        self.successMessage(filename + " lagret!")
        self.dlg.nameField.clear()
        self.dlg.listWidget.clear()
        self.dlg.objectsList_Search.clear()

    def loadPresets(self):
        nameList = returnNameData()
        objList = returnObjectData()
        areaTypeList = returnAreaTypeData()
        areaList = returnAreaData()
        road = returnRoadData()
        # Row count
        self.dlg.searchTable.setRowCount(len(objList))
        # Column count
        self.dlg.searchTable.setColumnCount(5)
        for i in range(len(road)):
            self.dlg.searchTable.setItem(i, 0, QTableWidgetItem(nameList[i]))
            self.dlg.searchTable.setItem(i, 1, QTableWidgetItem(objList[i]))
            self.dlg.searchTable.setItem(i, 2, QTableWidgetItem(areaTypeList[i]))
            self.dlg.searchTable.setItem(i, 3, QTableWidgetItem(areaList[i]))
            self.dlg.searchTable.setItem(i, 4, QTableWidgetItem(road[i]))
        # Table will fit the screen horizontally
        self.dlg.searchTable.horizontalHeader().setStretchLastSection(True)
        self.dlg.searchTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)

    def searchPreset(self):
        """
        Søker på valgt preset
        """
        rowNumber = None
        for i in self.dlg.searchTable.selectionModel().selectedIndexes():
            rowNumber = i.row()
        objList = self.dlg.searchTable.item(rowNumber, 1).text()
        objList = objList[1:-1]
        objList = objList.split(',')
        areaType = self.dlg.searchTable.item(rowNumber, 2).text()
        area = self.dlg.searchTable.item(rowNumber, 3).text()
        road = self.dlg.searchTable.item(rowNumber, 4).text()
        setLastSearch(area, areaType, road)
        pythonConsole = self.iface.mainWindow().findChild(QDockWidget, 'PythonConsole')
        if not pythonConsole or not pythonConsole.isVisible():
            self.iface.actionShowPythonDialog().trigger()
        for i in range(len(objList)):
            if i == 0:
                item = objList[i]
            else:
                item = objList[i][1:]
            item = item[1:-1]
            task = QgsTask.fromFunction("Henter: " + objList[i], getLayersFromPreset, on_finished=completed,
                                        item=item, areaType=areaType, area=area, road=road)
            self.tm.addTask(task)

    def deletePreset(self):
        rowNumber = None
        for i in self.dlg.searchTable.selectionModel().selectedIndexes():
            rowNumber = i.row()
        name = self.dlg.searchTable.item(rowNumber, 0).text()
        relPath = os.path.dirname(os.path.abspath(__file__))
        presetPath = os.path.join(relPath, "presets")
        path = os.path.join(presetPath, name + ".txt")
        os.remove(path)
        self.dlg.searchTable.removeRow(rowNumber)
        getAllPresetData()
        self.loadPresets()
        self.successMessage(name + " slettet.")

    def openFolder(self):
        """
        Åpner mappen som inneholder tekstfilene med presets
        """
        import subprocess
        relPath = os.path.dirname(os.path.abspath(__file__))
        presetPath = os.path.join(relPath, "presets")
        subprocess.Popen(f'explorer "{presetPath}"')

    def getStats(self):
        """
        Henter mengdedata til objekter lagret i NVDB.
        Denne dataen blir hentet med filtrering gitt av bruker.
        Dataen blir skrevet til en csvfil.
        """
        objList = [str(self.dlg.listWidget_layers.item(i).text()) for i in range(self.dlg.listWidget_layers.count())]
        valueList, indexList, antallList, lengdeList, areallist, itemlist, arealsum, data, namelist, statslist, rnonelist = [], [], [], [], [], [], [], [], [], [], []
        colnavn = namedtuple('colnavn', ['Objekt', 'Antall', 'Lengde', 'Areal'])

        today = date.today().strftime("_%d%m%y")
        output_dir_path = self.dlg.lineEdit_dir_m.text().strip()
        userin_file_name = self.dlg.lineEdit_fileNameM.text().strip()

        # Sjekker at bruker har oppgitt filnavn og filsti for utskrift.
        if userin_file_name and output_dir_path:
            output_dir = (output_dir_path + '/' + 'Mengder_' + today)
            try:
                os.makedirs(output_dir)
            except OSError:
                self.errorMessage("Klarte ikke å lage nye mappe")
            else:
                filename = os.path.join(output_dir + '/' + userin_file_name + '.csv')
                print(filename)
                with open(filename, 'w', newline='', encoding='utf8') as fm:
                    writer = csv.writer(fm, delimiter=',')
                    writer.writerow(colnavn._fields)
                    # Leser objekt fra en objekt liste laget av bruker og legger til filtrering gitt av bruker.
                    for itemname in objList:
                        namelist.append(itemname)
                        item_id = getID(itemname)
                        item = nvdbFagdata(item_id)
                        if self.dlg.kommuneCheck.isChecked():
                            kommuneID = getKommuneID(str(self.dlg.kommuneBox.currentText()))
                            item.filter({'kommune': kommuneID})
                        elif self.dlg.kontraktCheck.isChecked():
                            kontraktID = str(self.dlg.kontraktBox.currentText())
                            item.filter({'kontraktsomrade': kontraktID})
                        else:
                            fylkeID = getFylkeID(str(self.dlg.fylkeBox.currentText()))
                            item.filter({'fylke': fylkeID})
                        if returnSelectedVegreferanse() != "Alle":
                            item.filter({'vegsystemreferanse': [returnSelectedVegreferanse()[0]]})
                        # Statistikk() er en funksjon fra NVDB som henter ut lengde og data for det gitte objektet.
                        for v in item.statistikk().items():
                            valueList.append(v)
                        itemlist.append(item)

                    # Henter ut arealverdien til objektet fra NVDB.
                    for itemobj in itemlist:
                        while itemobj is not None:
                            areal = itemobj.nesteNvdbFagObjekt()
                            if areal is None:
                                break
                            else:
                                areallist.append(areal.egenskapverdi('Areal'))
                                continue
                        else:
                            break
                    # Deler valueList. En liste med lengde verdi og en med antall verdi.
                    for i in valueList:
                        indexList.append(i)
                    for a in range(0, len(indexList), 2):
                        antallList.append(valueList[a])
                    for l in range(1, len(indexList), 2):
                        lengdeList.append(valueList[l])

                    start = 0
                    i = 0
                    # Skriver verdiene til fil.
                    for antall, lengde in zip(antallList, lengdeList):
                        # print('{} {}'.format(antall[1], lengde[1]))
                        for a in range(1, len(antall)):
                            value = antall[a]
                            arealsum = areallist[start:start + value]
                            start += value
                            rnone = [0 if x is None else x for x in arealsum]
                            rnonelist.append(sum(rnone))
                        if rnone is not None:
                            a = sum(rnone)
                            data.append(namelist[i])
                            i += 1
                            data.append(antall[1])
                            data.append(lengde[1])
                            data.append(a)
                            writer.writerow(data)
                            data.clear()
                        else:
                            pass
                fm.close()
                self.successMessage('Utskrift fullført!')
        elif not userin_file_name:
            self.errorMessage("Du må gi filen et navn!")
        elif not output_dir_path:
            self.errorMessage("Du må velge en filsti!")

        statslist = [namelist, antallList, lengdeList, rnonelist]
        return statslist

    def select_output_dirM(self):
        output_dir_path = QFileDialog.getExistingDirectory(self.dlg, "Velg filsti", "")
        self.dlg.lineEdit_dir_m.setText(output_dir_path)

    def stat(self):
        stats = self.getStats()
        print(stats)

    def loadStats(self):
        """
        Henter statistikk fra layers i QGIS. Bruker siste filtrering brukt
        som grunnlag. Se lastsearch.py
        """
        names = self.getLayerNames()
        data = getLastSearch()
        valueList, itemList, amountList, lenghtList, areaList, areaTotalList = [], [], [], [], [], []

        for i in names:
            if i == "OpenStreetMap":
                names.remove(i)
            else:
                pass

        for i in names:
            item_id = getID(i)
            item = nvdbFagdata(item_id)
            if data[1] == "kommune":
                kommuneID = getKommuneID(data[0])
                item.filter({'kommune': kommuneID})
            elif data[1] == "kontraktsomrade":
                item.filter({'kontraktsomrade': data[0]})
            else:
                fylkeID = getFylkeID(data[0])
                item.filter({'fylke': fylkeID})
            if data[2] != "Alle":
                item.filter({'vegsystemreferanse': [data[2][0]]})
            for v in item.statistikk().items():
                valueList.append(v)
            itemList.append(item)

            for itemobj in itemList:
                while itemobj is not None:
                    area = itemobj.nesteNvdbFagObjekt()
                    if area is None:
                        break
                    else:
                        areaList.append(area.egenskapverdi('Areal'))
                        continue
                else:
                    print("TEST")
                    break

        for i in range(len(valueList)):
            v = valueList[i]
            if v[0] == "antall":
                amountList.append(v[1])
            else:
                lenghtList.append(v[1])

        for i in range(len(amountList)):
            areaTotal = 0
            for u in range(amountList[i]):
                if areaList[u] is not None:
                    if isinstance(areaList[u], str):
                        pass
                    else:
                        areaTotal += areaList[u]
                else:
                    pass
            areaTotalList.append(areaTotal)
            areaList = areaList[amountList[i]:]

        # Row count
        self.dlg.statsTable.setRowCount(len(names) + 1)
        # Column count
        self.dlg.statsTable.setColumnCount(4)
        self.dlg.statsTable.setItem(0, 0, QTableWidgetItem("Navn"))
        self.dlg.statsTable.setItem(0, 1, QTableWidgetItem("Mengde"))
        self.dlg.statsTable.setItem(0, 2, QTableWidgetItem("Lengde"))
        self.dlg.statsTable.setItem(0, 3, QTableWidgetItem("Areal"))
        for i in range(len(names) + 1):
            if i == len(names):
                break
            else:
                self.dlg.statsTable.setItem(i + 1, 0, QTableWidgetItem(names[i]))
                self.dlg.statsTable.setItem(i + 1, 1, QTableWidgetItem(str(amountList[i])))
                self.dlg.statsTable.setItem(i + 1, 2, QTableWidgetItem(str(round(int(lenghtList[i])))))
                self.dlg.statsTable.setItem(i + 1, 3, QTableWidgetItem(str(round(int(areaTotalList[i])))))
        # Table will fit the screen horizontally
        self.dlg.statsTable.horizontalHeader().setStretchLastSection(True)
        self.dlg.statsTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.successMessage("Viser statistikk for layers innenfor " + data[1] + ":")
        self.successMessage(data[0])
        self.successMessage("Vegsystemreferanse:")
        self.successMessage(data[2])

    def getLayerNames(self):
        """
        Henter alle layer navn.
        Ekskluderer alle som er duplikater eller bare forskjellig WKT type.
        """
        project = QgsProject.instance()
        nameList = []
        for id, layer in project.mapLayers().items():
            nameList.append(layer.name())
        for i in range(len(nameList)):
            if nameList[i][-3:] == "_2d" or nameList[i][-3:] == "_3d":
                nameList[i] = nameList[i][:-3]
        nameList = list(dict.fromkeys(nameList))
        return nameList

    def runTask(self):
        if self.dlg.kommuneCheck.isChecked():
            area = getKommuneID(str(self.dlg.kommuneBox.currentText()))
            areaType = "kommune"
        elif self.dlg.kontraktCheck.isChecked():
            area = str(self.dlg.kontraktBox.currentText())
            areaType = "kontraktsomrade"
        else:
            area = getFylkeID(str(self.dlg.fylkeBox.currentText()))
            areaType = "fylke"
        setLastSearch(area, areaType, returnSelectedVegreferanse())
        pythonConsole = self.iface.mainWindow().findChild(QDockWidget, 'PythonConsole')
        if not pythonConsole or not pythonConsole.isVisible():
            self.iface.actionShowPythonDialog().trigger()
        objList = [str(self.dlg.listWidget.item(i).text()) for i in range(self.dlg.listWidget.count())]
        for item in objList:
            """
            Legger til søk som en task.
            Det blir en kø som kjører alle søk etter hverandre.
            Gjør at QGIS ikke henger seg opp på langt nær like mye som uten
            """
            task = QgsTask.fromFunction("Henter: " + item, getLayers, on_finished=completed, item=item, qtGui=self.dlg)
            self.tm.addTask(task)

    def run(self):
        if self.first_start:
            self.dlg.kommuneBox.setEnabled(False)
            self.dlg.kontraktBox.setEnabled(False)
            self.displayFilters()
            self.loadPresets()
            self.first_start = False
        self.dlg.comboBox.clear()
        self.dlg.comboBox.addItems(sortCategories())
        self.dlg.fylkeBox.addItems(getFylkeNavn())
        self.dlg.openLayers = QgsProject.instance().layerTreeRoot().children()
        self.dlg.listWidget_layers.clear()
        self.dlg.show()
        result = self.dlg.exec_()
        if result:
            """ Close """


"""
Her kjøres taskene
"""


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


def getLayersFromPreset(task, item, areaType, area, road):
    item_text = item
    item_id = getID(item)
    item = nvdbFagdata(item_id)
    if areaType == "kommune":
        kommuneID = getKommuneID(area)
        item.filter({'kommune': kommuneID})
    elif areaType == "kontraktsomrade":
        item.filter({'kontraktsomrade': area})
    else:
        fylkeID = getFylkeID(area)
        item.filter({'fylke': fylkeID})
    if road != "Alle":
        item.filter({'vegsystemreferanse': road[0]})
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
    """This is called when getLayers is finished.
    Exception is not None if getLayers raises an exception.
    result is the return value of getLayers."""

    if exception is None:
        if result is None:
            print('Completed with no exception and no result')
        else:
            nvdbsok2qgis(result['item'], lagnavn=result['item_text'])
    else:
        print("Exception" + str(exception))
        raise exception
