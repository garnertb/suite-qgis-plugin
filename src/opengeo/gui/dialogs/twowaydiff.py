from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

class TwoWayDiffViewerDialog(QtGui.QDialog):
    def __init__(self, diffdata):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.diffdata = diffdata        
        self.setupUi()

    def setupUi(self):
        self.resize(800,600)
        self.setWindowTitle("Feature diff viewer")
        self.showoldgeom = True
        self.shownewgeom = True        
        self.oldgeom = None
        self.newgeom = None
        self.oldLayerId = None
        self.newLayerId = None
        layout = QVBoxLayout()        
        splitter = QtGui.QSplitter(self)        
        splitter.setOrientation(QtCore.Qt.Vertical)        
        self.table = QtGui.QTableWidget(splitter)
        self.table.setColumnCount(3)        
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.setHorizontalHeaderLabels(["Attribute", "Old value", "New value"])
        self.table.setRowCount(len(self.diffdata))                
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.selectionModel().selectionChanged.connect(self.selectionChanged)  
        idx = 0;
        for name in self.diffdata:
            values = self.diffdata[name]
            self.table.setItem(idx, 0, QtGui.QTableWidgetItem(name));
            oldValue = values[0] if values[0] is not None else ""
            newValue = values[1] if values[1] is not None else ""
            self.table.setItem(idx, 1, QtGui.QTableWidgetItem(oldValue));            
            self.table.setItem(idx, 2, QtGui.QTableWidgetItem(newValue));
            color = None
            if values[0] is None:
                color = QtCore.Qt.green
            elif values[1] is None:
                color = QtCore.Qt.red
            elif values[0] != values[1]:
                color = QtCore.Qt.yellow
            if color is not None:
                for i in range(3):
                    self.table.item(idx, i).setBackgroundColor(color);            
            idx += 1
        self.table.resizeRowsToContents()
        self.table.horizontalHeader().setMinimumSectionSize(250)        
        self.table.horizontalHeader().setStretchLastSection(True) 
        
        verticalLayout = QVBoxLayout()
        horizontalLayout = QHBoxLayout()
        self.showOldLabel = QtGui.QLabel()
        self.connect(self.showOldLabel, QtCore.SIGNAL("linkActivated(QString)"), self.toggleOldGeometry)
        self.showNewLabel = QtGui.QLabel()
        self.connect(self.showNewLabel, QtCore.SIGNAL("linkActivated(QString)"), self.toggleNewGeometry)
        self.tipLabel = QtGui.QLabel("Click on a geometry attribute to show differences") 
        horizontalLayout.addWidget(self.showOldLabel)
        horizontalLayout.addWidget(self.showNewLabel)
        horizontalLayout.addWidget(self.tipLabel)                                          
        verticalLayout.addLayout(horizontalLayout)  

        self.canvas = QgsMapCanvas()        
        self.canvas.setCanvasColor(Qt.white)    
        settings = QSettings()
        self.canvas.enableAntiAliasing(settings.value( "/qgis/enable_anti_aliasing", False, type=bool))
        self.canvas.useImageToRender(settings.value( "/qgis/use_qimage_to_render", False, type=bool))
        action = settings.value("/qgis/wheel_action", 0, type=float)
        zoomFactor = settings.value("/qgis/zoom_factor", 2, type=float)
        self.canvas.setWheelAction(QgsMapCanvas.WheelAction(action), zoomFactor)   
              
        verticalLayout.addWidget(self.canvas)
        container = QtGui.QWidget()
        container.setLayout(verticalLayout)
        splitter.addWidget(container)   
          
        self.setMap()
            
        closeButton = QtGui.QPushButton()
        closeButton.setText("Close")
        closeButton.setMaximumWidth(60)
        QObject.connect(closeButton, QtCore.SIGNAL("clicked()"), self.closeButtonPressed)
        
        layout.addWidget(splitter)
        layout.addWidget(closeButton)
        self.setLayout(layout)
        QtCore.QMetaObject.connectSlotsByName(self)
    
    def toggleOldGeometry(self):
        self.showoldgeom = not self.showoldgeom
        self.setMap()
        
    def toggleNewGeometry(self):
        self.shownewgeom = not self.shownewgeom
        self.setMap()        
    
    def setMap(self):
        types = ["Point", "LineString", "Polygon"]
        if self.oldLayerId:
            QgsMapLayerRegistry.instance().removeMapLayer(self.oldLayerId)
            self.oldLayerId = None            
        if self.newLayerId:
            QgsMapLayerRegistry.instance().removeMapLayer(self.newLayerId)
            self.newLayerId = None          
        layers = []
        if self.oldgeom is not None and self.showoldgeom:
            type = types[int(self.oldgeom.type())]            
            oldLayer = QgsVectorLayer(type, "Old", "memory")
            pr = oldLayer.dataProvider()    
            feat = QgsFeature()
            feat.setGeometry(self.oldgeom)
            pr.addFeatures([feat])
            layers.append(oldLayer)    
            oldLayer.updateExtents()         
            self.oldLayerId = oldLayer.id()                        
            symbol = QgsSymbolV2.defaultSymbol(oldLayer.geometryType())
            symbol.setColor(Qt.red)
            symbol.setAlpha(0.5)
            oldLayer.setRendererV2(QgsSingleSymbolRendererV2(symbol))
    
        if self.newgeom is not None and self.shownewgeom: 
            type = types[int(self.newgeom.type())]
            newLayer = QgsVectorLayer(type, "New", "memory")
            pr = newLayer.dataProvider()    
            feat = QgsFeature()
            feat.setGeometry(self.newgeom)
            pr.addFeatures([feat])  
            newLayer.updateExtents()          
            self.newLayerId = newLayer.id()
            layers.append(newLayer)
            symbol = QgsSymbolV2.defaultSymbol(newLayer.geometryType())
            symbol.setColor(Qt.green)
            symbol.setAlpha(0.5)
            newLayer.setRendererV2(QgsSingleSymbolRendererV2(symbol))
        
        if layers:            
            self.canvas.setRenderFlag(False)                                    
            self.canvas.setLayerSet([QgsMapCanvasLayer(lyr) for lyr in layers])
            for layer in layers:
                QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            self.canvas.setExtent(layers[0].extent())
            self.canvas.setRenderFlag(True)
        else:
            self.canvas.setLayerSet([])
   
        

        if self.showoldgeom:
            self.showOldLabel.setText('<qt><a href = "dummy.html"> Hide old geometry </a></qt>')
        else:
            self.showOldLabel.setText('<qt><a href = "dummy.html"> Show old geometry </a></qt>')
        
        if self.shownewgeom:
            self.showNewLabel.setText('<qt><a href = "dummy.html"> Hide new geometry </a></qt>')
        else:
            self.showNewLabel.setText('<qt><a href = "dummy.html"> Show new geometry </a></qt>')
            
        self.showNewLabel.setVisible(self.newgeom is not None)
        self.showOldLabel.setVisible(self.oldgeom is not None)  
        self.tipLabel.setVisible(self.newgeom is None and self.oldgeom is None)          
                    
        
    def selectionChanged(self):
        idx = self.table.currentRow()        
        try:
            name = self.table.item(idx, 0).text()
            self.oldgeom = self.diffdata[name][0]
            self.newgeom = self.diffdata[name][1]
            self.oldgeom = QgsGeometry.fromWkt(self.oldgeom)
            self.newgeom = QgsGeometry.fromWkt(self.newgeom)
            #===================================================================
            # self.oldgeom = shapely.wkb.loads(self.oldgeom)
            # self.newgeom = shapely.wkb.loads(self.newgeom)
            #===================================================================
            self.showoldgeom = True
            self.shownewgeom = True
        except Exception, e:          
            self.oldgeom = None
            self.newgeom = None
            
        self.setMap()
        
    def closeButtonPressed(self):
        self.close()
        
