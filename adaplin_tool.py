from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import numpy as np
from math import sqrt
import collections

from utils import *

class Adaplin(QgsMapTool):
    def __init__(self, iface, camada_raster, bandas):
        self.camada_raster = camada_raster
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.bandas = bandas
        
        QgsMapTool.__init__(self, self.canvas)
        self.rb = QgsRubberBand(self.canvas,  QGis.Polygon)
        self.type = QGis.Polygon 
        
        # List of points (points) marked by the user, of all the points that will form the line (pontos_interpolados) 
        # and variable to set the manual mode ON or OFF (at start is OFF)
        self.points = [] 
        self.pontos_interpolados = []
        self.mCtrl = False

        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                      "      c None",
                                      ".     c #FF0000",
                                    
                                    
                                      "+     c #FFFFFF",
                                      "                ",
                                      "       +.+      ",
                                      "      ++.++     ",
                                      "     +.....+    ",
                                      "    +.     .+   ",
                                      "   +.   .   .+  ",
                                      "  +.    .    .+ ",
                                      " ++.    .    .++",
                                      " ... ...+... ...",
                                      " ++.    .    .++",
                                      "  +.    .    .+ ",
                                      "   +.   .   .+  ",
                                      "   ++.     .+   ",
                                      "    ++.....+    ",
                                      "      ++.++     ",
                                      "       +.+      "]))       
                                      
    def canvasPressEvent(self, event):
        # Device coordinates of mouse
        x = event.pos().x()
        y = event.pos().y()
        
        # Add the marked point on left click
        if event.button() == Qt.LeftButton:
            startingPoint = QPoint(x,y) 
            
            # Try to snap to current Layer if it is specified in QGIS digitizing options
            snapper = QgsMapCanvasSnapper(self.canvas)
            (retval,result) = snapper.snapToCurrentLayer (startingPoint, QgsSnapper.SnapToVertex)
                 
            if result <> []:
                point = QgsPoint( result[0].snappedVertex )
            else:
                (retval,result) = snapper.snapToBackgroundLayers(startingPoint)
                if result <> []:
                    point = QgsPoint( result[0].snappedVertex )
                else:
                    point = self.canvas.getCoordinateTransform().toMapCoordinates( event.pos().x(), event.pos().y() )
            
            # Append point to list of points marked by the user
            self.points.append(point)
            
            # If tool is in Manual Mode, we just append the point to pontos_interpolados            
            if self.mCtrl:
                self.pontos_interpolados.append(point)
            # If the tool is in Default Mode, we append the new points to pontos_interpolados
            else:
                pontos_recentes = self.interpolacao ( self.points[-2::] )
                self.pontos_interpolados = self.pontos_interpolados + pontos_recentes[1:] 
        
        # On the right click, we create the feature with pontos_interpolados and clear the things for the next feature  
        else:
            if len( self.points ) >= 2:
                self.createFeature(self.pontos_interpolados) 

            self.resetPoints()
            self.resetRubberBand()
            self.canvas.refresh() 

    # Clean lists of points
    def resetPoints(self):
        self.points = []
        self.pontos_interpolados = []
    
    def createFeature(self, pontos_interpolados):
        layer = self.canvas.currentLayer() 
        provider = layer.dataProvider()
        fields = layer.pendingFields()
        f = QgsFeature(fields)
            
        coords = pontos_interpolados
        
        if self.canvas.mapRenderer().hasCrsTransformEnabled() and layer.crs() != self.canvas.mapRenderer().destinationCrs():
            coords_tmp = coords[:]
            coords = []
            for point in coords_tmp:
                transformedPoint = self.canvas.mapRenderer().mapToLayerCoordinates( layer, point )
                coords.append(transformedPoint)
              
        if self.isPolygon == True:
            g = QgsGeometry().fromPolygon([coords])
        else:
            g = QgsGeometry().fromPolyline(coords)
        f.setGeometry(g)
            
        for field in fields.toList():
            ix = fields.indexFromName(field.name())
            f[field.name()] = provider.defaultValue(ix)

        layer.beginEditCommand("Feature added")
        
        settings = QSettings()
        
        disable_attributes = settings.value( "/qgis/digitizing/disable_enter_attribute_values_dialog", False, type=bool)
        if disable_attributes:
            layer.addFeature(f)
            layer.endEditCommand()
        else:
            dlg = self.iface.getFeatureForm(layer, f)
            if QGis.QGIS_VERSION_INT >= 20400: 
                dlg.setIsAddDialog( True ) 
            if dlg.exec_():
                if QGis.QGIS_VERSION_INT < 20400: 
                    layer.addFeature(f)
                layer.endEditCommand()
            else:
                layer.destroyEditCommand()
                
    # This is similar to canvasPressEvent
    def canvasMoveEvent(self,event):
        color = QColor(255,0,0,100)
        self.rb.setColor(color)
        self.rb.setWidth(3)

        x = event.pos().x()
        y = event.pos().y()
        
        startingPoint = QPoint(x,y)
        snapper = QgsMapCanvasSnapper(self.canvas)
            
        (retval,result) = snapper.snapToCurrentLayer (startingPoint, QgsSnapper.SnapToVertex)   
        if result <> []:
            point = QgsPoint( result[0].snappedVertex )
        else:
            (retval,result) = snapper.snapToBackgroundLayers(startingPoint)
            if result <> []:
                point = QgsPoint( result[0].snappedVertex )
            else:
                point = self.canvas.getCoordinateTransform().toMapCoordinates( event.pos().x(), event.pos().y() );
        
        pontos_marcados = list( self.points )
        pontos_interpolados = list( self.pontos_interpolados)
        pontos_marcados.append( point )
        
        if self.mCtrl:
            pontos_interpolados.append(point)
        else:
            #pontos_recentes, grafo, pontos_perpendiculares, result = self.interpolacao ( pontos_marcados[-2::] )
            pontos_recentes = self.interpolacao ( pontos_marcados[-2::] )
            pontos_interpolados = pontos_interpolados + pontos_recentes[1:]
       
        self.setRubberBandPoints(pontos_interpolados)

    def showSettingsWarning(self):
        pass

    def activate(self):
        self.canvas.setCursor(self.cursor)
        
        mc = self.canvas
        layer = mc.currentLayer()
        self.type = layer.geometryType()
        self.isPolygon = False
        if self.type == QGis.Polygon:
            self.isPolygon = True

    def resetRubberBand(self):
        self.rb.reset( self.type )

    def setRubberBandPoints(self,points):
        self.resetRubberBand()
        for point in points:
            update = point is points[-1]
            self.rb.addPoint( point, update )

    # Interpolate 2 points between the segment traced by the user
    def interpolacao(self, points):
        # Here the graph is represented by a list of lists of QgsPoint
        grafo = []                               
        
        npoints = len(points)
        
        # If there is 1 point, we will not interpolate  
        #if npoints == 1: return [QgsPoint(1,1), points[0]], grafo, [], None
        
        if npoints == 1: return [QgsPoint(1,1), points[0]]
        
        # Loop in the points presented in the segment to interpolate (here npoints always will be 2, but this is designed to work even if it is passed a poliline)
        for i in range(0, npoints-1):
            # Try to add the perpendicular lines (formed by QgsPoints) to the segment, in order to do the interpolation
            # If points are out of raster bounds or other exception occurs, we don't interpolate
            try:
                retas_perpendiculares = self.calcula_reta(points[i], points[i+1])
            except:
                #return points, grafo, [], []
                return points
            
            grafo.append([points[i]])
            grafo.extend(retas_perpendiculares)
        
        grafo.append([points[-1]])
        result, p = self.acha_caminho(grafo, points)
        
        #return result, grafo, retas_perpendiculares, result
        return result
    
    # Calculate the points that will be candidates to the result of point interpolation
    def calcula_reta(self, p1, p2):
        # Get, from Adaplin Settings, the number of points that will be above (perpendicular that is counter-clockwise) and under (perpendicular that is clockwise) in each 
        # perpendicular segment to the segment traced by the user
        # The total of points in the perpendicular line will be 2 times pontos_acima_e_abaixo (above and under) plus 1 (that is located on the segment) 
        pontos_acima_e_abaixo = int( QSettings().value(SETTINGS_NAME + "/qpontos", DEFAULT_QPONTOS ))
        
        # Get, from Adaplin Settings, the spacement between the points in the perpendicular to the segment traced by the user 
        resolucao_y = float( QSettings().value(SETTINGS_NAME + "/espacamento", DEFAULT_ESPACAMENTO )) 
        
        # Calculate the unit vector (x and y coordinates)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        
        dist = sqrt(dx*dx + dy*dy)
        
        dx /= dist # x coordinate of the unit vector
        dy /= dist # y coordinate of the unit vector
        
        # Calculate list of x coordinates (coord_x_sobre) and y coordinates (coord_y_sobre) of inserted points on the line
        x_p1 = p1.x()
        x_p2 = p2.x()
        y_p1 = p1.y()
        y_p2 = p2.y()
                
        q = 2 # number of inserted points
        n = 3.0 # number of segments originated from insertion of q points
        
        coord_x_sobre = []
        coord_y_sobre = []

        for i in range(q, 0, -1):
            coord_x_sobre.append((i/(n))*x_p1 + (1. - i/n)*x_p2) 
            coord_y_sobre.append((i/(n))*y_p1 + (1. - i/n)*y_p2) 
        
        
        # Compute retas_perpendiculares list of lists. Each list inside retas_perpendiculares will be made of 
        # QgsPoints that are the possible points to interpolate in that line perpendicular to the user segment 
        retas_perpendiculares = []
        
        for i in range(len(coord_x_sobre)):
            x_acima = [(coord_x_sobre[i] - resolucao_y*j*dy) for j in range(1,pontos_acima_e_abaixo)] # Here we subtract resolucao_y*j*dy because the unit vector perpendicular (counter-clockwise) to the unit vector (dx, dy) is (-dy, dx)
            y_acima = [(coord_y_sobre[i] + resolucao_y*j*dx) for j in range(1,pontos_acima_e_abaixo)]

            x_abaixo = [(coord_x_sobre[i] + resolucao_y*j*dy) for j in range(1,pontos_acima_e_abaixo)]
            y_abaixo = [(coord_y_sobre[i] - resolucao_y*j*dx) for j in range(1,pontos_acima_e_abaixo)]        
        
            lista_de_x = [coord_x_sobre[i]] + x_acima + x_abaixo
            lista_de_y = [coord_y_sobre[i]] + y_acima + y_abaixo
        
            lista_pontos_perpendiculares = [QgsPoint(lista_de_x[j], lista_de_y[j]) for j in range(len(lista_de_x))]

            retas_perpendiculares.append(lista_pontos_perpendiculares)
        
        return retas_perpendiculares
    
    # Property 1: Maximize the rgb average of the poliline 
    def Prop1(self, no1, no2, no3):
        no1_media = self.rgb_media(self.camada_raster, no1)
        no2_media = self.rgb_media(self.camada_raster, no2)
        no3_media = self.rgb_media(self.camada_raster, no3)       
        
        return no1_media*no1_media + no2_media*no2_media + no3_media*no3_media
    
    # Property 2: Minimize the difference between rgb averages of the poliline     
    def Prop2(self, no1, no2, no3):
        no1no2 = self.pointsDist(no1, no2) 
        no2no3 = self.pointsDist(no2, no3) 
        
        nc_no1 = self.rgb_media(self.camada_raster, no1)
        nc_no2 = self.rgb_media(self.camada_raster, no2)
        nc_no3 = self.rgb_media(self.camada_raster, no3)
        
        mediaNo1No2 = (nc_no1 + nc_no2)/2.
        mediaNo2No3 = (nc_no2 + nc_no3)/2.
        
        somatorio_Prop2 = ((nc_no1 - mediaNo1No2)*(nc_no1 - mediaNo1No2) + (nc_no2 - mediaNo1No2)*(nc_no2 - mediaNo1No2)) + ((nc_no2 - mediaNo2No3)*(nc_no2 - mediaNo2No3) + (nc_no3 - mediaNo2No3)*(nc_no3 - mediaNo2No3)) 
        
        return somatorio_Prop2

    # Property 3: Minimize the poliline curvature     
    def Prop3(self, no1, no2, no3):
        no1no2 = self.pointsDist(no1, no2) 
        no2no3 = self.pointsDist(no2, no3) 
        no1no3 = self.pointsDist(no1, no3)
        distTotal = no1no2 + no2no3
        
        cosseno_interno = ( (no1no2*no1no2 + no2no3*no2no3 - no1no3*no1no3) / (2*no1no2*no2no3) ) 
        cosseno_deflexao = -1*cosseno_interno
        
        return (1 + cosseno_deflexao) /no1no2
    
    # Calculate the average of the input bands in the pixel corresponding to the point of interest    
    def rgb_media(self, raster, ponto):
        provedor = raster.dataProvider()        

        # We have to transform the point to the raster projection
        mapCanvasSrs = self.iface.mapCanvas().mapRenderer().destinationCrs()
        rasterSrs = raster.crs()
        srsTransform = QgsCoordinateTransform(mapCanvasSrs, rasterSrs)
        
        ponto_transform = srsTransform.transform(ponto)
        ponto_valor = provedor.identify(ponto_transform, QgsRaster.IdentifyFormatValue).results()
        
        if len(ponto_valor) > 3:
            ponto_media = sum([ponto_valor[i] for i in [int(self.bandas[0]), int(self.bandas[1]), int(self.bandas[2])]])/3.
        else:
            ponto_media = sum([ponto_valor[i] for i in ponto_valor])/float(len(ponto_valor))
        
        return ponto_media        
    
    # This function gives the best path in a graph considering the objective function that takes in consideration the properties Prop1, Prop2 and Prop3 
    def acha_caminho(self, grafo, points):
        def no_maximo(dic):
            for elem in dic:
                if elem == 'MAX':
                    continue
                if dic[elem] == dic['MAX']:
                    return elem
                    
                    
        lista_dic = []
        lista_dic.append({})
        
        no_inicial = grafo[0][0]                                                                                              
        
        for no in grafo[1]:
            lista_dic[0][(no_inicial, no)] = {'MAX': 0} 
        
        for i in range(len(grafo)):
            g = grafo[i]

            try:
                g_k_mais_dois = grafo[i+2]
            except:
                break
        
            g_k_mais_um = grafo[i+1]
            lista_dic.append({})
        
            for j in range(len(g_k_mais_um)):
                for k in range(len(g_k_mais_dois)):
                    no_k_mais_um = g_k_mais_um[j]
                    no_k_mais_dois = g_k_mais_dois[k]
                                        
                    lista_dic[i+1][(no_k_mais_um, no_k_mais_dois)] = {}
                                        
                    for z in range(len(g)):
                        no_atual = g[z] 
                        
                        try:                                            
                            res_parcial = lista_dic[i][(no_atual, no_k_mais_um)]['MAX'] + (self.Prop1(no_atual, no_k_mais_um, no_k_mais_dois) - self.Prop2(no_atual, no_k_mais_um, no_k_mais_dois))*self.Prop3(no_atual, no_k_mais_um, no_k_mais_dois)
                        except:
                            return points, points                             
                        
                        lista_dic[i+1][(no_k_mais_um, no_k_mais_dois)][no_atual] = res_parcial
                                            

                    lista_dic[i+1][(no_k_mais_um, no_k_mais_dois)]['MAX'] = max([lista_dic[i+1][(no_k_mais_um, no_k_mais_dois)][el] for el in lista_dic[i+1][(no_k_mais_um, no_k_mais_dois)]])
                    

        lista_dic_inv = lista_dic[-1:0:-1] 
        prima = lista_dic_inv[0]
        
        ultimos, f_acum, no_escolhido = max([(chave, valor['MAX'], no_maximo(valor)) for chave, valor in prima.iteritems()], key = lambda par_facum: par_facum[1])
        no_anterior, no_posterior = ultimos 
    
        caminho = []
        caminho += (no_posterior, no_anterior, no_escolhido)
    
        for elemento in lista_dic_inv[1::]:
            no_posterior, no_anterior = no_anterior, no_escolhido
            no_escolhido = no_maximo(elemento[(no_anterior, no_posterior)])
            caminho.append(no_escolhido)    
        
        caminho.reverse()
    
        return caminho, points
    
    # Calculate the euclidean distance between 2 points
    def pointsDist(self, a, b):
        dx = a.x()-b.x()
        dy = a.y()-b.y()
        return sqrt( dx*dx + dy*dy )
    
    # Define the Ctrl key to enter manual mode, the Escape key as an option to finish the feature and the Shift key to pan the canvas to the last point added    
    def keyPressEvent(self,  event):
        if event.key() == Qt.Key_Control:
            if self.mCtrl is True:
                self.mCtrl = False
            else:
                self.mCtrl = True
        if event.key() == Qt.Key_Escape:
            self.createFeature(self.pontos_interpolados)
            self.resetPoints()
            self.resetRubberBand()
            self.canvas.refresh()
        if event.key() == Qt.Key_Shift:
            try:
                ultimo_ponto = self.pontos_interpolados[-1]
                self.canvas.setExtent(QgsRectangle(ultimo_ponto, ultimo_ponto))
                self.canvas.refresh()
            except:
                pass
    
    # Define Backspace to delete the last point added    
    def keyReleaseEvent(self,  event):
        if event.key() == Qt.Key_Backspace:
            self.removeLastPoint()            

    def removeLastPoint(self):
        if len(self.points) == 0:
            QMessageBox.information(self.iface.mainWindow(), 'Aviso', 'Nenhum ponto marcado ainda')
        elif len(self.points) == 1:
            self.points.pop()
            self.pontos_interpolados.pop()
        else:
            penultimo_elemento_marcado = self.points[-2]
            self.pontos_interpolados = self.pontos_interpolados[0:self.pontos_interpolados.index(penultimo_elemento_marcado)+1]
            self.points.pop()
            
            


    
            
            
