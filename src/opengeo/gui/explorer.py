from PyQt4.QtCore import *
from qgis.core import *
from opengeo.gui.explorerthread import ExplorerThread
from opengeo.gui.exploreritems import *

import os
from opengeo.gui.explorerwidget import ExplorerWidget

INFO = 0
ERROR = 1
CONSOLE_OUTPUT = 2   
    
class OpenGeoExplorer(QtGui.QDockWidget):

    def __init__(self, parent = None, singletab = False):
        super(OpenGeoExplorer, self).__init__()  
        self.singletab = singletab      
        self.initGui()
        
    def initGui(self):    
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  
        self.dockWidgetContents = QtGui.QWidget()
        self.setWindowTitle('OpenGeo explorer')
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(Qt.Vertical)
        self.subwidget = QtGui.QWidget()               
        self.explorerWidget = ExplorerWidget(self, self.singletab)
        self.toolbar = QtGui.QToolBar()
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)#Qt.ToolButtonTextUnderIcon)
        self.toolbar.setVisible(self.singletab)
        self.setToolbarActions([])
        self.splitter.addWidget(self.explorerWidget)         
        self.tabbedPanel = QtGui.QTabWidget()                      
        self.log = QtGui.QTextEdit()        
        self.tabbedPanel.addTab(QtGui.QWidget(), "Description")
        self.tabbedPanel.addTab(self.log, "Log")
        self.splitter.addWidget(self.tabbedPanel);
        self.tabbedPanel.setVisible(True)
        self.progress = QtGui.QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)                       
        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(2)
        self.layout.setMargin(0)     
        self.status = QtGui.QLabel()   
        self.status.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)                                             
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.splitter)
        #self.layout.addWidget(self.status)
        self.layout.addWidget(self.progress)        
        self.setLayout(self.layout)
        self.dockWidgetContents.setLayout(self.layout)
        self.setWidget(self.dockWidgetContents)  
        
        self.topLevelChanged.connect(self.dockStateChanged)
        
    def dockStateChanged(self, floating):        
        if floating:
            self.resize(800, 450)
            #self.move((self.parent().width() - self.width() / 2), (self.parent().height() - self.height() / 2))
            self.splitter.setOrientation(Qt.Horizontal)
        else:
            self.splitter.setOrientation(Qt.Vertical)                

    def setToolbarActions(self, actions):        
        icon = None#QtGui.QIcon(os.path.dirname(__file__) + "/../images/add.png")
        self.toolbar.clear()        
        if len(actions) == 0:
            refreshIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/refresh.png")                         
            refreshAction = QtGui.QAction(refreshIcon, "Refresh", self)
            refreshAction.triggered.connect(self.explorerWidget.refreshContent)
            self.toolbar.addAction(refreshAction)
             
        for action in actions:
            #action.setIcon(icon)                                    
            self.toolbar.addAction(action)
        self.toolbar.update()
        
            
    def refreshContent(self):
        self.explorerWidget.refreshContent()
        self.refreshDescription()
        
    def catalogs(self):        
        return self.explorerWidget.catalogs()
        
    def updateQgisContent(self):
        self.explorerWidget.updateQgisContent()
                   
    def run(self, command, msg, refresh, *params):
        error = False                                
        self.status.setText(msg)
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))        
        thread = ExplorerThread(command, *params)                
        def finish():
            QtGui.QApplication.restoreOverrideCursor()
            for item in refresh:
                if item is not None:
                    item.refreshContent()
            if None in refresh:
                self.refreshContent()
            self.setInfo("Operation <i>" + msg + "</i> correctly executed")
        def error(msg):
            QtGui.QApplication.restoreOverrideCursor()            
            self.setInfo(msg, ERROR)   
            error = True         
        thread.finish.connect(finish)
        thread.error.connect(error)                                         
        thread.start()
        thread.wait()
        self.status.setText("")
        print "refreshing"
        self.refreshDescription()
        
        return error
        
    def resetActivity(self):
        self.status.setText("")
        self.progress.setValue(0)
        
    def setStatus(self, text):
        self.status.setText(text)
        
    def setInfo(self, msg, msgtype = INFO):
        if msgtype == ERROR:
            self.log.append('<span style="color:red">ERROR: ' + msg + '</span>')
            self.tabbedPanel.setCurrentIndex(1)            
        elif msgtype == INFO:
            self.log.append('<qt><span style="color:blue">INFO: ' + msg + '</span></qt>')
        else:
            self.log.append('<span style="color:grey">INFO: ' + msg + '</span>')
            
    def setDescriptionWidget(self, widget):
        isVisible = self.tabbedPanel.currentIndex() == 0
        self.tabbedPanel.removeTab(0)
        self.tabbedPanel.insertTab(0, widget, "Description")
        if isVisible:
            self.tabbedPanel.setCurrentIndex(0)
        

    def refreshDescription(self):
        item = self.explorerWidget.currentTree().lastClickedItem()
        if item is not None:
            try:      
                self.explorerWidget.currentTree().treeItemClicked(item, 0)
            except:
                self.setDescriptionWidget(QtGui.QWidget())
        else:
            print "NOONE"
    