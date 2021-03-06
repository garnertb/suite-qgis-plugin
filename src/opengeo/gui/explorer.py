from PyQt4.QtCore import *
from qgis.core import *
from opengeo.gui.explorerthread import ExplorerThread
from opengeo.gui.exploreritems import *

import os
from opengeo.gui.explorerwidget import ExplorerWidget
from opengeo import config

INFO = 0
ERROR = 1
CONSOLE_OUTPUT = 2   
    
class OpenGeoExplorer(QtGui.QDockWidget):

    def __init__(self, parent = None, singletab = True):
        super(OpenGeoExplorer, self).__init__()  
        self.singletab = singletab      
        self.initGui()
        
    def initGui(self):
        self.explorerWidget = None 
        self.progressMaximum = 0   
        self.isProgressVisible = False
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  
        self.dockWidgetContents = QtGui.QWidget()
        self.setWindowTitle('OpenGeo explorer')
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(Qt.Vertical)
        self.subwidget = QtGui.QWidget()               
        self.explorerWidget = ExplorerWidget(self, self.singletab)
        self.toolbar = QtGui.QToolBar()
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar.setVisible(self.singletab)
        self.setToolbarActions([])
        self.splitter.addWidget(self.explorerWidget)                             
        self.log = QtGui.QTextEdit()        
        self.description = QtGui.QWidget()
        self.descriptionLayout = QtGui.QVBoxLayout()
        self.descriptionLayout.setSpacing(2)
        self.descriptionLayout.setMargin(0)
        self.description.setLayout(self.descriptionLayout)
        self.splitter.addWidget(self.description)
        self.setDescriptionWidget()
        self.progress = None
        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(2)
        self.layout.setMargin(0)                                               
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.splitter)     
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
        self.toolbar.clear()
        for action in actions:
            if action.icon().isNull():
                icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/process.png")
                action.setIcon(icon)        
        if len(actions) == 0:
            refreshIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/refresh.png")                         
            refreshAction = QtGui.QAction(refreshIcon, "Refresh", self)
            refreshAction.triggered.connect(self.explorerWidget.refreshContent)
            actions.append(refreshAction)
             
        for action in actions:   
            button = QtGui.QPushButton()
            button.setIcon(action.icon())
            button.setToolTip(action.text())
            button.setEnabled(action.isEnabled())
            button.clicked.connect(action.trigger)                           
            self.toolbar.addWidget(button)
            
        self.toolbar.update()
                    
    def refreshContent(self):
        self.explorerWidget.refreshContent()
        self.refreshDescription()
        
    def catalogs(self):        
        if self.explorerWidget is None:
            return {}
        return self.explorerWidget.catalogs()
    
    def geogitRepositories(self):
        return self.explorerWidget.geogitRepostories()
    
    def pgDatabases(self):
        return self.explorerWidget.pgDatabases()
        
    def updateQgisContent(self):
        self.explorerWidget.updateQgisContent()
                   
    def run(self, command, msg, refresh, *params):
        error = False                                   
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))        
        thread = ExplorerThread(command, *params)                
        def finish():
            QtGui.QApplication.restoreOverrideCursor()
            for item in refresh:
                if item is not None:
                    item.refreshContent(self)
            if None in refresh:
                self.refreshContent()            
            if msg is not None and not self.isProgressVisible:
                self.setInfo("Operation <i>" + msg + "</i> correctly executed")                
        def error(msg):
            QtGui.QApplication.restoreOverrideCursor()            
            self.setInfo(msg, ERROR)   
            error = True         
        thread.finish.connect(finish)
        thread.error.connect(error)                                         
        thread.start()
        thread.wait()      
        self.refreshDescription()
        
        return error
        
    def resetActivity(self):               
        config.iface.messageBar().clearWidgets()
        self.isProgressVisible = False
        self.progress = None  
        self.progressMaximum = 0                    
        
    def setProgress(self, value):
        if self.progress is not None:
            self.progress.setValue(value)        
        
    def setProgressMaximum(self, value, msg = ""):
        self.progressMaximum = value
        self.isProgressVisible = True
        self.progressMessageBar = config.iface.messageBar().createMessage("Task", msg)
        self.progress = QtGui.QProgressBar()
        self.progress.setMaximum(self.progressMaximum)
        self.progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        self.progressMessageBar.layout().addWidget(self.progress) 
        config.iface.messageBar().pushWidget(self.progressMessageBar, config.iface.messageBar().INFO)   
        
    def setInfo(self, msg, msgtype = INFO):
        if msgtype == ERROR:
            if self.progressMaximum != 0:
                self.resetActivity()
            config.iface.messageBar().pushMessage("Error", msg, 
                                                  level = config.iface.messageBar().CRITICAL,                                                  
                                                  duration = 3)            
        else:
            config.iface.messageBar().pushMessage("Info", msg, 
                                                  level = config.iface.messageBar().INFO,
                                                  duration = 3)
                   
            
    def setDescriptionWidget(self, widget = None):                
        item = self.descriptionLayout.itemAt(0)        
        if item:
            self.descriptionLayout.removeItem(item)
            item.widget().close()
        if widget is None:                    
            widget = QtGui.QTextBrowser()
            widget.setHtml(u'<div style="background-color:#ffffcc;"><h1>No description available</h1></div><ul>') 
                                  
        self.descriptionLayout.addWidget(widget)
        
        

    def refreshDescription(self):
        item = self.explorerWidget.currentTree().lastClickedItem()
        if item is not None:
            try:      
                self.explorerWidget.currentTree().treeItemClicked(item, 0)
            except:
                self.setDescriptionWidget(None)        
    