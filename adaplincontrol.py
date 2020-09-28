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
import sys
import os

# Import the PyQt and the QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import qgis.utils
from qgis.core.contextmanagers import qgisapp

# Initialize Qt resources from file resources.py
import resources

# Import own classes and tools
from adaplin import Adaplin

# Import code for settings
from settings_dialog import SettingsDialog
from utils import *

from compositeControl import compositeControl
from settingsControl import settingsControl

import logging

logging.info('test :D')

class AdaplinControl():
    
    def __init__(self, iface):

    	logging.info('AdaplinControl:__init__')
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        
        # Create settings dialog
        self.settingsDialog = SettingsDialog()

        self.disconnection = None #**#

    def initGui(self):

    	logging.info('AdaplinControl:initGui')

        mc = self.canvas
        layer = mc.currentLayer()

        # Create action for the plugin icon and the plugin menu
        #self.action = QAction(QIcon(":/plugins/AdaplinTool/AdaplinIcon.png"), "AdapLin", self.iface.mainWindow())

        path = os.path.dirname(os.path.abspath(__file__))

        self.action = QAction(QIcon(path + "/AdaplinIcon.png"), "AdapLin", self.iface.mainWindow())
        
        # Button starts disabled and unchecked
        self.action.setEnabled(False)
        self.action.setCheckable(True)
        self.action.setChecked(False)

        # Add Settings to the [Vector] Menu 
        self.settingsAction = QAction(QIcon(path + "/SettingsIcon.png"), "Settings", self.iface.mainWindow())
        #self.iface.addPluginToVectorMenu("&Adaplin Settings", self.settingsAction)
        self.iface.addPluginToMenu("&AdapLin", self.settingsAction)
        self.settingsAction.triggered.connect(self.openSettings)

        # Add the plugin to Plugin Menu and the Plugin Icon to the Toolbar
        self.iface.addPluginToMenu("&AdapLin", self.action)
        self.iface.addToolBarIcon(self.action)
      
        # Connect signals for button behaviour (map layer change, run the tool and change of QGIS map tool set)
        self.iface.currentLayerChanged['QgsMapLayer*'].connect(self.toggle)
        self.action.triggered.connect(self.run)
        QObject.connect(mc, SIGNAL("mapToolSet(QgsMapTool*)"), self.deactivate)

    def toggle(self):

    	logging.info('AdaplinControl:toggle')

        # Get current layer
        mc = self.canvas
        layer = mc.currentLayer()

        if self.disconnection:
            self.disconnection()
            self.disconnection = None
        #print "Adaplin layer = ", layer.name()
        
        # In case the current layer is None we do nothing
        if layer is None:
            return
        
        #print 'raster type = ', layer.type()
        #print 'e vector = ', layer.type() == layer.VectorLayer
        
        # This is to decide when the plugin button is enabled or disabled
        # The layer must be a Vector Layer
        if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QGis.Line:
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
                self.action.setChecked(False)
                
                # If we stop editing, we run toggle function to disable the button
                layer.editingStopped.connect(self.toggle)
                
            # Layer is not editable
            else:
                self.action.setEnabled(False)
                self.canvas.unsetCursor()
                
                # In case we start editing, we run toggle function to enable the button
                layer.editingStarted.connect(self.toggle)

        else:

        	self.action.setEnabled(False)

    def deactivate(self):

    	logging.info('AdaplinControl:deactivate')

        self.action.setChecked(False)
        
    def unload(self):

    	logging.info('AdaplinControl:unload')

        # Removes item from Plugin Menu, Vector Menu and removes the toolbar icon
        self.iface.removePluginMenu("&Adaplin", self.action)
        self.iface.removePluginMenu("&Adaplin", self.settingsAction)
        self.iface.removeToolBarIcon(self.action)
    
    def run(self):

    	logging.info('AdaplinControl:run')

        # Unpress the button if it is pressed
        #Changed here so the tool can't be disabled from the button
        if not self.action.isChecked():
            msg = QMessageBox()
            msg.setIcon(4)
            msg.setText("Adaplin is already running.")
            msg.setWindowTitle("Adaplin")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            
            self.action.setEnabled(True)
            self.action.setChecked(True)
            return

##################################################################################################################
        control = compositeControl(self.iface.legendInterface().layers())
        a = control.control()
                
        # Error in case there are no raster layers in the Legend Interface
        if not a:
            QMessageBox.information(self.iface.mainWindow(), 'Error', '<h2>There are no raster layers in the Legend Interface</h2>')
            self.deactivate()
            return

        okPressed = a[0]
        layer = a[1]
        bands = a[2]

        # On-the-fly SRS must be Projected 
        mapCanvasSrs = self.iface.mapCanvas().mapSettings().destinationCrs()
        if mapCanvasSrs.geographicFlag():
            QMessageBox.information(self.iface.mainWindow(), 'Error', '<h2> Please choose an On-the-Fly Projected Coordinate System</h2>')
        
        if okPressed:
            # Activate our tool if OK is pressed
            self.adaplin = Adaplin(self.iface, layer, bands, self.action)

            mc = self.canvas
            
            layer = mc.currentLayer()

            mc.setMapTool(self.adaplin)
            self.action.setChecked(True)
            
        else:
            self.deactivate()
            return

    def openSettings(self):

        control = settingsControl()
        control.control()