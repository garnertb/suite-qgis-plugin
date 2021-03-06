from PyQt4 import QtGui, QtCore       
from opengeo.qgis import layers


class ImportDialog(QtGui.QDialog):
    
    def __init__(self, showLayerSelector = True, parent = None):
        super(ImportDialog, self).__init__(parent)
        self.showLayerSelector = showLayerSelector
        self.ok = False
        self.dest = None
        self.layer = None
        self.add = False
        self.initGui()
                
                
    def initGui(self):    
        self.setWindowTitle("Import")                     
        layout = QtGui.QVBoxLayout()                                
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(20)
        self.verticalLayout.setMargin(20)
        
        
        if self.showLayerSelector:
            horizontalLayout = QtGui.QHBoxLayout()
            horizontalLayout.setSpacing(30)
            horizontalLayout.setMargin(0)        
            layerLabel = QtGui.QLabel('Layer')
            self.layerBox = QtGui.QComboBox()        
            self.layerBox.addItems([layer.name() for layer in layers.getVectorLayers()])        
            horizontalLayout.addWidget(layerLabel)
            horizontalLayout.addWidget(self.layerBox)
            layout.addLayout(horizontalLayout)            
            
        horizontalLayout2 = QtGui.QHBoxLayout()
        horizontalLayout2.setSpacing(10)
        horizontalLayout2.setMargin(0)        
        nameLabel = QtGui.QLabel('Destination tree')        
        self.destBox = QtGui.QLineEdit()
        self.destBox.setPlaceholderText("[Leave empty to use default destination]")
        horizontalLayout2.addWidget(nameLabel)
        horizontalLayout2.addWidget(self.destBox)
        self.addCheck = QtGui.QCheckBox('Add')  
                
        
        layout.addLayout(horizontalLayout2)              
        layout.addWidget(self.addCheck)
        spacer = QtGui.QSpacerItem(20,40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        layout.addItem(spacer)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.connect(buttonBox, QtCore.SIGNAL("accepted()"), self.okPressed)
        self.connect(buttonBox, QtCore.SIGNAL("rejected()"), self.cancelPressed)
        
        self.resize(500,200)
            
              
    def okPressed(self):
        if self.showLayerSelector:
            self.layer = layers.resolveLayer(self.layerBox.currentText())
        self.add = self.addCheck.isChecked()
        self.dest = unicode(self.destBox.text())
        if self.dest == "":
            self.dest = None
        self.ok = True
        self.close()

    def cancelPressed(self):
        self.ok = False
        self.layer = None
        self.close()  
        


class ImportAndCommitDialog(QtGui.QDialog):
    
    def __init__(self, showLayerSelector = True, parent = None):
        super(ImportAndCommitDialog, self).__init__(parent)                
        self.showLayerSelector = showLayerSelector
        self.layer = None
        self.message = None        
        self.initGui()        
        
    def initGui(self):                         
        layout = QtGui.QVBoxLayout()                                
              
        self.setWindowTitle('Import and commit layer')
         
        if self.showLayerSelector:
            horizontalLayout = QtGui.QHBoxLayout()
            horizontalLayout.setSpacing(30)
            horizontalLayout.setMargin(0)        
            layerLabel = QtGui.QLabel('Layer')
            self.layerBox = QtGui.QComboBox()        
            self.layerBox.addItems([layer.name() for layer in layers.getVectorLayers()])        
            horizontalLayout.addWidget(layerLabel)
            horizontalLayout.addWidget(self.layerBox)
            layout.addLayout(horizontalLayout)
                           
        commitLabel = QtGui.QLabel('Commit message')
        layout.addWidget(commitLabel)
        self.text = QtGui.QPlainTextEdit()
        self.text.textChanged.connect(self.textHasChanged)
        layout.addWidget(self.text)
        
        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Close) 
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(False) 
        layout.addWidget(self.buttonBox)
        
        self.setLayout(layout)

        self.buttonBox.accepted.connect(self.okPressed)
        self.buttonBox.rejected.connect(self.cancelPressed)
        
        self.resize(400,200) 

    def textHasChanged(self):
        self.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(str(self.text.toPlainText()) != "")
            
    def okPressed(self):                        
        self.message = self.text.toPlainText()
        if self.showLayerSelector:
            self.layer = layers.resolveLayer(self.layerBox.currentText())        
        self.close()

    def cancelPressed(self):
        self.layer = None  
        self.message = None              
        self.close()           