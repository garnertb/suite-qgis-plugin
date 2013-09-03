from PyQt4 import QtGui, QtCore

class RefWidget(QtGui.QWidget):
    
    def __init__(self, repo, parent = None):
        super(RefWidget, self).__init__()
        self.repo = repo
        self.initGui()

    def initGui(self):                    
        verticalLayout = QtGui.QVBoxLayout()
        verticalLayout.setSpacing(2)
        verticalLayout.setMargin(0)
        
        verticalLayout2 = QtGui.QVBoxLayout()
        verticalLayout2.setSpacing(2)
        verticalLayout2.setMargin(15)
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)        
        self.branchRadio = QtGui.QRadioButton('Branch', self)        
        self.branchRadio.toggled.connect(self.branchRadioClicked)        
        horizontalLayout.addWidget(self.branchRadio)
        self.comboBranch = QtGui.QComboBox()
        for branch in self.repo.branches():
            self.comboBranch.addItem(branch.ref)
        horizontalLayout.addWidget(self.comboBranch)        
        verticalLayout2.addLayout(horizontalLayout)
        
        horizontalLayout2 = QtGui.QHBoxLayout()
        horizontalLayout2.setSpacing(30)
        horizontalLayout2.setMargin(0)
        self.tagRadio = QtGui.QRadioButton('Tag', self)
        self.tagRadio.toggled.connect(self.tagRadioClicked)
        horizontalLayout2.addWidget(self.tagRadio)
        self.comboTag = QtGui.QComboBox()
        for tag in self.repo.tags():
            self.comboTag.addItem(tag.ref)
        horizontalLayout2.addWidget(self.comboTag)
        verticalLayout2.addLayout(horizontalLayout2)
        
        horizontalLayout3 = QtGui.QHBoxLayout()
        horizontalLayout3.setSpacing(30)
        horizontalLayout3.setMargin(0)
        self.commitRadio = QtGui.QRadioButton('Commit', self)
        self.commitRadio.toggled.connect(self.commitRadioClicked)   
        horizontalLayout3.addWidget(self.commitRadio)
        self.commitBox = QtGui.QLineEdit()        
        horizontalLayout3.addWidget(self.commitBox)
        verticalLayout2.addLayout(horizontalLayout3)
        groupBox = QtGui.QGroupBox("Reference")
        groupBox.setLayout(verticalLayout2)
        
        verticalLayout.addWidget(groupBox)
        self.setLayout(verticalLayout)
        
        self.branchRadio.setChecked(True)
            
    def commitRadioClicked(self):
        self.comboBranch.setEnabled(False)
        self.comboTag.setEnabled(False)
        self.commitBox.setEnabled(True)
        
    def tagRadioClicked(self):
        self.comboBranch.setEnabled(False)
        self.commitBox.setEnabled(False)
        self.comboTag.setEnabled(True)
        
    def branchRadioClicked(self):
        self.commitBox.setEnabled(False)
        self.comboTag.setEnabled(False)
        self.comboBranch.setEnabled(True)        
          
    def getref(self):
        if self.branchRadio.isChecked():
            return str(self.comboBranch.currentText())
        elif self.branchRadio.isChecked():
            return str(self.comboTag.currentText())
        else:
            return str(self.commitBox.text())
    
    def setref(self, ref):
        if ref is not None:
            self.commitRadio.setChecked(True)
            self.commitBox.setText(ref)
        
class RefDialog(QtGui.QDialog):
    
    def __init__(self, repo, parent = None):
        super(RefDialog, self).__init__()
        self.repo = repo
        self.ref = None
        self.initGui()

        
    def initGui(self):                         
        layout = QtGui.QVBoxLayout()                                
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Close)
        self.refwidget = RefWidget(self.repo)
        layout.addWidget(self.refwidget)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.connect(buttonBox, QtCore.SIGNAL("accepted()"), self.okPressed)
        self.connect(buttonBox, QtCore.SIGNAL("rejected()"), self.cancelPressed)
        
        self.resize(400,180)
        self.setWindowTitle("Reference")
        
    def getref(self):
        return self.ref        

    def okPressed(self):
        self.ref = self.refwidget.getref()
        self.close()

    def cancelPressed(self):
        self.ref = None
        self.close()        
        
class RefPanel(QtGui.QWidget):

    def __init__(self, repo, ref = None):
        super(RefPanel, self).__init__(None)
        self.repo = repo        
        self.horizontalLayout = QtGui.QHBoxLayout(self)
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setMargin(0)
        self.text = QtGui.QLineEdit()        
        if ref is not None:
            self.text.setText(ref)
        self.text.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self.horizontalLayout.addWidget(self.text)
        self.pushButton = QtGui.QPushButton()
        self.pushButton.setText("...")    
        self.pushButton.clicked.connect(self.showSelectionDialog)
        self.horizontalLayout.addWidget(self.pushButton)
        self.setLayout(self.horizontalLayout)        

    def showSelectionDialog(self):
        dialog = RefDialog(self.repo, self)
        dialog.exec_()
        ref = dialog.getref() 
        if ref:
            self.setRef(ref)

    def setRef(self, ref):        
        self.text.setText(str(ref))

    def getRef(self):
        return str(self.text.text())
