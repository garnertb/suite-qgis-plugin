from PyQt4.QtCore import *
from qgis.core import *
from opengeo.gui.gsexploreritems import *
from opengeo.gui.qgsexploreritems import *
from opengeo.postgis.connection import PgConnection
from opengeo.qgis import utils


class ExplorerTreeWidget(QtGui.QTreeWidget):

    pgIcon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/pg.png")
    
    def __init__(self, explorer):         
        self.explorer = explorer
        QtGui.QTreeWidget.__init__(self, None) 
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)                    
        self.setColumnCount(1)            
        self.header().hide()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showTreePopupMenu)
        self.itemClicked.connect(self.treeItemClicked) 
        self.setDragDropMode(QtGui.QTreeWidget.DragDrop)                
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.catalogs = {}
        self.qgsItem = None
        self.fillTree()
        
    def fillTree(self):
        self.addGeoServerCatalogs()
        #self.addPostGisConnections()
        self.addQGisProject()
        
    def updateContent(self):
        if self.qgisItem is not None:
            self.qgisItem.refreshContent()
        
    def addGeoServerCatalogs(self):
        self.gsItem = GsCatalogsItem()                
        self.gsItem.populate()
        self.addTopLevelItem(self.gsItem) 
        
    def addPostGisConnections(self):
        connectionsItem = QtGui.QTreeWidgetItem()
        connectionsItem.setText(0, "PostGIS connections")
        connectionsItem.setIcon(0, self.pgIcon)
        settings = QSettings()
        settings.beginGroup(u'/PostgreSQL/connections')
        for name in settings.childGroups():
            settings.beginGroup(name)                
            conn = PgConnection(name, settings.value('host'), settings.value('port'), 
                                settings.value('database'), settings.value('username'), 
                                settings.value('password'))     
            item = PgConnectionItem(conn)            
            connectionsItem.addChild(item)
        settings.endGroup()            
        self.addTopLevelItem(connectionsItem)        
           
        
    def addQGisProject(self):        
        self.qgisItem = QgsProjectItem()                
        self.qgisItem.populate()
        self.addTopLevelItem(self.qgisItem)        
        
    def getSelectionTypes(self):
        items = self.selectedItems()
        return set([type(item) for item in items])  

    def treeItemClicked(self, item, column):        
        if hasattr(item, 'descriptionWidget'):
            widget = item.descriptionWidget()
            if widget is not None:
                self.explorer.setDescriptionWidget(widget) 
        
    def showTreePopupMenu(self,point):
        allTypes = self.getSelectionTypes()                
        if len(allTypes) != 1:
            return 
        items = self.selectedItems()
        if len(items) > 1:
            self.showMultipleSelectionPopupMenu(point)
        else:
            self.showSingleSelectionPopupMenu(point)
                
    def getDefaultWorkspace(self, catalog):                            
        workspaces = catalog.get_workspaces()
        if workspaces:
            return catalog.get_default_workspace()
        else:
            return None
                        
    def showMultipleSelectionPopupMenu(self, point):        
        self.currentItem = self.itemAt(point)  
        point = self.mapToGlobal(point)        
        menu = QtGui.QMenu()
        actions = self.currentItem.multipleSelectionContextMenuActions(self.explorer, self.selectedItems())
        for action in actions:
            menu.addAction(action)            
        menu.exec_(point)             
                                            
                
    def showSingleSelectionPopupMenu(self, point):                
        self.currentItem = self.itemAt(point)
        if not isinstance(self.currentItem, TreeItem):
            return 
                 
        menu = QtGui.QMenu()
        if (isinstance(self.currentItem, TreeItem) and hasattr(self.currentItem, 'populate')):            
            refreshAction = QtGui.QAction("Refresh", None)
            refreshAction.triggered.connect(self.currentItem.refreshContent)
            menu.addAction(refreshAction) 
        point = self.mapToGlobal(point)    
        actions = self.currentItem.contextMenuActions(self.explorer)
        for action in actions:
            menu.addAction(action)            
        menu.exec_(point)

        #=======================================================================
        # elif isinstance(self.currentItem, PgTableItem):        
        #    publishPgTableAction = QtGui.QAction("Publish...", None)
        #    publishPgTableAction.triggered.connect(self.publishPgTable)
        #    menu.addAction(publishPgTableAction)
        # elif isinstance(self.currentItem, PgSchemaItem):        
        #    publishPgSchemaAction = QtGui.QAction("Publish all tables...", None)
        #    publishPgSchemaAction.triggered.connect(self.publishPgSchema)
        #    menu.addAction(publishPgSchemaAction)       
        #=======================================================================

    def findAllItems(self, element):
        allItems = []
        iterator = QtGui.QTreeWidgetItemIterator(self)
        value = iterator.value()
        while value:
            if hasattr(value, 'element'):
                if hasattr(value.element, 'name') and hasattr(element, 'name'):
                    if  value.element.name == element.name and value.element.__class__ == element.__class__:
                        allItems.append(value)
                elif value.element == element:
                    allItems.append(value)                
            iterator += 1
            value = iterator.value()
        return allItems      
                     


    def publishPgTable(self, catalog = None, workspace = None):
        if catalog is None:
            pass        
        table = self.currentItem.element
        connection = table.connection
        catalog.create_pg_featurestore(connection,                                           
                                           workspace = connection.workspace,
                                           overwrite = True,
                                           host = connection.host,
                                           database = connection.database,
                                           schema = table.schema,
                                           port = connection.port(),
                                           user = connection.username(),
                                           passwd = connection.password())  
        catalog.create_pg_featuretype(table.name, table.name, workspace)
         

                    
