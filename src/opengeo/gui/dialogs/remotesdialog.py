from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class RemotesDialog(QtGui.QDialog):
    def __init__(self, repo):        
        QtGui.QDialog.__init__(self)
        self.repo = repo                
        self.remotes = repo.remotes()        
        self.setupUi()        

    def setupUi(self):
        self.resize(500, 350)
        self.setWindowTitle("Remotes manager")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setMargin(0)
        self.buttonBox = QtGui.QDialogButtonBox()
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Close)
        self.table = QtGui.QTableWidget()                
        self.table.verticalHeader().setVisible(False)
        self.addRowButton = QtGui.QPushButton()
        self.addRowButton.setText("Add remote")
        self.removeRowButton = QtGui.QPushButton()
        self.removeRowButton.setText("Remove remote")
        self.buttonBox.addButton(self.addRowButton, QtGui.QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.removeRowButton, QtGui.QDialogButtonBox.ActionRole)
        self.setTableContent()
        self.horizontalLayout.addWidget(self.table)
        self.horizontalLayout.addWidget(self.buttonBox)
        self.setLayout(self.horizontalLayout)        
        QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), self.closePressed)
        QObject.connect(self.addRowButton, QtCore.SIGNAL("clicked()"), self.addRow)
        QObject.connect(self.removeRowButton, QtCore.SIGNAL("clicked()"), self.removeRow)
        QtCore.QMetaObject.connectSlotsByName(self)

    def setTableContent(self):
        self.table.clear()
        self.table.setColumnCount(2)        
        self.table.setColumnWidth(0,200)
        self.table.setColumnWidth(1,200)
        self.table.setHorizontalHeaderLabels(["Name", "URL"])        
        self.table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.table.setRowCount(len(self.remotes))                    
        for i in xrange(len(self.remotes)):
            name, url = self.remotes[i]
            self.table.setRowHeight(i,22)                        
            self.table.setItem(i,0,QtGui.QTableWidgetItem(name, 0))
            widget = QLineEdit(url)
            widget.editingFinished.connect(lambda: self.updateRemote(i, name, widget))   
            self.table.setCellWidget(i, 1, widget)

    def updateRemote(self, idx, name, widget):
        url = widget.text().strip()
        if self.remotes[idx][1] != url:            
            self.repo.addremote(name, url)
        
    def closePressed(self):
        self.close()

    def removeRow(self):
        idx = self.table.currentRow()
        try:
            name = self.remotes[idx][0]
        except:
            return
        self.repo.removeremote(name)
        del self.remotes[idx]
        self.setTableContent()

    def addRow(self):
        dlg = NewRemoteDialog()
        dlg.exec_()
        if dlg.name:
            self.repo.addremote(dlg.name, dlg.url)
            self.remotes.append((dlg.name, dlg.url)) 
            self.setTableContent()


class NewRemoteDialog(QtGui.QDialog):
    
    def __init__(self, parent = None):
        super(NewRemoteDialog, self).__init__(parent)
        self.name = None
        self.url = None
        self.initGui()        
        
    def initGui(self):                         
        self.setWindowTitle('New remote')
        layout = QtGui.QVBoxLayout()                                
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Close)        
                
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)        
        nameLabel = QtGui.QLabel('Name')
        self.nameBox = QtGui.QLineEdit()        
        horizontalLayout.addWidget(nameLabel)
        horizontalLayout.addWidget(self.nameBox)
        layout.addLayout(horizontalLayout)
        
        horizontalLayout = QtGui.QHBoxLayout()
        horizontalLayout.setSpacing(30)
        horizontalLayout.setMargin(0)        
        urlLabel = QtGui.QLabel('URL')
        self.urlBox = QtGui.QLineEdit()        
        horizontalLayout.addWidget(urlLabel)
        horizontalLayout.addWidget(self.urlBox)
        layout.addLayout(horizontalLayout)               
        
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.connect(buttonBox, QtCore.SIGNAL("accepted()"), self.okPressed)
        self.connect(buttonBox, QtCore.SIGNAL("rejected()"), self.cancelPressed)
        
        self.resize(400,200)            
    
    def okPressed(self):
        self.name = unicode(self.nameBox.text())
        self.url = unicode(self.urlBox.text()) 
        self.close()

    def cancelPressed(self):
        self.name = None
        self.url = None
        self.close()              