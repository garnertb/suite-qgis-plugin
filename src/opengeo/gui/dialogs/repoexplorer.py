import os
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from opengeo.geogit.tree import Tree
from opengeo.gui.dialogs.twowaydiff import TwoWayDiffViewerDialog
from opengeo.geogit.feature import Feature
from opengeo.gui.dialogs.featureviewer import FeatureViewer
from opengeo.qgis import utils
from opengeo.gui.dialogs.blamedialog import BlameDialog

class RepoExplorer(QtGui.QDialog):
    def __init__(self, explorer, worktree, repo, ref):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.explorer = explorer
        self.worktree = worktree
        self.repo = repo
        self.ref = ref
        self.setupUi()
        
    def setupUi(self):
        self.resize(800, 600)
        self.setWindowTitle("Repository explorer")
        layout = QVBoxLayout()                    
        self.tree = QTreeWidget()
        self.tree.itemExpanded.connect(self.treeItemExpanded)
        self.tree.itemClicked.connect(self.treeItemClicked)         
        self.tree.header().hide()
        self.tree.setSelectionMode(QAbstractItemView.NoSelection)        
        self.ftText = QtGui.QTextBrowser()        
        self.table = QTableWidget()
        self.table = QtGui.QTableWidget()
        self.table.setColumnCount(1)        
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().hide() 
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.showTablePopupMenu)       
        self.table.setSelectionMode(QAbstractItemView.SingleSelection);
        self.table.doubleClicked.connect(self.itemDoubleClicked)
        self.table.setStyleSheet("QTableView{outline: 0;}")
        
        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Vertical)
        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.ftText)
        self.splitter2 = QSplitter()
        self.splitter2.addWidget(self.splitter)
        self.splitter2.addWidget(self.table)        
        layout.addWidget(self.splitter2)        
        self.setLayout(layout)
        QtCore.QMetaObject.connectSlotsByName(self)
        
        item = PathItem(self.repo, self.ref)
        self.tree.addTopLevelItem(item)
        self.treeItemClicked(item, 0)
    
    def itemDoubleClicked(self, modelIndex):
        item = self.table.item(modelIndex.row(), modelIndex.column())
        self.open(item.element)
            
    def setTableContent(self, item):
        self.currentPath = item
        content = item.content
        self.table.clear()                
        self.table.setRowCount(len(content))                        
        for i, child in enumerate(content):
            self.table.setItem(i, 0, ChildItem(child));                        
        self.table.horizontalHeader().setStretchLastSection(True) 
        self.table.resizeRowsToContents()   

    def treeItemExpanded(self, item):
        item.populate()

    def treeItemClicked(self, item, column):
        self.ftText.setText(item.description())
        item.populate()
        self.setTableContent(item)
           
        
    def showTablePopupMenu(self,point):
        currentItem = self.table.itemAt(point)
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../../images/open.png") 
        openAction = QtGui.QAction(icon, "Open", self)
        openAction.triggered.connect(lambda: self.open(currentItem.element))
        popupmenu = QtGui.QMenu()             
        popupmenu.addAction(openAction)
        if isinstance(currentItem.element, Feature): 
            if self.ref != "WORK_HEAD":           
                icon = QtGui.QIcon(os.path.dirname(__file__) + "/../../images/diff.png") 
                compareAction = QtGui.QAction(icon, "Compare with working tree...", self)
                compareAction.triggered.connect(lambda: self.compare(currentItem.element.path))          
                icon = QtGui.QIcon(os.path.dirname(__file__) + "/../../images/reset.png") 
                revertAction = QtGui.QAction(icon, "Revert to this version...", self)
                revertAction.triggered.connect(lambda: self.revert(currentItem.element.path))
                popupmenu.addAction(compareAction) 
                popupmenu.addAction(revertAction)
            icon = QtGui.QIcon(os.path.dirname(__file__) + "/../../images/blame.png") 
            blameAction = QtGui.QAction(icon, "Blame...", self)
            blameAction.triggered.connect(lambda: self.blame(currentItem.element.path))                 
             
            popupmenu.addAction(blameAction)        
        else:
            icon = QtGui.QIcon(os.path.dirname(__file__) + "/../../images/export_geogit_tree.png") 
            exportAction = QtGui.QAction(icon, "Add as project layer", self)
            exportAction.triggered.connect(lambda: self.export(currentItem.element.path))
            popupmenu.addAction(exportAction)
        popupmenu.exec_(self.table.mapToGlobal(point))
                
    def export(self, path):           
        filename = utils.tempFilenameInTempFolder("exported.sqlite")     
        def _addToProject():        
            self.repo.exportsl(self.ref + ":" + path, unicode(filename))                
        self.explorer.run(_addToProject, "Add Geogit tree to QGIS project", [])
        layer = QgsVectorLayer(filename, path, "ogr")   
        QgsMapLayerRegistry.instance().addMapLayers([layer])
        self.explorer.updateQgisContent()
                            
    def open(self, element):
        if isinstance(element, Feature):
            dlg = FeatureViewer(element)
            dlg.exec_()
        else:            
            for i in xrange(self.currentPath.childCount()):
                child = self.currentPath.child(i)
                if child.path == element.path:
                    child.setExpanded(True)
                    child.parent().setExpanded(True)
                    child.populate()
                    self.setTableContent(child)
                    self.ftText.setText(child.description())
                    return

    
    def compare(self, path):
        dlg = TwoWayDiffViewerDialog(self.repo.getfeaturediffs(
                                    "WORK_HEAD", self.ref, path))                   
        dlg.exec_()
            
    def blame(self, path):        
        dlg = BlameDialog(self.repo, self.repo.blame(path))
        dlg.exec_()
        
    def revert(self, path):
        self.repo.checkout(self.ref, [path])
        self.worktree.refresh()
        
        

class PathItem(QtGui.QTreeWidgetItem): 
    def __init__(self, repo, ref, path = None): 
        QtGui.QTreeWidgetItem.__init__(self) 
        self.repo = repo
        self.ref = ref
        self.path = path  
        self.content = None 
        self._description = None 
        if path is None:
            text = "/"        
        else:
            text = path[path.rfind("/") + 1:] if "/" in path else path

        self.setText(0, text)   
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../../images/folder.png")             
        self.setIcon(0, icon)   
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        self.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator) 
        
    def description(self):
        self.populate()                   
        return self._description
                    
    def populate(self):
        if self.content is not None:
            return 
        if self.path is None:
            self._description = ""            
        else:
            self._description = self.repo.show(self.ref + ":" + self.path)
        self.content = self.repo.children(self.ref, self.path)
        for child in self.content:
            if isinstance(child, Tree):
                path = self.path + "/" + child.path if self.path is not None else child.path
                item = PathItem(self.repo, self.ref, path)
                self.addChild(item)
        self.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.DontShowIndicatorWhenChildless)                 
    
class ChildItem(QtGui.QTableWidgetItem): 
    def __init__(self, element): 
        QtGui.QTreeWidgetItem.__init__(self) 
        self.element = element   
        text = element.path[element.path.rfind("/") + 1:] if "/" in element.path else element.path
        self.setText(text)   
        if isinstance(element, Tree): 
            icon = QtGui.QIcon(os.path.dirname(__file__) + "/../../images/folder.png")
        else:
            icon = QtGui.QIcon(os.path.dirname(__file__) + "/../../images/layer_polygon.png")
        self.setIcon(icon)   
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
  