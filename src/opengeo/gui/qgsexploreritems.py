import os
from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import *
from opengeo.gui.exploreritems import TreeItem
from opengeo.qgis import layers as qgislayers
from dialogs.styledialog import PublishStyleDialog
from opengeo.qgis.catalog import OGCatalog
from opengeo.gui.catalogselector import selectCatalog
from dialogs.layerdialog import PublishLayersDialog, PublishLayerDialog
from dialogs.projectdialog import PublishProjectDialog
                
class QgsProjectItem(TreeItem): 
    def __init__(self): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/qgis.png")
        TreeItem.__init__(self, None, icon, "QGIS project")        
                 
    def populate(self):                    
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/layer.png")
        layersItem = TreeItem(None, icon, "QGIS Layers")        
        layersItem.setIcon(0, icon)
        layers = qgislayers.getAllLayers()
        for layer in layers:
            layerItem = QgsLayerItem(layer)            
            layersItem.addChild(layerItem)
        self.addChild(layersItem)
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/group.gif")
        groupsItem = TreeItem(None, icon, "QGIS Groups")        
        groups = qgislayers.getGroups()
        for group in groups:
            groupItem = QgsGroupItem(group)                                
            groupsItem.addChild(groupItem)
            groupItem.populate()
        self.addChild(groupsItem)
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/style.png")
        stylesItem = TreeItem(None, icon, "QGIS Styles")               
        stylesItem.setIcon(0, icon)
        styles = qgislayers.getVectorLayers()
        for style in styles:
            styleItem = QgsStyleItem(style)            
            stylesItem.addChild(styleItem)
        self.addChild(stylesItem)        
            
    def contextMenuActions(self, tree, explorer):
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/publish-to-geoserver.png")        
        publishProjectAction = QtGui.QAction(icon, "Publish...", explorer)
        publishProjectAction.triggered.connect(lambda: self.publishProject(tree, explorer))
        publishProjectAction.setEnabled(len(explorer.catalogs())>0)        
        return [publishProjectAction]
                       
        
    def publishProject(self, tree, explorer):        
        layers = qgislayers.getAllLayers()                
        dlg = PublishProjectDialog(explorer.catalogs())
        dlg.exec_()     
        catalog  = dlg.catalog
        if catalog is None:
            return
        workspace = dlg.workspace
        groupName = dlg.groupName
        explorer.setProgressMaximum(len(layers))
        progress = 0                    
        for layer in layers:
            explorer.setProgress(progress)            
            ogcat = OGCatalog(catalog)                 
            if not explorer.run(ogcat.publishLayer,
                     "Publish layer '" + layer.name() + "'",
                     [],
                     layer, workspace, True):
                explorer.setProgress(0)
                return
            progress += 1                
            explorer.setProgress(progress)  
        
        groups = qgislayers.getGroups()
        for group in groups:
            names = [layer.name() for layer in groups[group]] 
            layergroup = catalog.create_layergroup(group, names, names)
            explorer.run(catalog.save, "Create layer group '" + group + "'", 
                     [], layergroup)
        
        if groupName is not None:
            names = [layer.name() for layer in layers]      
            layergroup = catalog.create_layergroup(groupName, names, names)
            explorer.run(catalog.save, "Create global layer group", 
                     [], layergroup)                
        tree.findAllItems(catalog)[0].refreshContent(explorer)
        explorer.resetActivity()                                              
                    
