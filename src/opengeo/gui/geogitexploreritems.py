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
from dialogs.geogitimportdialog import ImportAndCommitDialog, ImportDialog
from opengeo.qgis.exporter import exportVectorLayer
from opengeo.geogit.geogitexception import GeoGitException
from opengeo.geogit import diff
from dialogs.createbranch import CreateBranchDialog
from dialogs.diffdialog import DiffDialog
from opengeo.geogit.diff import TYPE_ADDED, TYPE_MODIFIED
from dialogs.geogitref import RefDialog
from dialogs.commitdialog import CommitDialog
from dialogs.twowaydiff import TwoWayDiffViewerDialog
from opengeo.gui.qgsexploreritems import QgsLayerItem
from opengeo.gui.dialogs.remoterepodialog import DefineRemoteRepoDialog
from opengeo.gui.dialogs.pushdialog import PushDialog
from opengeo.gui.dialogs.remotesdialog import RemotesDialog
from opengeo.gui.dialogs.repoexplorer import RepoExplorer

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
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/init.png")      
        createRepoAction = QtGui.QAction(icon, "Init/create new repository...", explorer)
        createRepoAction.triggered.connect(lambda: self.addGeogitRepo(explorer, True))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/add.png")      
        createRepoConnectionAction = QtGui.QAction(icon, "Add new repository...", explorer)
        createRepoConnectionAction.triggered.connect(lambda: self.addGeogitRepo(explorer, False))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/clone.png")      
        cloneRepoAction = QtGui.QAction(icon, "Clone remote repository...", explorer)
        cloneRepoAction.triggered.connect(lambda: self.cloneRepo(explorer))
        return [createRepoAction, createRepoConnectionAction, cloneRepoAction]

                              
    def cloneRepo(self, explorer):
        dlg = DefineRemoteRepoDialog()
        dlg.exec_()
        if dlg.ok:
            explorer.run(CLIConnector.clone, "Clone remote repo", [], dlg.url, dlg.folder)
            try:
                repo = Repository(dlg.folder, CLIConnector(), True)
            except GeoGitException, e:
                explorer.setInfo(str(e), 1)
                return                                                             
            item = self.getGeogitRepoItem(repo, dlg.name, explorer)
            if item is not None:                
                self.repos[dlg.name] = repo                
                self.addChild(item)
                self.setExpanded(True)
            
                                  
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
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/push.png")      
        pushAction = QtGui.QAction(icon, "Push...", explorer)
        pushAction.triggered.connect(lambda: self.pushRepo(explorer))          
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/pull.png")      
        pullAction = QtGui.QAction(icon, "Pull...", explorer)
        pullAction.triggered.connect(lambda: self.pullRepo(explorer))      
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/remotes.gif")      
        manageRemotesAction = QtGui.QAction(icon, "Manage remotes...", explorer)
        manageRemotesAction.triggered.connect(self.manageRemotes)    
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/delete.gif")      
        removeRepoAction = QtGui.QAction(icon, "Remove", explorer)
        removeRepoAction.triggered.connect(lambda: self.removeRepo(explorer))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/create_branch.png")
        createBranchAction = QtGui.QAction(icon, "Create branch...", explorer)
        createBranchAction.triggered.connect(lambda: self.createBranch(explorer))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/checkout.png")
        checkoutBranchAction = QtGui.QAction(icon, "Switch/checkout...", explorer)
        checkoutBranchAction.triggered.connect(lambda: self.checkout(explorer))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/import_into_geogit.png")
        importAndCommitAction = QtGui.QAction(icon, "Import and create new snapshot...", explorer)
        importAndCommitAction.triggered.connect(lambda: self.importAndCommit(explorer))        
        importAction = QtGui.QAction(icon, "Import...", explorer)
        importAction.triggered.connect(lambda: self.importData(explorer))
        return[pushAction, pullAction, manageRemotesAction, removeRepoAction, createBranchAction, 
               checkoutBranchAction, importAction, importAndCommitAction] 
    
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

    def manageRemotes(self):
        dlg = RemotesDialog(self.element)
        dlg.exec_()
        
    def pullRepo(self, explorer):
        repo = self.element
        dlg = PushDialog(repo)
        dlg.setWindowTitle("Pull")
        dlg.exec_()
        if dlg.ok:
            explorer.run(repo.pull, "Pull from remote repository", [self], dlg.remote, dlg.refspec, dlg.all)
        
    def pushRepo(self, explorer):        
        repo = self.element
        dlg = PushDialog(repo)
        dlg.exec_()
        if dlg.ok:
            explorer.run(repo.push, "Push to remote repository", [], dlg.remote, dlg.refspec, dlg.all)
        
    def createBranch(self, explorer):
        repo = self.element
        dlg = CreateBranchDialog(repo)
        dlg.exec_()                        
        if dlg.ok:
            ref = dlg.getref()            
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
        if dlg.ok:                         
            explorer.run(self.element.importshp, "Import layer into repository", [self.worktreeItem], 
                          exportVectorLayer(dlg.layer), dlg.add, dlg.layer.name())
            
    
    def importAndCommit(self, explorer):
        dlg = ImportAndCommitDialog()
        dlg.exec_()
        if dlg.message is not None:
            def _importAndCommit():              
                self.element.importshp(exportVectorLayer(dlg.layer), dest = dlg.layer.name())
                self.element.add()
                self.element.commit(dlg.message)
            explorer.run(_importAndCommit, "Import layer into repository and commit", [self]) 
            
    def acceptDroppedItems(self, tree, explorer, items):        
        toImport = []
        for item in items:         
            if isinstance(item, QgsLayerItem):
                if item.element.type() == QgsMapLayer.VectorLayer:
                    toImport.append(item.element)         
        if toImport:                
            dlg = ImportAndCommitDialog(False)
            dlg.exec_()
            if dlg.message is not None:
                explorer.setProgressMaximum(len(toImport) + 2, "Import layers into repository and commit")    
                for i, layer in enumerate(toImport):
                    def _importAndCommit():              
                        self.element.importshp(exportVectorLayer(layer), dest = layer.name())
                    explorer.run(_importAndCommit, None, [])             
                    explorer.setProgress(i + 1)
                explorer.run(self.element.add, None, [])
                explorer.setProgress(i + 2)
                explorer.run(self.element.commit, None, [], dlg.message)
                explorer.setProgress(i + 3)                                                  
                explorer.resetActivity()
                return [self]
        return []
    
    def acceptDroppedUris(self, tree, explorer, uris):       
        if uris:            
            files = []
            for uri in uris:
                if isinstance(uri, basestring):
                    file.append(uri)                    
                else:                                       
                    files.append(uri.uri) 
            if len(files) == 0:
                return []
            dlg = ImportAndCommitDialog(False)
            dlg.exec_()
            if dlg.message is not None:
                explorer.setProgressMaximum(len(files) + 2, "Import files into repository and commit")                                       
                for i, filename in enumerate(files):              
                    explorer.run(self.element.importshp, None, [], exportVectorLayer(filename))
                    explorer.setProgress(i + 1)
                explorer.run(self.element.add, None, [])
                explorer.setProgress(i + 2)
                explorer.run(self.element.commit, None, [], dlg.message)
                explorer.setProgress(i + 3)
                explorer.resetActivity()
                return [self]
            return []
        else:
            return []     
                      
    
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
        
    def refresh(self):
        self.diffs = self.element.notindatabase();
        self.isDirty = len(self.diffs) > 0 
        text = "Working Tree [NOT CLEAN]" if self.isDirty else "Working Tree"  
        icon = worktreeUncleanIcon if self.isDirty else worktreeCleanIcon 
        self.setIcon(0, icon)
        self.setText(0, text)           
        
    def contextMenuActions(self, tree, explorer): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/browser.png") 
        browserAction = QtGui.QAction(icon, "Repository browser...", explorer)
        browserAction.triggered.connect(lambda: openBrowser(explorer, self, self.element, "WORK_HEAD"))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/commit_op.png")     
        commitAction = QtGui.QAction(icon, "Commit", explorer)
        commitAction.triggered.connect(lambda: self.commit(explorer))
        commitAction.setEnabled(self.isDirty)
        return[browserAction, commitAction]  
        
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
        diffs = self.diffs if len(self.diffs) < 100 else self.diffs[0:100]
        for diff in diffs:
            html += ('<li><b><font color="' + colorFromType(diff.type()) +'">' + diff.path 
                    + '</font></b>  &nbsp;<a href="' + diff.path + '">View change</a></li>\n')
        if len(self.diffs) > 100:
            html += "<li><b>Too many changes. Only the first 100 are shown</b></li>"            
            
        return html
    
    def linkClicked(self, tree, explorer, url):
        url  = url.toString()
        for diff in self.diffs:
            if url == diff.path:             
                dlg = TwoWayDiffViewerDialog(self.element.getfeaturediffs(geogit.HEAD, geogit.WORK_HEAD, url))                   
                dlg.exec_()
                return            
        actions = self.contextMenuActions(tree, explorer)
        for action in actions:
            if action.text() == url:
                action.trigger()
                return  
    
    def acceptDroppedItems(self, tree, explorer, items):        
        toImport = []
        for item in items:         
            if isinstance(item, QgsLayerItem):
                if item.element.type() == QgsMapLayer.VectorLayer:
                    toImport.append(item.element)         
        if toImport:                    
            dlg = ImportDialog(False)
            dlg.exec_()
            if dlg.ok:
                explorer.setProgressMaximum(len(toImport), "Import layers into repository")   
                for i, layer in enumerate(toImport):
                    def _import():              
                        self.element.importshp(exportVectorLayer(layer), dest = layer.name())
                    explorer.run(_import, None, [])             
                    explorer.setProgress(i + 1)                                                            
                explorer.resetActivity()
                return [self]
        return []
    

    def acceptDroppedUris(self, tree, explorer, uris):       
        if uris:            
            files = []
            for uri in uris:
                if isinstance(uri, basestring):
                    file.append(uri)                    
                else:                                       
                    files.append(uri.uri) 
            if len(files) == 0:
                return []
            dlg = ImportDialog(False)
            dlg.exec_()
            if dlg.ok:
                explorer.setProgressMaximum(len(files) + 2, "Import files into repository")                                       
                for i, filename in enumerate(files):              
                    explorer.run(self.element.importshp, None, [], exportVectorLayer(filename))
                    explorer.setProgress(i + 1)                
                explorer.resetActivity()
                return [self]
            return []
        else:
            return []     
                                    
            
    def commit(self, explorer):
        dlg = CommitDialog(self.element)
        dlg.exec_()
        if dlg.getPaths():
            def _commit():
                self.element.add(dlg.getPaths())
                self.element.commit(dlg.getMessage())
            explorer.run(_commit, "Commit changes inworking tree", [self.parent()])             
        
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
            
        diffs = self.element.diffset if len(self.element.diffset) < 100 else self.element.diffset[0:100]
        for diff in diffs:
            html += ('<li><b><font color="' + colorFromType(diff.type()) +'">' + diff.path 
                    + '</font></b>  &nbsp;<a href="' + diff.path + '">View change</a></li>\n')
        if len(self.element.diffset) > 100:
            html += "<li><b>Too many changes. Only the first 100 are shown</b></li>"                 
            
        return html      

    def linkClicked(self, tree, explorer, url):
        url  = url.toString()
        for diff in self.element.diffset:
            if url == diff.path:             
                parentid = "0"*40 if self.element.commit.parent is None else self.element.commit.commitid + "~1"
                dlg = TwoWayDiffViewerDialog(self.element.commit.repo.getfeaturediffs(
                                    parentid, self.element.commit.commitid, url))                   
                dlg.exec_()
                return            
        actions = self.contextMenuActions(tree, explorer)
        for action in actions:
            if action.text() == url:
                action.trigger()
                return    
                
    
    def contextMenuActions(self, tree, explorer):
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/browser.png") 
        browserAction = QtGui.QAction(icon, "Repository browser...", explorer)
        browserAction.triggered.connect(lambda: openBrowser(explorer, self.parent().worktreeItem,
                                                            self.element.commit.repo, self.element.commit.ref)) 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/diff.png") 
        compareAction = QtGui.QAction(icon, "Compare with working tree...", explorer)
        compareAction.triggered.connect(lambda: self.compareCommitAndWorkingTree(explorer)) 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/checkout.png")       
        checkoutAction = QtGui.QAction(icon, "Checkout this commit", explorer)
        checkoutAction.triggered.connect(lambda: self.checkoutCommit(explorer))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/reset.png")        
        resetAction = QtGui.QAction(icon, "Reset current branch to this commit...", explorer)
        resetAction.triggered.connect(lambda: self.reset(tree, explorer))
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/tag.gif")         
        tagAction = QtGui.QAction(icon, "Create tag at this commit...", explorer)
        tagAction.triggered.connect(lambda: self.createTag(explorer)) 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/create_branch.png")       
        branchAction = QtGui.QAction(icon, "Create branch at this commit...", explorer)
        branchAction.triggered.connect(lambda: self.createBranchAtCommit(explorer))
        return [browserAction, compareAction, checkoutAction, resetAction, tagAction, branchAction]
        
    def checkoutCommit(self, explorer):
        ref = self.element.commit.ref
        repo = self.element.commit.repo
        explorer.run(repo.checkout, "Checkout commit " + ref, [self], ref)
        
    def reset(self, tree, explorer):
        value, ok = QtGui.QInputDialog.getItem(explorer, "Reset", "Select reset mode", ["Soft", "Mixed", "Hard"], current=1, editable=False)
        if ok:
            repo = self.element.commit.repo
            ref = self.element.commit.ref
            explorer.run(repo.reset, "Reset to commit " + ref, tree.findAllItems(repo), ref, str(value).lower())                     
        
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
        if dlg.ok:
            ref = dlg.getref()          
            explorer.run(repo.createbranch, "Create branch at commit " + ref, [], dlg.getName(), dlg.isForce(), dlg.isCheckout())        
            if dlg.isCheckout():
                self.refreshContent(explorer)                
                
    def createTag(self, explorer):               
        name, ok = QtGui.QInputDialog.getText(explorer, 'Tag name','Enter tag name:')        
        if ok:        
            explorer.run(self.element.commit.repo.createtag, "Create tag '" + unicode(name) + "'", 
                         [], self.element.commit, unicode(name))                    
    
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
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/export_geogit_tree.png") 
        addToProjectAction = QtGui.QAction(icon, "Add as project layer", explorer)
        addToProjectAction.triggered.connect(lambda: self.addToProject(explorer))
        return[addToProjectAction]                

    def addToProject(self, explorer):           
        filename = utils.tempFilenameInTempFolder("exported.sqlite")
        if  filename != "":    
            def _addToProject():        
                self.element.repo.exportsl(str(self.element), unicode(filename))                
            explorer.run(_addToProject, "Add Geogit tree to QGIS project", [])
            layer = QgsVectorLayer(filename, self.element.path, "ogr")   
            QgsMapLayerRegistry.instance().addMapLayers([layer])
            explorer.updateQgisContent()
    
def openBrowser(explorer, worktree, repo, commit):
    dlg = RepoExplorer(explorer, worktree, repo, commit)
    dlg.exec_()
    