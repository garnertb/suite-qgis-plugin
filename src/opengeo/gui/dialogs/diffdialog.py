from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from geogitref import RefPanel

class DiffDialog(QtGui.QDialog):
    def __init__(self, repo, refa = None, refb = None):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.repo = repo
        self.refa = refa
        self.refb = refb
        self.setupUi()
        if refa is not None and refb is not None:
            self.computeDiffs()

    def setupUi(self):
        self.resize(800, 600)
        self.setWindowTitle("Diff")
        layout = QVBoxLayout()                    
        
        horizontalLayout = QHBoxLayout()
        horizontalLayout.setSpacing(20)
        self.refaPanel = RefPanel(self.repo, self.refa)
        self.refbPanel = RefPanel(self.repo, self.refb)
        computeButton = QtGui.QPushButton()
        computeButton.setText("Compute diffs")
        computeButton.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)        
        QObject.connect(computeButton, QtCore.SIGNAL("clicked()"), self.computeDiffs)
        horizontalLayout.addWidget(self.refaPanel)
        horizontalLayout.addWidget(self.refbPanel)
        horizontalLayout.addWidget(computeButton)
        
        self.table = QtGui.QTableWidget()
        self.table.setColumnCount(2)        
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.setHorizontalHeaderLabels(["Path", "Status"])
        self.table.horizontalHeader().setMinimumSectionSize(150)  
        self.table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)                    
        closeButton = QtGui.QPushButton()
        closeButton.setText("Close")
        closeButton.setMaximumWidth(60)
        QObject.connect(closeButton, QtCore.SIGNAL("clicked()"), self.closeButtonPressed)
        layout.addLayout(horizontalLayout)
        layout.addWidget(self.table)
        layout.addWidget(closeButton)
        self.setLayout(layout)
        QtCore.QMetaObject.connectSlotsByName(self)
    
    def computeDiffs(self):
        refa = self.refaPanel.getRef()
        refb = self.refbPanel.getRef()
        diffset = self.repo.diff(refa, refb)
        self.table.clear()
        self.table.setRowCount(len(diffset))
        self.table.setHorizontalHeaderLabels(["Path", "Status"])
        self.table.horizontalHeader().setMinimumSectionSize(150)            
        for i, diff in enumerate(diffset):
            self.table.setItem(i, 0, QtGui. QTableWidgetItem(diff.path));
            self.table.setItem(i, 1, QtGui. QTableWidgetItem(diff.type()));                
        self.table.horizontalHeader().setStretchLastSection(True) 
        self.table.resizeRowsToContents()

    def closeButtonPressed(self):
        self.close()
        