class QgsLayerItem(TreeItem): 
    def __init__(self, layer ): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/layer.png")
        TreeItem.__init__(self, layer, icon)   
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)      
     
    def contextMenuActions(self, tree, explorer):
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/publish-to-geoserver.png")
        publishLayerAction = QtGui.QAction(icon, "Publish to GeoServer...", explorer)
        publishLayerAction.triggered.connect(lambda: self.publishLayer(tree, explorer)) 
        publishLayerAction.setEnabled(len(explorer.catalogs())>0)    
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/create-store-from-layer.png")   
        createStoreFromLayerAction= QtGui.QAction("Create store from layer...", explorer)
        createStoreFromLayerAction.triggered.connect(lambda: self.createStoreFromLayer(tree, explorer))
        createStoreFromLayerAction.setEnabled(len(explorer.catalogs())>0)
        importToPostGisAction = QtGui.QAction(None, "import into PostGIS...", explorer)
        importToPostGisAction.triggered.connect(lambda: self.importToPostGis(tree, explorer))
        importToPostGisAction.setEnabled(len(explorer.pgDatabases())>0)
        
        return [publishLayerAction, createStoreFromLayerAction, importToPostGisAction]   
    
    def multipleSelectionContextMenuActions(self, tree, explorer, selected):        
        publishLayersAction = QtGui.QAction("Publish to GeoServer...", explorer)
        publishLayersAction.triggered.connect(lambda: self.publishLayers(tree, explorer, selected))
        publishLayersAction.setEnabled(len(explorer.catalogs())>0)        
        createStoresFromLayersAction= QtGui.QAction("Create stores from layers...", explorer)
        createStoresFromLayersAction.triggered.connect(lambda: self.createStoresFromLayers(tree, explorer, selected))
        importToPostGisAction = QtGui.QAction(None, "Import into PostGIS...", explorer)
        importToPostGisAction.triggered.connect(lambda: self.importLayersToPostGis(tree, explorer, selected))
        importToPostGisAction.setEnabled(len(explorer.pgDatabases())>0)  
        return [publishLayersAction, createStoresFromLayersAction, importToPostGisAction] 
    
    def publishLayers(self, tree, explorer, selected):        
        layers = [item.element for item in selected]        
        dlg = PublishLayersDialog(explorer.catalogs(), layers)
        dlg.exec_()     
        toPublish  = dlg.topublish
        if toPublish is None:
            return
        explorer.setProgressMaximum(len(toPublish))
        progress = 0        
        toUpdate = set();
        for layer, catalog, workspace in toPublish:
            explorer.setProgress(progress)            
            ogcat = OGCatalog(catalog)                 
            explorer.run(ogcat.publishLayer,
                     "Publish layer '" + layer.name() + "'",
                     [],
                     layer, workspace, True)
            progress += 1
            toUpdate.add(tree.findAllItems(catalog)[0])
            explorer.setProgress(progress)
        
        for item in toUpdate:
            item.refreshContent(explorer)
        explorer.resetActivity()    
                           

    def importLayerToPostGis(self, tree, explorer):
        self.importLayersToPostGis(tree, explorer, [self])
        
    
    def importLayersToPostGis(self, tree, explorer, selected):    
        
        
    def createStoresFromLayers(self, tree, explorer, selected):        
        layers = [item.element for item in selected]        
        dlg = PublishLayersDialog(explorer.catalogs(), layers)
        dlg.exec_()     
        toPublish  = dlg.topublish
        if toPublish is None:
            return
        explorer.setProgressMaximum(len(toPublish))
        progress = 0        
        toUpdate = set();
        for layer, catalog, workspace in toPublish:
            explorer.setProgress(progress)            
            ogcat = OGCatalog(catalog)                 
            explorer.run(ogcat.createStore,
                     "Create store from layer '" + layer.name() + "'",
                     [],
                     layer, workspace, True)
            progress += 1
            toUpdate.add(tree.findAllItems(catalog))
            explorer.setProgress(progress)
        
        for item in toUpdate:
            item.refreshContent(explorer)
        explorer.resetActivity()
        
    def createStoreFromLayer(self, tree, explorer):
        dlg = PublishLayerDialog(explorer.catalogs())
        dlg.exec_()      
        if dlg.catalog is None:
            return
        cat = dlg.catalog  
        ogcat = OGCatalog(cat)
        catItem = tree.findAllItems(cat)[0]
        toUpdate = [catItem]                    
        explorer.run(ogcat.createStore,
                 "Create store from layer '" + self.element.name() + "'",
                 toUpdate,
                 self.element, dlg.workspace, True)
                    
    def publishLayer(self, tree, explorer):
        dlg = PublishLayerDialog(explorer.catalogs())
        dlg.exec_()      
        if dlg.catalog is None:
            return
        cat = dlg.catalog  
        ogcat = OGCatalog(cat)
        catItem = tree.findAllItems(cat)[0]
        toUpdate = [catItem]                    
        explorer.run(ogcat.publishLayer,
                 "Publish layer '" + self.element.name() + "'",
                 toUpdate,
                 self.element, dlg.workspace, True)

             
