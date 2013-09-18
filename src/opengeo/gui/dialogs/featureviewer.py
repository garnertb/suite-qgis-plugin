from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

class FeatureViewer(QtGui.QDialog):
    def __init__(self, feature):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.feature = feature        
        self.setupUi()

    def setupUi(self):
        self.resize(800,600)
        self.setWindowTitle("Feature viewer")       
        layout = QVBoxLayout()        
        splitter = QtGui.QSplitter(self)        
        splitter.setOrientation(QtCore.Qt.Vertical)        
        self.table = QtGui.QTableWidget(splitter)
        self.table.setColumnCount(2)        
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.setHorizontalHeaderLabels(["Attribute", "Value"])                    
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection);
        self.table.selectionModel().selectionChanged.connect(self.selectionChanged)          
        attributes = self.feature.attributes()
        self.table.setRowCount(len(attributes))
        for idx, attribute in enumerate(attributes):            
            self.table.setItem(idx, 0, QtGui.QTableWidgetItem(attribute[0]));            
            self.table.setItem(idx, 1, QtGui.QTableWidgetItem(attribute[1]));                                                            
        self.table.resizeRowsToContents()
        self.table.horizontalHeader().setMinimumSectionSize(250)        
        self.table.horizontalHeader().setStretchLastSection(True) 
        
        verticalLayout = QVBoxLayout()
        self.tipLabel = QtGui.QLabel("Click on a geometry attribute to render it") 
        verticalLayout.addWidget(self.tipLabel)  

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
          
        self.geom = None
        self.setMap()
            
        closeButton = QtGui.QPushButton()
        closeButton.setText("Close")
        closeButton.setMaximumWidth(60)
        QObject.connect(closeButton, QtCore.SIGNAL("clicked()"), self.closeButtonPressed)
        
        layout.addWidget(splitter)
        layout.addWidget(closeButton)
        self.setLayout(layout)
        QtCore.QMetaObject.connectSlotsByName(self)    
    
    def setMap(self):
        types = ["Point", "LineString", "Polygon"]       
        layer = None
        if self.geom is not None:
            type = types[int(self.geom.type())]            
            layer = QgsVectorLayer(type, "layer", "memory")
            pr = layer.dataProvider()    
            feat = QgsFeature()
            feat.setGeometry(self.geom)
            pr.addFeatures([feat])
               
            layer.updateExtents()         
            self.oldLayerId = layer.id()                        
            symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())
            symbol.setColor(Qt.green)
            symbol.setAlpha(0.5)
            layer.setRendererV2(QgsSingleSymbolRendererV2(symbol))
        
        if layer is not None:            
            self.canvas.setRenderFlag(False)                                    
            self.canvas.setLayerSet([QgsMapCanvasLayer(layer)])
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            self.canvas.setExtent(layer.extent())
            self.canvas.setRenderFlag(True)
        else:
            self.canvas.setLayerSet([])
   
        self.tipLabel.setVisible(self.geom is None)          
                    
        
    def selectionChanged(self):
        idx = self.table.currentRow()        
        try:
            value = self.feature.attributes()[idx]
            self.geom = QgsGeometry.fromWkt(value[1])            
        except Exception, e:
            print e          
            self.geom = None            
            
        self.setMap()
        
    def closeButtonPressed(self):
        self.close()
        
