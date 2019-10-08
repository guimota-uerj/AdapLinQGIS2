# AdapLin 
### Repository for the development of AdapLin plugin for QGIS 

![Project Icon](AdapliniconSmall.png )

The AdapLin Tool is an adaptive, interactive, assisting tool for roads vector mapping. It is based on dynamic programming and was developed as a plugin for the QGIS software. AdapLin is intended to optimize the vector mapping of roads, based on features present on a georeferenced image. In terms of workflow, after setting up a project and starting AdapLin on QGIS software, the operator clicks on the first vertex of the focused road on the QGIS map canvas. Such vertex is a reference coordinate for the process that follows. Considering the cursor position and the underlain image, AdapLin Tool shows a preview for such road segment. That preview encompasses the reference vertex, two vertices automatically suggested by a dynamic programming procedure, followed by the current cursor position. The preview is adaptive once it changes in real time according to cursor position. If the operator clicks on it, preview points are incorporated to the road polyline into the shapefile buffer. Then, the last vertex measured by the user turns to be the next reference vertex for the preview. During AdapLin operation, the optimization process is carried out by a dynamic programming approach based on a graph. Shape and spectral features, extracted from the image, are combined to choose the minimal cost path. 

AdapLin Tool was created for the master’s degree dissertation of Marcel Emanuelli Rotunno (2017) submitted to the Post-Graduation Program on Computational Sciences at Rio de Janeiro State University (UERJ). That research aimed at attending demands of road cartographic production of the Brazilian Institute of Geography and Statistics (IBGE). This software is available under GNU/GPL licence to anyone who desires improving roads mapping experience.
