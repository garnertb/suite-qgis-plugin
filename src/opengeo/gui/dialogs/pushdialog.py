from PyQt4 import QtGui

class PushDialog(QtGui.QDialog):
    
    def __init__(self, repo, parent = None):
        super(PushDialog, self).__init__(parent)
        self.repo = repo
        self.remote = None
        self.refspec = None
        self.ok = False
        self.initGui()        
        
    def initGui(self):                                 
        self.setWindowTitle('Push')
        layout = QtGui.QVBoxLayout()                                             
                
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)        
        remoteLabel = QtGui.QLabel('Remote')
        self.remoteBox = QtGui.QComboBox()        
        remotes = self.repo.remotes()
        remoteNames = [r[0] for r in remotes]
        self.remoteBox.addItems(remoteNames) 
        self.remoteBox.setEditable(True)       
        horizontalLayout.addWidget(remoteLabel)
        horizontalLayout.addWidget(self.remoteBox)
        layout.addLayout(horizontalLayout)
        
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)        
        refspecLabel = QtGui.QLabel('Refspec')
        self.refspecBox = QtGui.QLineEdit()   
        self.refspecBox.setText(self.repo.head())     
        horizontalLayout.addWidget(refspecLabel)
        horizontalLayout.addWidget(self.refspecBox)
        layout.addLayout(horizontalLayout)
        
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)        
        refspecLabel = QtGui.QLabel('Refspec')
        self.allCheck = QtGui.QCheckBox("All branches")                
        horizontalLayout.addWidget(self.allCheck)
        self.allCheck.clicked.connect(self.allClicked)
        layout.addLayout(horizontalLayout)
        
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Close)               
        layout.addWidget(buttonBox)
        self.setLayout(layout)
           
        buttonBox.accepted.connect(self.okPressed)
        buttonBox.rejected.connect(self.cancelPressed)
        
        self.resize(400,200)

    def allClicked(self):
        self.refspecBox.setEnabled(not self.allCheck.isChecked())
    
    def okPressed(self):
        self.remote = unicode(self.remoteBox.currentText())
        self.refspec = unicode(self.refspecBox.text())
        self.all = self.allCheck.isChecked() 
        self.ok = True
        self.close()

    def cancelPressed(self):
        self.remote = None
        self.refspec = None
        self.ok = False
        self.close()  