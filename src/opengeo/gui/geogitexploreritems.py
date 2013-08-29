import os
import traceback
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
from qgis.core import *
from opengeo.gui.exploreritems import TreeItem
from opengeo.geogit.repo import Repository
from opengeo.geogit.cliconnector import CLIConnector
from opengeo import geogit
from opengeo.qgis import utils
from opengeo.gui.geogitimportdialog import ImportAndCommitDialog, ImportDialog
from opengeo.qgis.exporter import exportVectorLayer
from opengeo.geogit.geogitexception import GeoGitException
from opengeo.geogit import diff
from opengeo.gui.createbranch import CreateBranchDialog
from opengeo.gui.diffdialog import DiffDialog
from opengeo.geogit.diff import TYPE_ADDED, TYPE_MODIFIED
from opengeo.gui.refwidget import RefDialog
from opengeo.gui.commitdialog import CommitDialog

geogitIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/geogit.png")
repoIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/repo.gif")   
worktreeCleanIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/worktree_clean.gif")
worktreeUncleanIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/worktree_unclean.png")
commitIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/commit.png")
treeIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/tree.gif")  
 
class GeogitRepositoriesItem(TreeItem):

    def __init__(self):   
        self.repos = {}          
        TreeItem.__init__(self, None, geogitIcon, "Geogit repositories") 
                 
    def contextMenuActions(self, tree, explorer):  
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/add.png")      
        createRepoAction = QtGui.QAction(icon, "Create new repository...", explorer)
        createRepoAction.triggered.connect(lambda: self.addGeogitRepo(explorer, True))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/add.png")      
        createRepoConnectionAction = QtGui.QAction(icon, "Add new repository connection...", explorer)
        createRepoConnectionAction.triggered.connect(lambda: self.addGeogitRepo(explorer, False))
        return [createRepoAction, createRepoConnectionAction]

                              
    def addGeogitRepo(self, explorer, init):  
        folder = unicode(QtGui.QFileDialog.getExistingDirectory(explorer, "GeoGit repository folder"));
        if folder != "": 
            try:
                repo = Repository(folder, CLIConnector(), init)
            except GeoGitException, e:
                explorer.setInfo(str(e), 1)
                return                
            folder_name = os.path.basename(folder)               
            name = folder_name
            i = 2
            while name in self.repos.keys():
                name = folder_name + "_" + str(i)
                i += 1                                 
            item = self.getGeogitRepoItem(repo, name, explorer)
            if item is not None:
                self.repos[name] = repo
                self.addChild(item)
                self.setExpanded(True)
        
        
    def getGeogitRepoItem(self, repo, name, explorer):    
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))
        try:    
            geogitItem = GeogitRepositoryItem(repo, name)
            geogitItem.populate()
            QtGui.QApplication.restoreOverrideCursor()
            explorer.setInfo("Repository connection '" + name + "' correctly created")
            return geogitItem
        except Exception, e:   
            traceback.print_exc()         
            QtGui.QApplication.restoreOverrideCursor()
            explorer.setInfo("Could not create repository connection:" + str(e), 1)    
                         
