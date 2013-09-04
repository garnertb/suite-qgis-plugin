from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class TwoWayDiffViewerDialog(QtGui.QDialog):
    def __init__(self, diffdata):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.diffdata = diffdata        
        self.setupUi()

    def setupUi(self):
        self.resize(800,600)
        self.setWindowTitle("Feature diff viewer")
        layout = QVBoxLayout()        
        splitter = QtGui.QSplitter(self)        
        splitter.setOrientation(QtCore.Qt.Vertical)        
        table = QtGui.QTableWidget(splitter)
        table.setColumnCount(3)        
        table.setShowGrid(False)
        table.verticalHeader().hide()
        table.setHorizontalHeaderLabels(["Attribute", "Old value", "New value"])
        table.setRowCount(len(self.diffdata))                
        table.setSelectionMode(QtGui.QAbstractItemView.NoSelection)  
        idx = 0;
        for name in self.diffdata:
            values = self.diffdata[name]
            table.setItem(idx, 0, QtGui.QTableWidgetItem(name));
            oldValue = values[0] if values[0] is not None else ""
            newValue = values[1] if values[1] is not None else ""
            table.setItem(idx, 1, QtGui.QTableWidgetItem(oldValue));            
            table.setItem(idx, 2, QtGui.QTableWidgetItem(newValue));
            color = None
            if values[0] is None:
                color = QtCore.Qt.green
            elif values[1] is None:
                color = QtCore.Qt.red
            elif values[0] != values[1]:
                color = QtCore.Qt.yellow
            if color is not None:
                for i in range(3):
                    table.item(idx, i).setBackgroundColor(color);            
            idx += 1
        table.resizeRowsToContents()
        table.horizontalHeader().setMinimumSectionSize(250)        
        table.horizontalHeader().setStretchLastSection(True)        
        text = QtGui.QPlainTextEdit(splitter)
        text.setReadOnly(True)                
        closeButton = QtGui.QPushButton()
        closeButton.setText("Close")
        closeButton.setMaximumWidth(60)
        QObject.connect(closeButton, QtCore.SIGNAL("clicked()"), self.closeButtonPressed)
        layout.addWidget(splitter)
        layout.addWidget(closeButton)
        self.setLayout(layout)
        QtCore.QMetaObject.connectSlotsByName(self)
    

    def closeButtonPressed(self):
        self.close()
        