class QgsGroupItem(TreeItem): 
    def __init__(self, group): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/group.gif")
        TreeItem.__init__(self, group , icon)   
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)
        
    def populate(self):            
        grouplayers = qgislayers.getGroups()[self.element]
        for layer in grouplayers:
            layerItem = QgsLayerItem(layer)                                
            self.addChild(layerItem)

    def contextMenuActions(self, tree, explorer): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/publish-to-geoserver.png")                
        publishGroupAction = QtGui.QAction(icon, "Publish...", explorer)
        publishGroupAction.triggered.connect(lambda: self.publishGroup(tree, explorer))
        publishGroupAction.setEnabled(len(explorer.catalogs())>0)
        return[publishGroupAction]  
        
    def publishGroup(self, tree, explorer):
        groupname = self.element
        groups = qgislayers.getGroups()   
        group = groups[groupname]     
        cat = selectCatalog(explorer.catalogs())
        if cat is None:
            return                            
        gslayers= [layer.name for layer in cat.get_layers()]
        missing = []         
        for layer in group:            
            if layer.name() not in gslayers:
                missing.append(layer) 
        toUpdate = set();
        toUpdate.add(tree.findAllItems(cat)[0])
        if missing:
            catalogs = {k :v for k, v in explorer.catalogs().iteritems() if v == cat}
            dlg = PublishLayersDialog(catalogs, missing)
            dlg.exec_()     
            toPublish  = dlg.topublish
            if toPublish is None:
                return
            explorer.setProgressMaximum(len(toPublish))
            progress = 0                    
            for layer, catalog, workspace in toPublish:
                explorer.setProgress(progress)            
                ogcat = OGCatalog(catalog)                 
                if not explorer.run(ogcat.publishLayer,
                         "Publish layer '" + layer.name() + "'",
                         [],
                         layer, workspace, True):
                    explorer.setProgress(0)
                    return
                progress += 1                
                explorer.setProgress(progress)  
        names = [layer.name() for layer in group]      
        layergroup = cat.create_layergroup(groupname, names, names)
        explorer.run(cat.save, "Create layer group from group '" + groupname + "'", 
                 [], layergroup)        
        for item in toUpdate:
            item.refreshContent(explorer)
        explorer.resetActivity()                     
               
class QgsStyleItem(TreeItem): 
    def __init__(self, layer): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/style.png")
        TreeItem.__init__(self, layer, icon, "Style of layer '" + layer.name() + "'") 
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)
        
    def contextMenuActions(self, tree, explorer):
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/publish-to-geoserver.png")
        publishStyleAction = QtGui.QAction(icon, "Publish...", explorer)
        publishStyleAction.triggered.connect(lambda: self.publishStyle(tree, explorer))
        publishStyleAction.setEnabled(len(explorer.catalogs()) > 0)
        return [publishStyleAction]    
        
    def publishStyle(self, tree, explorer):
        dlg = PublishStyleDialog(explorer.catalogs().keys())
        dlg.exec_()      
        if dlg.catalog is None:
            return
        cat = explorer.catalogs()[dlg.catalog]  
        ogcat = OGCatalog(cat)
        catItem = tree.findAllItems(cat)[0]
        toUpdate = [catItem.stylesItem]                        
        explorer.run(ogcat.publishStyle,
                 "Publish style from layer '" + self.element.name() + "'",
                 toUpdate,
                 self.element, True, dlg.name)              