class GeogitRepositoryItem(TreeItem):
     
    def __init__(self, repo, name):                      
        TreeItem.__init__(self, repo, repoIcon, name)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)          
        
    def populate(self):                             
        self.worktreeItem = GeogitWorkTreeItem(self.element)        
        self.addChild(self.worktreeItem)          
        log = self.element.log(geogit.HEAD)                            
        for entry in log:
            commitItem = GeogitCommitItem(entry)
            commitItem.setChildIndicatorPolicy(QtGui.QTreeWidgetItem.ShowIndicator)
            self.addChild(commitItem)  
            
    def contextMenuActions(self, tree, explorer):  
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/delete.gif")      
        removeRepoAction = QtGui.QAction(icon, "Remove", explorer)
        removeRepoAction.triggered.connect(lambda: self.removeRepo(explorer))
        createBranchAction = QtGui.QAction("Create branch...", explorer)
        createBranchAction.triggered.connect(lambda: self.createBranch(explorer))
        checkoutBranchAction = QtGui.QAction("Switch/checkout...", explorer)
        checkoutBranchAction.triggered.connect(lambda: self.checkout(explorer))
        importAndCommitAction = QtGui.QAction("Import and create new snapshot...", explorer)
        importAndCommitAction.triggered.connect(lambda: self.importAndCommit(explorer))
        importAction = QtGui.QAction("Import...", explorer)
        importAction.triggered.connect(lambda: self.importData(explorer))
        return[removeRepoAction, createBranchAction, checkoutBranchAction, importAction, importAndCommitAction] 
    
    def _getDescriptionHtml(self, tree, explorer):                        
        html = u'<div style="background-color:#ffffcc;"><h1>&nbsp; ' + self.text(0) + '</h1></div></br>'                  
        html += '<li><b>Current HEAD at: </b>' + str(self.element.head()) + ' &nbsp;<a href="modify:checkout">Change</a></li>\n'        
        html += '</ul>'
        html += "<p><h3><b>Available actions</b></h3></p><ul>"
        actions = self.contextMenuActions(tree, explorer)
        for action in actions:
            if action.isEnabled():
                html += '<li><a href="' + action.text() + '">' + action.text() + '</a></li>\n'
        html += '</ul>'            
        return html  
    
    def linkClicked(self, tree, explorer, url):
        actionName = url.toString()
        if actionName == 'modify:checkout':
            self.checkout(explorer)
        actions = self.contextMenuActions(tree, explorer)
        for action in actions:
            if action.text() == actionName:
                action.trigger()
                return     
        
    def createBranch(self, explorer):
        repo = self.element
        dlg = CreateBranchDialog(repo)
        dlg.exec_()
        ref = dlg.getref()                
        if ref is not None:            
            explorer.run(repo.createbranch, "Create new branch", [], ref, dlg.getName(), dlg.isForce(), dlg.isCheckout())                            
            if dlg.isCheckout():
                self.refreshContent(explorer) 
                  
    
    def checkout(self, explorer):
        dialog = RefDialog(self.element)
        dialog.exec_()
        ref = dialog.getref() 
        if ref:
            explorer.run(self.element.checkout, "Checkout reference '" + ref + "'", [], ref)
            self.refreshContent(explorer)
    
    def importData(self, explorer):
        dlg = ImportDialog()
        dlg.exec_()
        if dlg.layer is not None:                         
            explorer.run(self.element.importshp, "Import layer into repository", [self.worktreeItem], 
                          exportVectorLayer(dlg.layer), dlg.add, dlg.layer.name())
            
    
    def importAndCommit(self, explorer):
        dlg = ImportAndCommitDialog()
        dlg.exec_()
        if dlg.layer is not None:
            def _importAndCommit():
                #explorer.setProgressMaximum(3)                
                self.element.importshp(exportVectorLayer(dlg.layer), dest = dlg.layer.name())
                #explorer.setProgress(1)
                self.element.add()
                #explorer.setProgressMaximum(2)
                self.element.commit(dlg.message)
                #explorer.setProgressMaximum(3)
            explorer.run(_importAndCommit, "Import layer into repository and commit", [self]) 
            
    
    def removeRepo(self, explorer):
        del self.parent().repos[self.text(0)]
        parent = self.parent()        
        parent.takeChild(parent.indexOfChild(self))  
        explorer.setDescriptionWidget(QtGui.QWidget())                    
        
class GeogitWorkTreeItem(TreeItem):
     
    def __init__(self, repo):
        self.diffs = repo.notindatabase();
        self.isDirty = len(self.diffs) > 0 
        text = "Working Tree [NOT CLEAN]" if self.isDirty else "Working Tree"  
        icon = worktreeUncleanIcon if self.isDirty else worktreeCleanIcon                     
        TreeItem.__init__(self, repo, icon, text)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
          
        
    def contextMenuActions(self, tree, explorer):      
        commitAction = QtGui.QAction("Commit", explorer)
        commitAction.triggered.connect(lambda: self.commit(explorer))
        commitAction.setEnabled(self.isDirty)
        return[commitAction]  
        
    def refreshContent(self, explorer):
        self.diffs = self.element.notindatabase();
        self.isDirty = len(self.diffs) > 0        
        text = "Working Tree [NOT CLEAN]" if self.isDirty else "Working Tree"  
        icon = worktreeUncleanIcon if self.isDirty else worktreeCleanIcon
        self.setText(0, text)
        self.setIcon(0, icon)
                       
        
    def _getDescriptionHtml(self, tree, explorer):                        
        html = u'<div style="background-color:#ffffcc;"><h1>&nbsp; ' + self.text(0) + '</h1></div></br>'          
        html += '<p><h3><b>Changes</b></h3></p><ul>'
        def colorFromType(t):
            if t == TYPE_ADDED:
                return "#228b22"
            elif t == TYPE_MODIFIED:
                return "#8b4513"
            else:
                return "#b22222"
        for diff in self.diffs:
            html += ('<li><b><font color="' + colorFromType(diff.type()) +'">' + diff.path 
                    + '</font></b>  &nbsp;<a href="' + diff.path + '">View change</a></li>\n')
            
        return html
    
    def linkClicked(self, tree, explorer, url):
        url  = url.toString()
        for diff in self.diffs:
            if url == diff.path:
                ref = self.element.commit.ref
                repo = self.element.commit.repo
                dlg = DiffDialog(repo, ref, ref + "~1")
                dlg.exec_()
                return            
        actions = self.contextMenuActions(tree, explorer)
        for action in actions:
            if action.text() == url:
                action.trigger()
                return    
            
    def commit(self, explorer):
        dlg = CommitDialog(self.element)
        dlg.exec_()
        if dlg.getPaths():
            self.element.commit(dlg.getMessage(), dlg.getPaths())
            self.refreshContent(explorer)
        
