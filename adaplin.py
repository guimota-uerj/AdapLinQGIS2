# -*- coding: utf-8 -*-

#---------------------------------------------------------------------
# 
# Adaplin - a QGIS Plugin
#
# Copyright (C) 2016 Marcel Rotunno with stuff from Peter Wells for Lutra Consulting (AutoTrace), 
#                    Cédric Möri (traceDigitize) and Radim Blazek (Spline)
#
# EMAIL: marcelgaucho@yahoo.com.br
#
#---------------------------------------------------------------------
# 
# Licensed under the terms of GNU GPL 2
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# 
#---------------------------------------------------------------------



# Import the PyQt and the QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

# Initialize Qt resources from file resources.py
import resources

# Import the code for the dialog
from adaplin_dialog import AdaplinDialog

# Import own classes and tools
from adaplin_tool import Adaplin

# Import code for settings
from settings_dialog import SettingsDialog
from utils import *


class AdaplinControl:
    
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        
        # Create dialog form
        self.dlg = AdaplinDialog()
        
        # Create settings dialog
        self.settingsDialog = SettingsDialog()

   
    def initGui(self):
        mc = self.canvas
        layer = mc.currentLayer()

        # Create action for the plugin icon and the plugin menu
        self.action = QAction( QIcon(":/plugins/AdaplinTool/icon.png"), "Adaplin", self.iface.mainWindow() )
        
        # Button starts disabled and unchecked        
        self.action.setEnabled(False) 
        self.action.setCheckable(True) 
        self.action.setChecked(False) 

        # Add Settings to the [Vector] Menu 
        self.settingsAction = QAction( "Settings", self.iface.mainWindow() )
        #self.iface.addPluginToVectorMenu("&Adaplin Settings", self.settingsAction)
        self.iface.addPluginToMenu("&Adaplin", self.settingsAction)
        self.settingsAction.triggered.connect(self.openSettings) 

        # Add the plugin to Plugin Menu and the Plugin Icon to the Toolbar
        self.iface.addPluginToMenu("&Adaplin", self.action)
        self.iface.addToolBarIcon(self.action)

      
        # Connect signals for button behaviour (map layer change, run the tool and change of QGIS map tool set)
        self.iface.currentLayerChanged['QgsMapLayer*'].connect(self.toggle)
        self.action.triggered.connect(self.run)
        QObject.connect(mc, SIGNAL("mapToolSet(QgsMapTool*)"), self.deactivate)
        
        # Connect the change of the Raster Layer in the ComboBox to function trata_combo
        self.dlg.comboBox.currentIndexChanged.connect(self.trata_combo)
        



    def toggle(self):
        # Get current layer
        mc = self.canvas
        layer = mc.currentLayer()
        #print "Adaplin layer = ", layer.name()
        
        # In case the current layer is None we do nothing
        if layer is None:
            return
        
        #print 'raster type = ', layer.type()
        #print 'e vector = ', layer.type() == layer.VectorLayer
        
        # This is to decide when the plugin button is enabled or disabled
        # The layer must be a Vector Layer
        if layer.type() == layer.VectorLayer:
            # We only care about the Line and Polygon layers
            if layer.geometryType() == QGis.Line or layer.geometryType() == QGis.Polygon:
                # First we disconnect all possible previous signals associated with this layer 
                # If layer is editable, SIGNAL "editingStopped()" is connected to toggle
                # If it is not editable, SIGNAL "editingStarted()" is connected to toggle
                try:
                    layer.editingStarted.disconnect(self.toggle)
                except:
                    pass
                try:
                    layer.editingStopped.disconnect(self.toggle)
                except:
                    pass                

                # If current layer is editable, the button is enabled
                if layer.isEditable():
                    self.action.setEnabled(True)
                    
                    # If we stop editing, we run toggle function to disable the button
                    layer.editingStopped.connect(self.toggle)
                # Layer is not editable
                else:
                    self.action.setEnabled(False)
                    
                    # In case we start editing, we run toggle function to enable the button
                    layer.editingStarted.connect(self.toggle)
            else:
                self.action.setEnabled(False)
        else:
            self.action.setEnabled(False)

    def deactivate(self):
        self.action.setChecked(False)
        
    def unload(self):
        # Removes item from Plugin Menu, Vector Menu and removes the toolbar icon
        self.iface.removePluginMenu("&Adaplin", self.action)
        self.iface.removePluginMenu("&Adaplin", self.settingsAction)
        self.iface.removeToolBarIcon(self.action)

    def trata_combo(self):
        # ComboBox Selected Raster Layer
        indiceCamada = self.dlg.comboBox.currentIndex()
        camadaSelecionada = self.camadas_raster[indiceCamada]
        
        # Clear ComboBoxs of Bands
        self.dlg.comboBox_2.clear()
        self.dlg.comboBox_3.clear()
        self.dlg.comboBox_4.clear()

        # Get number of raster bands
        numBandas = camadaSelecionada.bandCount()

        # List image bands by numbers and add them to Bands ComboBoxs
        lista_bandas = [str(b) for b in range(1, numBandas+1)]
        self.dlg.comboBox_2.addItems(lista_bandas)
        self.dlg.comboBox_3.addItems(lista_bandas)
        self.dlg.comboBox_4.addItems(lista_bandas)


    def run(self):
        # Unpress the button if it is pressed  
        if not self.action.isChecked(): 
            print self.action.isChecked()
            self.action.setChecked(False)
            return
        
        # On-the-fly SRS must be Projected     
        mapCanvasSrs = self.iface.mapCanvas().mapRenderer().destinationCrs()
        if mapCanvasSrs.geographicFlag():
            QMessageBox.information(self.iface.mainWindow(), 'Error', '<h2> Please choose an On-the-Fly Projected Coordinate System</h2>')
            return
        
        
        # Clear ComboBox of Raster Selection. 
        # This command generate a bug sometimes (for example, when using the plugin with a raster, removing this raster and adding it again) 
        # when trying to clear the comboBox when it is triggered with trata_combo
        # Disconnect and connect the signal is possible but not elegant
        self.dlg.comboBox.clear()
        
        
        
        # List rasters of Legend Interface
        self.camadas_raster = []
        camadas = self.iface.legendInterface().layers()
        
        for camada in camadas:
            if camada.type() == QgsMapLayer.RasterLayer:
                self.camadas_raster.append(camada)
                self.dlg.comboBox.addItem(camada.name())
                
        # Error in case there are no raster layers in the Legend Interface
        if not self.camadas_raster:
            QMessageBox.information(self.iface.mainWindow(), 'Error', '<h2>There are no raster layers in the Legend Interace</h2>')
            return
        
        
        # Finish the dialog box and run the dialog event loop
        self.dlg.show()
        result = self.dlg.exec_()
                
        # See if OK was pressed
        if result:
            # Get Raster Selected from ComboBox
            indiceCamada = self.dlg.comboBox.currentIndex()
            camadaSelecionada = self.camadas_raster[indiceCamada]
                    

            
            # Get Bands selected for this Raster
            numBandas = camadaSelecionada.bandCount()
            lista_bandas = [str(b) for b in range(1, numBandas+1)]
            
            indiceCombo2 = self.dlg.comboBox_2.currentIndex()
            indiceCombo3 = self.dlg.comboBox_3.currentIndex()
            indiceCombo4 = self.dlg.comboBox_4.currentIndex()
            
            bandas_selecao = (lista_bandas[indiceCombo2], lista_bandas[indiceCombo3], lista_bandas[indiceCombo4])
                        
            # Activate our tool if OK is pressed
            self.adaplin = Adaplin(self.iface, camadaSelecionada, bandas_selecao)

            mc = self.canvas
            layer = mc.currentLayer()
      
            mc.setMapTool(self.adaplin)
            self.action.setChecked(True)
        
        else:
            self.action.setChecked(False)
     
    def openSettings(self):
        # Default settings to reload
        def valoresPadrao():
            self.settingsDialog.doubleSpinBox.setValue(DEFAULT_ESPACAMENTO)
            self.settingsDialog.spinBox.setValue(DEFAULT_QPONTOS)
            
        
        # Connect button to function that reload default values
        self.settingsDialog.pushButton.clicked.connect(valoresPadrao)
        self.settingsDialog.show()
        result = self.settingsDialog.exec_()
        
        # If OK is pressed we update the settings
        if result:
            QSettings().setValue(SETTINGS_NAME + "/qpontos", self.settingsDialog.spinBox.value())
            QSettings().setValue(SETTINGS_NAME + "/espacamento", self.settingsDialog.doubleSpinBox.value())

        # Disconnect signal connected previously 
        self.settingsDialog.pushButton.clicked.disconnect(valoresPadrao)
            