###################################DRAG & DROP########################    
    
    QGIS_URI_MIME = "application/x-vnd.qgis.qgis.uri"

    def mimeTypes(self):
        return ["text/uri-list", self.QGIS_URI_MIME]
    
    def mimeData(self, items):
        mimeData = QMimeData()
        encodedData = QByteArray()
        stream = QDataStream(encodedData, QIODevice.WriteOnly)

        for item in items:
            if isinstance(item, GsLayerItem):                
                layer = item.element
                uri = utils.mimeUri(layer)
                print uri
                stream.writeQString(uri)

        mimeData.setData(self.QGIS_URI_MIME, encodedData)        
        return mimeData
        
    def dropEvent(self, event):
        destinationItem=self.itemAt(event.pos())
        draggedTypes = {item.__class__ for item in self.selectedItems()}
        if len(draggedTypes) > 1:
            return
        draggedType = draggedTypes.pop()
        print "Dragging objects of type '" + str(draggedType) +"' into object of type '" + str(destinationItem.__class__) + "'"
        
        selected = self.selectedItems()
        self.explorer.progress.setMaximum(len(selected))
        i = 0
        toUpdate = set()
        for item in selected:  
            toUpdate.extend(destinationItem.acceptDroppedItem(self.explorer))
                      
            if isinstance(item, QgsLayerItem):
                if isinstance(destinationItem, GsWorkspaceItem):
                    self.publishDraggedLayer(item.element, destinationItem.element)
                    toUpdate.add(self.findAllItems(destinationItem.element.catalog)[0])
                elif isinstance(destinationItem, (GsResourceItem, GsStoreItem)):
                    self.publishDraggedLayer(item.element, destinationItem.element.workspace)
                    toUpdate.add(self.findAllItems(destinationItem.element.catalog)[0])
                elif isinstance(destinationItem, (GsWorkspacesItem, GsLayersItem, GsLayerItem, GsCatalogItem)):
                    catalog = destinationItem.parentCatalog()
                    workspace = self.getDefaultWorkspace(catalog)
                    if workspace is not None:
                        self.publishDraggedLayer(item.element, workspace)
                        toUpdate.add(self.findAllItems(catalog)[0])                    
            if isinstance(item, QgsGroupItem):                
                catalog = destinationItem.parentCatalog()
                if catalog is None:
                    return
                workspace = destinationItem.parentWorkspace()
                if workspace is None:
                    workspace = self.getDefaultWorkspace(catalog)
                self.publishDraggedGroup(item, catalog, workspace)
                toUpdate.add(self.findAllItems(catalog)[0])                                                  
            elif isinstance(item, GsLayerItem): 
                if isinstance(destinationItem, GwcLayersItem):
                    self.createGwcLayer(item.element)
                    toUpdate.add(destinationItem)
                elif isinstance(destinationItem, GsGroupItem):
                    self.addDraggedLayerToGroup(item.element, destinationItem)
                    toUpdate.add(destinationItem)                            
                elif isinstance(destinationItem, GsLayerItem):
                    if isinstance(destinationItem.parent(), GsGroupItem):
                        destinationItem = destinationItem.parent()
                        self.addDraggedLayerToGroup(item.element, destinationItem)
                        toUpdate.add(destinationItem)
            elif isinstance(item, (GsStyleItem,QgsStyleItem)):
                if isinstance(destinationItem, GsLayerItem):                                            
                    self.addDraggedStyleToLayer(item, destinationItem)
                    toUpdate.add(destinationItem)                
                elif isinstance(destinationItem, GsStyleItem):
                    if isinstance(destinationItem.parent(), GsLayerItem):
                        destinationItem = destinationItem.parent()
                        self.addDraggedStyleToLayer(item, destinationItem)
                        toUpdate.add(destinationItem)
                    elif isinstance(destinationItem.parent(), GsStylesItem) and isinstance(item, QgsStyleItem):
                        self.publishDraggedStyle(item.element.name(), destinationItem.parent())                                                   
                elif isinstance(destinationItem, GsCatalogItem) and isinstance(item, QgsStyleItem):                    
                    self.publishDraggedStyle(item.element.name(), destinationItem)                           
            else:
                continue                                        
            i += 1
            self.explorer.progress.setValue(i)
        
        for item in toUpdate:
            item.refreshContent()        
        self.explorer.progress.setValue(0)
        event.acceptProposedAction()
        

    def createGwcLayer(self, layer):                
        dlg = EditGwcLayerDialog([layer], None)
        dlg.exec_()        
        if dlg.gridsets is not None:
            gwc = Gwc(layer.catalog)
            
            #TODO: this is a hack that assumes the layer belong to the same workspace
            typename = layer.resource.workspace.name + ":" + layer.name
            
            gwclayer= GwcLayer(gwc, typename, dlg.formats, dlg.gridsets, dlg.metaWidth, dlg.metaHeight)
            self.explorer.run(gwc.addLayer,
                              "GWC layer '" + layer.name + "' correctly created",
                              [],
                              gwclayer)        
                    
    def publishDraggedGroup(self, groupItem, catalog, workspace):        
        groupName = groupItem.element
        groups = qgislayers.getGroups()   
        group = groups[groupName]           
        gslayers= [layer.name for layer in catalog.get_layers()]
        missing = []         
        for layer in group:            
            if layer.name() not in gslayers:
                missing.append(layer)         
        if missing:
            self.explorer.progress.setMaximum(len(missing))
            progress = 0
            ogcat = OGCatalog(catalog)                  
            for layer in missing:
                self.explorer.progress.setValue(progress)                                           
                self.explorer.run(ogcat.publishLayer,
                         "Layer correctly published from layer '" + layer.name() + "'",
                         [],
                         layer, workspace, True)
                progress += 1                                                            
            self.explorer.progress.setValue(progress)  
        names = [layer.name() for layer in group]      
        layergroup = catalog.create_layergroup(groupName, names, names)
        self.explorer.run(catalog.save, "Layer group correctly created from group '" + groupName + "'", 
                 [], layergroup)               
        
    def publishDraggedStyle(self, layerName, catalogItem):
        ogcat = OGCatalog(catalogItem.element)
        toUpdate = []
        for idx in range(catalogItem.childCount()):
            subitem = catalogItem.child(idx)
            if isinstance(subitem, GsStylesItem):
                toUpdate.append(subitem)
                break                
        self.explorer.run(ogcat.publishStyle,
                 "Style correctly published from layer '" + layerName + "'",
                 toUpdate,
                 layerName, True, layerName)

        
    def addDraggedLayerToGroup(self, layer, groupItem):
        print "adding"
        group = groupItem.element
        styles = group.styles
        layers = group.layers
        if layer.name not in layers:
            layers.append(layer.name)
            styles.append(layer.default_style.name)
        group.dirty.update(layers = layers, styles = styles)
        self.explorer.run(layer.catalog.save,
                     "Group '" + group.name + "' correctly updated",
                     [groupItem],
                     group)
        
    def addDraggedStyleToLayer(self, styleItem, layerItem):
        catalog = layerItem.element.catalog  
        if isinstance(styleItem, QgsStyleItem):
            styleName = styleItem.element.name()
                       
            catalogItem = self.findAllItems(catalog)[0]
            self.publishStyle(styleName, catalogItem)     
            style = catalog.get_style(styleName)
        else:         
            style = styleItem.element            
        layer = layerItem.element
        styles = layer.styles                            
        styles.append(style)
        layer.styles = styles                        
        self.explorer.run(catalog.save, 
                 "Style '" + style.name + "' correctly added to layer '" + layer.name + "'",
                 [layerItem],
                 layer)                      
            



                 