class GeogitCommitItem(TreeItem):
     
    def __init__(self, entry):                            
        TreeItem.__init__(self, entry, commitIcon, entry.commit.message)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable) 
        
    def _getDescriptionHtml(self, tree, explorer):                        
        html = u'<div style="background-color:#ffffcc;"><h1>&nbsp; ' + self.text(0) + '</h1></div></br>'          
        html += '<p><h3><b>Properties</b></h3></p><ul>'
        html += '<li><b>Commit ID: </b>' + str(self.element.commit.commitid) + '</li>\n'
        html += '<li><b>Parent: </b>' + str(self.element.commit.parent) +'</li>\n'     
        html += '<li><b>Message: </b>' + str(self.element.commit.message) +'</li>\n'
        html += '<li><b>Author name: </b>' + str(self.element.commit.authorname) +'</li>\n'
        html += '<li><b>Author date: </b>' + str(self.element.commit.authordate) +'</li>\n'    
        html += '<li><b>Commiter name: </b>' + str(self.element.commit.commitername) +'</li>\n'
        html += '<li><b>Commiter date: </b>' + str(self.element.commit.commiterdate) +'</li>\n'
        html += '</ul>'
        html += '<p><h3><b>Changes</b></h3></p><ul>'
        def colorFromType(t):
            if t == TYPE_ADDED:
                return "#228b22"
            elif t == TYPE_MODIFIED:
                return "#8b4513"
            else:
                return "#b22222"
        for diff in self.element.diffset:
            html += ('<li><b><font color="' + colorFromType(diff.type()) +'">' + diff.path 
                    + '</font></b>  &nbsp;<a href="' + diff.path + '">View change</a></li>\n')
            
        return html  
    
    def contextMenuActions(self, tree, explorer): 
        compareAction = QtGui.QAction("Compare with working tree...", explorer)
        compareAction.triggered.connect(lambda: self.compareCommitAndWorkingTree(explorer))        
        checkoutAction = QtGui.QAction("Checkout this commit", explorer)
        checkoutAction.triggered.connect(lambda: self.checkoutCommit(explorer))        
        resetAction = QtGui.QAction("Reset current branch to this commit...", explorer)
        resetAction.triggered.connect(lambda: self.reset(explorer))         
        tagAction = QtGui.QAction("Create tag at this commit...", explorer)
        tagAction.triggered.connect(lambda: self.createTag(explorer))        
        branchAction = QtGui.QAction("Create branch at this commit...", explorer)
        branchAction.triggered.connect(lambda: self.createBranchAtCommit(explorer))
        return [compareAction, checkoutAction, resetAction, tagAction, branchAction]
        
    def checkoutCommit(self, explorer):
        ref = self.element.commit.ref
        repo = self.element.commit.repo
        explorer.run(repo.checkout, "Checkout commit " + ref, [self], ref)
        
    def reset(self, explorer):
        value, ok = QtGui.QInputDialog.getItem(self, "Reset", "Select reset mode", ["Soft", "Mixed", "Hard"], current=1, editable=False)
        if ok:
            repo = self.element.commit.repo
            ref = self.element.commit.ref
            explorer.run(repo.reset, "Reset to commit " + ref, str(value).lower())                     
        
    def compareCommitAndWorkingTree(self, explorer):
        ref = self.element.commit.ref
        repo = self.element.commit.repo
        dlg = DiffDialog(repo, ref, geogit.WORK_HEAD)
        dlg.exec_()
    
    def createBranchAtCommit(self, explorer):        
        ref = self.element.commit.ref
        repo = self.element.commit.repo
        dlg = CreateBranchDialog(repo, ref)
        dlg.exec_()
        ref = dlg.getref()                
        if ref is not None:          
            explorer.run(repo.createbranch, "Create branch at commit " + ref, [], dlg.getName(), dlg.isForce(), dlg.isCheckout())        
            if dlg.isCheckout():
                self.refreshContent(explorer)                
                
    def createTag(self, explorer):               
        name, ok = QtGui.QInputDialog.getText(self, 'Tag name','Enter tag name:')        
        if ok:        
            self.element.commit.repo.createtag(self.element.commit, str(name))                    
    
    def populate(self):            
        trees = self.element.commit.trees()
        for tree in trees:
            item = GeogitTreeItem(tree)
            self.addChild(item)
                           
              
class GeogitTreeItem(TreeItem):
     
    def __init__(self, tree):                            
        TreeItem.__init__(self, tree, treeIcon, tree.path)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)  
        
    def contextMenuActions(self, tree, explorer):      
        addToProjectAction = QtGui.QAction("Add as project layer", explorer)
        addToProjectAction.triggered.connect(lambda: self.addToProject(explorer))
        return[addToProjectAction]                

    def addToProject(self, explorer):           
        filename = utils.tempFilenameInTempFolder("exported.shp")
        if  filename != "":    
            def _addToProject():        
                self.element.repo.exportshp(str(self.element), unicode(filename))                
            explorer.run(_addToProject, "Add Geogit tree to QGIS project", [])
            layer = QgsVectorLayer(filename, self.element.path, "ogr")            
            QgsMapLayerRegistry.instance().addMapLayers([layer])
            explorer.updateQgisContent()
        
    