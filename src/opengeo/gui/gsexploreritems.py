import os
from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import *
from opengeo.core import util
from opengeo.core.store import DataStore
from opengeo.core.resource import Coverage, FeatureType
from opengeo.geoserver.gwc import Gwc, GwcLayer
from opengeo.gui.catalogdialog import DefineCatalogDialog
from opengeo.core.style import Style
from opengeo.core.layer import Layer
from opengeo.gui.styledialog import AddStyleToLayerDialog, StyleFromLayerDialog
from opengeo.qgis.catalog import OGCatalog
from opengeo.gui.exploreritems import TreeItem
from opengeo.gui.groupdialog import LayerGroupDialog
from opengeo.gui.workspacedialog import DefineWorkspaceDialog
from opengeo.gui.gwclayer import SeedGwcLayerDialog, EditGwcLayerDialog
from opengeo.core.layergroup import UnsavedLayerGroup

class GsTreeItem(TreeItem):
    
    def parentCatalog(self):        
        item  = self            
        while item is not None:                    
            if isinstance(item, GsCatalogItem):
                return item.element                           
            item = item.parent()            
        return None   
    
    def catalogs(self):
        item  = self            
        while item is not None:                    
            if isinstance(item, GsCatalogsItem):
                return item._catalogs                           
            item = item.parent()            
        return None
    
    def parentWorkspace(self):        
        item  = self            
        while item is not None:                    
            if isinstance(item, GsWorkspaceItem):
                return item.element                           
            item = item.parent()            
        return None   
                 
    def getDefaultWorkspace(self):                            
        workspaces = self.parentCatalog().get_workspaces()
        if workspaces:
            return self.parentCatalog().get_default_workspace()
        else:
            return None  
        
    def deleteElements(self, selected):                
        elements = []
        unused = []
        for item in selected:
            elements.append(item.element)
            if isinstance(item, GsStoreItem):
                for idx in range(item.childCount()):
                    subitem = item.child(idx)
                    elements.insert(0, subitem.element)
            elif isinstance(item, GsLayerItem):
                uniqueStyles = self.uniqueStyles(item.element)
                for style in uniqueStyles:
                    if style.name == item.element.name:
                        unused.append(style)      
        toUpdate = set(item.parent() for item in selected)                
        self.explorer.progress.setMaximum(len(elements))
        progress = 0        
        dependent = self.getDependentElements(elements)
                
        if dependent:
            msg = "The following elements depend on the elements to delete\nand will be deleted as well:\n\n"
            for e in dependent:
                msg += "-" + e.name + "(" + e.__class__.__name__ + ")\n\n"
            msg += "Do you really want to delete all these elements?"                   
            reply = QtGui.QMessageBox.question(None, "Delete confirmation",
                                               msg, QtGui.QMessageBox.Yes | 
                                               QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                return
            toDelete = set()
            for e in dependent:                
                items = self.explorer.tree.findAllItems(e);                
                toUpdate.update(set(item.parent() for item in items))
                toDelete.update(items)
            toUpdate = toUpdate - toDelete
        
                
        unusedToUpdate = set() 
        for e in unused:                
            items = self.explorer.tree.findAllItems(e); 
            unusedToUpdate.add(item.parent())                       
        toUpdate.update(unusedToUpdate)
        
        elements[0:0] = dependent 
        elements.extend(unused)      
        for element in elements:
            self.explorer.progress.setValue(progress)    
            if isinstance(element, GwcLayer):
                self.explorer.run(element.delete,
                     element.__class__.__name__ + " '" + element.name + "' correctly deleted",
                     [])                      
            else:                                     
                self.explorer.run(element.catalog.delete,
                     element.__class__.__name__ + " '" + element.name + "' correctly deleted",
                     [], 
                     element, isinstance(element, Style))  
            progress += 1
        self.explorer.progress.setValue(progress)
        for item in toUpdate:
            item.refreshContent()
        self.explorer.progress.setValue(0)
    
    def uniqueStyles(self, layer):
        '''returns the styles used by a layer that are not used by any other layer'''
        unique = []
        allUsedStyles = set()
        catalog = layer.catalog
        layers = catalog.get_layers()
        for lyr in layers:
            if lyr.name == layer.name:
                continue
            for style in lyr.styles:
                allUsedStyles.add(style.name)
            allUsedStyles.add(lyr.default_style.name)
        for style in layer.styles:
            if style.name not in allUsedStyles:
                unique.append(style)
        if layer.default_style not in allUsedStyles:
            unique.append(layer.default_style)
        return unique
            
    def getDependentElements(self, elements):
        dependent = []
        for element in elements:
            if isinstance(element, Layer):
                groups = element.catalog.get_layergroups()
                for group in groups:                    
                    for layer in group.layers:
                        if layer == element.name:
                            dependent.append(group)
                            break                    
            elif isinstance(element, (FeatureType, Coverage)):
                layers = element.catalog.get_layers()
                for layer in layers:
                    if layer.resource.name == element.name:
                        dependent.append(layer)     
            elif isinstance(element, Style):
                layers = element.catalog.get_layers()                
                for layer in layers:
                    if layer.default_style.name == element.name:
                        dependent.append(layer)                         
                    else:
                        for style in layer.styles:                            
                            if style.name == element.name:
                                dependent.append(layer)
                                break
                                                                                    
        if dependent:
            subdependent = self.getDependentElements(dependent)
            if subdependent:
                dependent[0:0] = subdependent
        return dependent
                                     
    
class GsCatalogsItem(GsTreeItem):    
    def __init__(self): 
        self._catalogs = {}
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/geoserver.png")        
        GsTreeItem.__init__(self, None, icon, "GeoServer catalogs")        
                 
    def populate(self):
        for name, catalog in self._catalogs.iteritems():                    
            item = self.getGeoServerCatalogItem(catalog, name)
            self.addChild(item)

    def contextMenuActions(self, explorer):
        self.explorer = explorer
        createCatalogAction = QtGui.QAction("New catalog...", None)
        createCatalogAction.triggered.connect(self.addGeoServerCatalog)
        return [createCatalogAction]
                    
    def addGeoServerCatalog(self):         
        dlg = DefineCatalogDialog()
        dlg.exec_()
        cat = dlg.getCatalog()        
        if cat is not None:   
            name = dlg.getName()
            i = 2
            while name in self._catalogs.keys():
                name = dlg.getName() + "_" + str(i)
                i += 1                                 
            item = self.getGeoServerCatalogItem(cat, name)
            if item is not None:
                self._catalogs[name] = cat
                self.addChild(item)
        
        
    def getGeoServerCatalogItem(self, cat, name):    
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))
        try:    
            geoserverItem = GsCatalogItem(cat, name)
            geoserverItem.populate()
            QtGui.QApplication.restoreOverrideCursor()
            self.explorer.setInfo("Catalog '" + name + "' correctly created")
            return geoserverItem
        except Exception, e:            
            QtGui.QApplication.restoreOverrideCursor()
            self.explorer.setInfo("Could not create catalog:" + str(e), True)   
     
            
class GsLayersItem(GsTreeItem): 
    def __init__(self): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/layer.png")
        GsTreeItem.__init__(self, None, icon, "Layers")
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled) 
            
    def populate(self):
        layers = self.parentCatalog().get_layers()
        for layer in layers:
            layerItem = GsLayerItem(layer)            
            layerItem.populate()    
            self.addChild(layerItem)       
                
class GsGroupsItem(GsTreeItem): 
    def __init__(self): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/group.gif")
        GsTreeItem.__init__(self, None, icon, "Groups")
           
        
    def populate(self):
        groups = self.parentCatalog().get_layergroups()
        for group in groups:
            groupItem = GsGroupItem(group)
            groupItem.populate()                                
            self.addChild(groupItem)         

    def acceptDroppedItem(self, explorer, item):
        catalog = self.parentCatalog()
        workspace = self.getDefaultWorkspace(catalog)
        toUpdate = []
        if workspace is not None:
            self.publishDraggedLayer(item.element, workspace)
            toUpdate.append(explorer.tree.findAllItems(catalog)[0])  
        return toUpdate  
    
    def contextMenuActions(self, explorer):
        self.explorer = explorer                
        createGroupAction = QtGui.QAction("New group...", None)
        createGroupAction.triggered.connect(self.createGroup)
        return [createGroupAction]
    
    def createGroup(self):
        dlg = LayerGroupDialog(self.parentCatalog())
        dlg.exec_()
        group = dlg.group
        if group is not None:
            self.explorer.run(self.parentCatalog().save,
                     "Group '" + group.name + "' correctly created",
                     [self],
                     group)
     
        
class GsWorkspacesItem(GsTreeItem): 
    def __init__(self): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/workspace.png")
        GsTreeItem.__init__(self, None, icon, "Workspaces")  
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)        
    
    def populate(self):
        cat = self.parentCatalog()
        try:
            defaultWorkspace = cat.get_default_workspace()
            defaultWorkspace.fetch()
            defaultName = defaultWorkspace.dom.find('name').text
        except:
            defaultName = None             
        workspaces = cat.get_workspaces()
        for workspace in workspaces:
            workspaceItem = GsWorkspaceItem(workspace, workspace.name == defaultName)
            workspaceItem.populate()
            self.addChild(workspaceItem) 
    
    def acceptDroppedItem(self, explorer, item):
        catalog = self.parentCatalog()
        workspace = self.getDefaultWorkspace(catalog)
        toUpdate = []
        if workspace is not None:
            self.publishDraggedLayer(item.element, workspace)
            toUpdate.append(explorer.tree.findAllItems(catalog)[0])  
        return toUpdate                        
                            
    def contextMenuActions(self, explorer):
        self.explorer = explorer
        createWorkspaceAction = QtGui.QAction("New workspace...", None)
        createWorkspaceAction.triggered.connect(self.createWorkspace)
        return [createWorkspaceAction]
    
    def createWorkspace(self):
        dlg = DefineWorkspaceDialog() 
        dlg.exec_()            
        if dlg.name is not None:
            self.explorer.run(self.parentCatalog().create_workspace, 
                    "Workspace '" + dlg.name + "' correctly created",
                    [self],
                    dlg.name, dlg.uri)
                 
class GsStylesItem(GsTreeItem): 
    def __init__(self ): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/style.png")
        GsTreeItem.__init__(self, None, icon, "Styles")
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled) 
                    
    def populate(self):
        styles = self.parentCatalog().get_styles()
        for style in styles:
            styleItem = GsStyleItem(style, False)                
            self.addChild(styleItem)

    def acceptDroppedItem(self, explorer, item):
        catalog = self.parentCatalog()
        workspace = self.getDefaultWorkspace(catalog)
        toUpdate = []
        if workspace is not None:
            self.publishDraggedLayer(item.element, workspace)
            toUpdate.append(explorer.tree.findAllItems(catalog)[0])  
        return toUpdate  
        
    def contextMenuActions(self, explorer):
        self.explorer = explorer
        createStyleFromLayerAction = QtGui.QAction("New style from QGIS layer...", None)
        createStyleFromLayerAction.triggered.connect(self.createStyleFromLayer)
        return [createStyleFromLayerAction] 
           
    
    def createStyleFromLayer(self):  
        dlg = StyleFromLayerDialog(self.catalogs().keys())
        dlg.exec_()      
        if dlg.layer is not None:
            ogcat = OGCatalog(self.catalogs()[dlg.catalog])        
            self.explorer.run(ogcat.publish_style, 
                     "Style correctly created from layer '" + dlg.layer + "'",
                     [self],
                     dlg.layer, dlg.name, True)


class GsCatalogItem(GsTreeItem): 
    def __init__(self, catalog, name): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/geoserver.png")
        GsTreeItem.__init__(self, catalog, icon, name) 
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled) 
        
    def populate(self):        
        self.workspacesItem = GsWorkspacesItem()                              
        self.addChild(self.workspacesItem)  
        self.workspacesItem.populate()
        self.layersItem = GsLayersItem()                                      
        self.addChild(self.layersItem)
        self.layersItem.populate()
        self.groupsItem = GsGroupsItem()                                    
        self.addChild(self.groupsItem)
        self.groupsItem.populate()
        self.stylesItem = GsStylesItem()                        
        self.addChild(self.stylesItem)
        self.stylesItem.populate()      
        self.gwcItem = GwcLayersItem()                        
        self.addChild(self.gwcItem)
        self.gwcItem.populate()

    def contextMenuActions(self, explorer):
        self.explorer = explorer
        removeCatalogAction = QtGui.QAction("Remove", None)
        removeCatalogAction.triggered.connect(self.removeCatalog)
        return[removeCatalogAction] 
        
    def removeCatalog(self):
        del self.catalogs()[self.text(0)]
        parent = self.parent()        
        parent.takeChild(parent.indexOfChild(self))   
        
           
                        
                                
class GsLayerItem(GsTreeItem): 
    def __init__(self, layer): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/layer.png")
        GsTreeItem.__init__(self, layer, icon)  
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable 
                      | QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsDragEnabled)       
        
    def populate(self):
        layer = self.element
        for style in layer.styles:
            styleItem = GsStyleItem(style, False)
            self.addChild(styleItem)
        if layer.default_style is not None:
            styleItem = GsStyleItem(layer.default_style, True)                    
            self.addChild(styleItem)  
            
    def acceptDroppedItem(self, explorer, item):
        catalog = self.parentCatalog()
        workspace = self.getDefaultWorkspace(catalog)
        toUpdate = []
        if workspace is not None:
            self.publishDraggedLayer(item.element, workspace)
            toUpdate.append(explorer.tree.findAllItems(catalog)[0])  
        return toUpdate  
                
    def contextMenuActions(self, explorer):
        self.explorer = explorer
        actions = []
        if isinstance(self.parent(), GsGroupItem):
            layers = self.parent().element.layers
            count = len(layers)
            idx = layers.index(self.element.name)
            removeLayerFromGroupAction = QtGui.QAction("Remove layer from group", None)            
            removeLayerFromGroupAction.setEnabled(count > 1)
            removeLayerFromGroupAction.triggered.connect(self.removeLayerFromGroup)
            actions.append(removeLayerFromGroupAction)                                                
            moveLayerUpInGroupAction = QtGui.QAction("Move up", None)            
            moveLayerUpInGroupAction.setEnabled(count > 1 and idx > 0)
            moveLayerUpInGroupAction.triggered.connect(self.moveLayerUpInGroup)
            actions.append(moveLayerUpInGroupAction)
            moveLayerDownInGroupAction = QtGui.QAction("Move down", None)            
            moveLayerDownInGroupAction.setEnabled(count > 1 and idx < count - 1)
            moveLayerDownInGroupAction.triggered.connect(self.moveLayerDownInGroup)
            actions.append(moveLayerDownInGroupAction)
            moveLayerToFrontInGroupAction = QtGui.QAction("Move to front", None)            
            moveLayerToFrontInGroupAction.setEnabled(count > 1 and idx > 0)
            moveLayerToFrontInGroupAction.triggered.connect(self.moveLayerToFrontInGroup)
            actions.append(moveLayerToFrontInGroupAction)
            moveLayerToBackInGroupAction = QtGui.QAction("Move to back", None)            
            moveLayerToBackInGroupAction.setEnabled(count > 1 and idx < count - 1)
            moveLayerToBackInGroupAction.triggered.connect(self.moveLayerToBackInGroup)
            actions.append(moveLayerToBackInGroupAction)
        else:
            addStyleToLayerAction = QtGui.QAction("Add style to layer...", None)
            addStyleToLayerAction.triggered.connect(self.addStyleToLayer)                    
            actions.append(addStyleToLayerAction)   
            deleteLayerAction = QtGui.QAction("Delete", None)
            deleteLayerAction.triggered.connect(self.deleteLayer)
            actions.append(deleteLayerAction)                                
            addLayerAction = QtGui.QAction("Add to current QGIS project", None)
            addLayerAction.triggered.connect(self.addLayerToProject)
            actions.append(addLayerAction)    
            
        return actions
    
    def multipleSelectionContextMenuActions(self, explorer, selected):
        self.explorer = explorer
        deleteSelectedAction = QtGui.QAction("Delete", None)
        deleteSelectedAction.triggered.connect(lambda: self.deleteElements(selected))
        createGroupAction = QtGui.QAction("Create group...", None)
        createGroupAction.triggered.connect(lambda: self.createGroupFromLayers(selected))        
        return [deleteSelectedAction, createGroupAction]
                 
            
    def createGroupFromLayers(self):        
        name, ok = QtGui.QInputDialog.getText(None, "Group name", "Enter the name of the group to create")        
        if not ok:
            return
        catalog = self.element.catalog
        catalogItem = self.explorer.tree.findAllItems(catalog)[0]
        groupsItem = catalogItem.groupsItem
        layers = [item.element for item in self.selectedItems()]
        styles = [layer.default_style.name for layer in layers]
        layerNames = [layer.name for layer in layers]
        #TODO calculate bounds
        bbox = None
        group =  UnsavedLayerGroup(catalog, name, layerNames, styles, bbox)
                
        self.explorer.run(self.parentCatalog().save,
                     "Group '" + name + "' correctly created",
                     [groupsItem],
                     group)
                    
    def deleteLayer(self):
        self.deleteElements([self])
            
    def removeLayerFromGroup(self):
        group = self.parent().element
        layers = group.layers
        styles = group.styles
        idx = group.layers.index(self.element.name)
        del layers[idx]
        del styles[idx]
        group.dirty.update(layers = layers, styles = styles)
        self.explorer.run(self.parentCatalog().save, 
                 "Layer '" + self.element.name + "' correctly removed from group '" + group.name +"'",
                 [self.parent()],
                 group)

    def moveLayerDownInGroup(self):
        group = self.parent().element
        layers = group.layers
        styles = group.styles
        idx = group.layers.index(self.element.name)
        tmp = layers [idx + 1]
        layers[idx + 1] = layers[idx]
        layers[idx] = tmp  
        tmp = styles [idx + 1]
        styles[idx + 1] = styles[idx]
        styles[idx] = tmp          
        group.dirty.update(layers = layers, styles = styles)
        self.explorer.run(self.parentCatalog().save, 
                 "Layer '" + self.element.name + "' correctly moved down in group '" + group.name +"'",
                 [self.parent()],
                 group)        
    
    def moveLayerToFrontInGroup(self):
        group = self.parent().element
        layers = group.layers
        styles = group.styles
        idx = group.layers.index(self.element.name)
        tmp = layers[idx]
        del layers[idx]
        layers.insert(0, tmp)        
        tmp = styles [idx]
        del styles[idx]
        styles.insert(0, tmp)          
        group.dirty.update(layers = layers, styles = styles)
        self.explorer.run(self.parentCatalog().save, 
                 "Layer '" + self.element.name + "' correctly moved to front in group '" + group.name +"'",
                 [self.parent()],
                 group)
    
    def moveLayerToBackInGroup(self):
        group = self.parent().element
        layers = group.layers
        styles = group.styles
        idx = group.layers.index(self.element.name)
        tmp = layers[idx]
        del layers[idx]
        layers.append(tmp)        
        tmp = styles [idx]
        del styles[idx]
        styles.append(tmp)          
        group.dirty.update(layers = layers, styles = styles)
        self.explorer.run(self.parentCatalog().save, 
                 "Layer '" + self.element.name + "' correctly moved to back in group '" + group.name +"'",
                 [self.parent()],
                 group)
                     
    def moveLayerUpInGroup(self):
        group = self.parent().element
        layers = group.layers
        styles = group.styles
        idx = group.layers.index(self.element.name)
        tmp = layers [idx - 1]
        layers[idx - 1] = layers[idx]
        layers[idx] = tmp  
        tmp = styles [idx - 1]
        styles[idx - 1] = styles[idx]
        styles[idx] = tmp          
        group.dirty.update(layers = layers, styles = styles)
        self.explorer.run(self.parentCatalog().save, 
                 "Layer '" + self.element.name + "' correctly moved up in group '" + group.name +"'",
                 [self.parent()],
                 group)    
        
            
    def addStyleToLayer(self):
        cat = self.parentCatalog()
        dlg = AddStyleToLayerDialog(cat)
        dlg.exec_()
        if dlg.style is not None:
            layer = self.element
            styles = layer.styles            
            if dlg.default:
                default = layer.default_style
                styles.append(default)
                layer.styles = styles
                layer.default_style = dlg.style                 
            else:
                styles.append(dlg.style)
                layer.styles = styles 
            self.explorer.run(cat.save, 
                     "Style '" + dlg.style.name + "' correctly added to layer '" + layer.name + "'",
                     [self],
                     layer)  
            
    def addLayerToProject(self):
        #Using threads here freezes the QGIS GUI
        cat = OGCatalog(self.parentCatalog()) 
        cat.addLayerToProject(self.element.name) 
        self.explorer.setInfo("Layer '" + self.element.name + "' correctly added to QGIS project")                        

class GsGroupItem(GsTreeItem): 
    def __init__(self, group): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/group.gif")
        GsTreeItem.__init__(self, group, icon)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable 
                      | QtCore.Qt.ItemIsDropEnabled)  
        
    def populate(self):
        layers = self.element.catalog.get_layers()
        layersDict = {layer.name : layer for layer in layers}
        groupLayers = self.element.layers
        if groupLayers is None:
            return
        for layer in groupLayers:
            layerItem = GsLayerItem(layersDict[layer])                    
            self.addChild(layerItem)
            
    def contextMenuActions(self, explorer):
        explorer = explorer
        editLayerGroupAction = QtGui.QAction("Edit...", None)
        editLayerGroupAction.triggered.connect(self.editLayerGroup)             
        deleteLayerGroupAction = QtGui.QAction("Delete", None)
        deleteLayerGroupAction.triggered.connect(self.deleteLayerGroup)
        return [editLayerGroupAction, deleteLayerGroupAction]
       
    def multipleSelectionContextMenuActions(self, explorer, selected):
        self.explorer = explorer
        deleteSelectedAction = QtGui.QAction("Delete", None)
        deleteSelectedAction.triggered.connect(lambda: self.deleteElements(selected))
        return [deleteSelectedAction]
    
    def deleteLayerGroup(self):
        self.deleteElements([self]);
        
    def editLayerGroup(self):
        cat = self.parentCatalog()        
        dlg = LayerGroupDialog(cat, self.element)
        dlg.exec_()
        group = dlg.group
        if group is not None:
            self.explorer.run(cat.save, "Layer group '" + self.element.name + "' correctly edited", 
                              [self], 
                              group)   
    
                
            

class GsStyleItem(GsTreeItem): 
    def __init__(self, style, isDefault): 
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/style.png")
        name = style.name if not isDefault else style.name + " [default style]"
        GsTreeItem.__init__(self, style, icon, name)
        self.isDefault = isDefault     
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)        
        
    def contextMenuActions(self, explorer):
        self.explorer = explorer    
        actions = []
        if isinstance(self.parent(), GsLayerItem):
            setAsDefaultStyleAction = QtGui.QAction("Set as default style", None)
            setAsDefaultStyleAction.triggered.connect(self.setAsDefaultStyle)
            setAsDefaultStyleAction.setEnabled(not self.isDefault)
            actions.append(setAsDefaultStyleAction)  
            removeStyleFromLayerAction = QtGui.QAction("Remove style from layer", None)
            removeStyleFromLayerAction.triggered.connect(self.removeStyleFromLayer)
            removeStyleFromLayerAction.setEnabled(not self.isDefault)            
            actions.append(removeStyleFromLayerAction)                           
        else:                      
            deleteStyleAction = QtGui.QAction("Delete", None)
            deleteStyleAction.triggered.connect(self.deleteStyle)
            actions.append(deleteStyleAction)
        return actions 
    
    def multipleSelectionContextMenuActions(self, explorer, selected):
        self.explorer = explorer
        deleteSelectedAction = QtGui.QAction("Delete", None)
        deleteSelectedAction.triggered.connect(lambda: self.deleteElements(selected))
        return [deleteSelectedAction]
    
    def deleteStyle(self):
        self.deleteElements([self])
        
    def removeStyleFromLayer(self):
        layer = self.parent().element        
        styles = layer.styles
        styles = [style for style in styles if style.name != self.element.name]            
        layer.styles = styles 
        self.explorer.run(self.parentCatalog().save, 
                "Style '" + self.element.name + "' removed from layer '" + layer.name, 
                self.explorer.tree.findAllItems(self.parent().element),
                layer)
    
    def setAsDefaultStyle(self):
        layer = self.parent().element        
        styles = layer.styles
        styles = [style for style in styles if style.name != self.element.name]
        default = layer.default_style
        if default is not None:
            styles.append(default)
        layer.default_style = self.element
        layer.styles = styles 
        self.explorer.run(self.parentCatalog().save, 
                "Style '" + self.element.name + "' set as default style for layer '" + layer.name + "'", 
                self.explorer.tree.findAllItems(self.parent().element),
                layer)          
    
                      
class GsWorkspaceItem(GsTreeItem): 
    def __init__(self, workspace, isDefault):
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/workspace.png")                 
        self.isDefault = isDefault        
        name = workspace.name if not isDefault else workspace.name + " [default workspace]"
        GsTreeItem.__init__(self, workspace, icon, name)    
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)  
        
    def populate(self):
        stores = self.element.catalog.get_stores(self.element)
        for store in stores:
            storeItem = GsStoreItem(store)
            storeItem.populate()
            self.addChild(storeItem)         
                   
    def acceptDroppedItem(self, explorer, item):
        publishDraggedLayer(explorer, item.element, self.element)
        return explorer.tree.findAllItems(self.element.catalog)
                                     
    def contextMenuActions(self, explorer):
        self.explorer = explorer
        setAsDefaultAction = QtGui.QAction("Set as default workspace", None)
        setAsDefaultAction.triggered.connect(self.setAsDefaultWorkspace)
        setAsDefaultAction.setEnabled(not self.isDefault)                                
        deleteWorkspaceAction = QtGui.QAction("Delete", None)
        deleteWorkspaceAction.triggered.connect(self.deleteWorkspace)
        return[setAsDefaultAction, deleteWorkspaceAction]
        
    def multipleSelectionContextMenuActions(self, explorer, selected):
        self.explorer = explorer
        deleteSelectedAction = QtGui.QAction("Delete", None)
        deleteSelectedAction.triggered.connect(lambda: self.deleteElements(selected))
        return [deleteSelectedAction]
    
    def deleteWorkspace(self):
        self.deleteElements([self])
        
    def setAsDefaultWorkspace(self):
        self.explorer.run(self.parentCatalog().set_default_workspace, 
                 "Workspace '" + self.element.name + "' set as default workspace",
                 [self.parent()],
                 self.element.name)
        
                                     
class GsStoreItem(GsTreeItem): 
    def __init__(self, store):
        if isinstance(store, DataStore):
            icon = None#QtGui.QIcon(os.path.dirname(__file__) + "/../images/workspace.png")
        else:
            icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/grid.jpg")             
        GsTreeItem.__init__(self, store, icon)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)  

    def populate(self):      
        resources = self.element.get_resources()
        for resource in resources:
            resourceItem = GsResourceItem(resource)                        
            self.addChild(resourceItem)        

    def acceptDroppedItem(self, explorer, item):        
        publishDraggedLayer(explorer, item.element, self.element.workspace)
        return explorer.tree.findAllItems(self.element.catalog)
    
    def contextMenuActions(self, explorer):
        self.explorer = explorer
        deleteStoreAction = QtGui.QAction("Delete", None)
        deleteStoreAction.triggered.connect(self.deleteStore)
        return[deleteStoreAction]
                
    def multipleSelectionContextMenuActions(self, explorer, selected):
        self.explorer = explorer
        deleteSelectedAction = QtGui.QAction("Delete", None)
        deleteSelectedAction.triggered.connect(lambda: self.deleteElements(selected))
        return [deleteSelectedAction]
                    
    def deleteStore(self):
        self.deleteElements([self])
        
class GsResourceItem(GsTreeItem): 
    def __init__(self, resource):  
        if isinstance(resource, Coverage):
            icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/grid.jpg")
        else:
            icon = None#QtGui.QIcon(os.path.dirname(__file__) + "/../images/workspace.png")
        GsTreeItem.__init__(self, resource, icon)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)  

    def acceptDroppedItem(self, explorer, item):        
        publishDraggedLayer(explorer, item.element, self.element.workspace)
        return explorer.tree.findAllItems(self.element.catalog)
    
    def contextMenuActions(self, explorer):
        self.explorer = explorer
        deleteResourceAction = QtGui.QAction("Delete", None)
        deleteResourceAction.triggered.connect(self.deleteResource)
        return[deleteResourceAction]
                
    def deleteResource(self):
        self.deleteElements([self])      

#### GWC ####

class GwcLayersItem(GsTreeItem): 
    def __init__(self):
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/gwc.png")
        GsTreeItem.__init__(self, None, icon, "GeoWebCache layers")                                    
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)

    def populate(self):
        catalog = self.parentCatalog()
        self.element = Gwc(catalog)        
        layers = self.element.layers()
        for layer in layers:
            item = GwcLayerItem(layer)
            self.addChild(item)

    def acceptDroppedItem(self, explorer, item):
        catalog = self.parentCatalog()
        workspace = self.getDefaultWorkspace(catalog)
        toUpdate = []
        if workspace is not None:
            self.publishDraggedLayer(item.element, workspace)
            toUpdate.append(explorer.tree.findAllItems(catalog)[0])  
        return toUpdate  
    
    def contextMenuActions(self, explorer):
        self.explorer = explorer   
        addGwcLayerAction = QtGui.QAction("New GWC layer...", None)
        addGwcLayerAction.triggered.connect(self.addGwcLayer)
        return [addGwcLayerAction]        
               
     
    def addGwcLayer(self):
        cat = self.parentCatalog()
        layers = cat.get_layers()              
        dlg = EditGwcLayerDialog(layers, None)
        dlg.exec_()        
        if dlg.gridsets is not None:
            layer = dlg.layer
            gwc = Gwc(layer.catalog)
            
            #TODO: this is a hack that assumes the layer belong to the same workspace
            typename = layer.resource.workspace.name + ":" + layer.name
            
            gwclayer= GwcLayer(gwc, typename, dlg.formats, dlg.gridsets, dlg.metaWidth, dlg.metaHeight)
            catItem = self.explorer.tree.findAllItems(cat)            
            self.explorer.run(gwc.addLayer,
                              "GWC layer '" + layer.name + "' correctly created",
                              [catItem.gwcItem],
                              gwclayer)             
                            

          
                
class GwcLayerItem(GsTreeItem): 
    def __init__(self, layer):          
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/layer.png")        
        GsTreeItem.__init__(self, layer, icon)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)
        
    def contextMenuActions(self, explorer):
        self.explorer = explorer  
        editGwcLayerAction = QtGui.QAction("Edit...", None)
        editGwcLayerAction.triggered.connect(self.editGwcLayer)           
        seedGwcLayerAction = QtGui.QAction("Seed...", None)
        seedGwcLayerAction.triggered.connect(self.seedGwcLayer)        
        emptyGwcLayerAction = QtGui.QAction("Empty", None)
        emptyGwcLayerAction.triggered.connect(self.emptyGwcLayer)                  
        deleteLayerAction = QtGui.QAction("Delete", None)
        deleteLayerAction.triggered.connect(self.deleteLayer)
        return[editGwcLayerAction, seedGwcLayerAction, emptyGwcLayerAction, deleteLayerAction]
                
    def deleteLayer(self):
        self.deleteElements([self])      
        
        
    def emptyGwcLayer(self):
        layer = self.element   
        #TODO: confirmation dialog??    
        self.explorer.run(layer.truncate,
                          "GWC layer '" + layer.name + "' correctly truncated",
                          [],
                          )            
    def seedGwcLayer(self):
        layer = self.element   
        dlg = SeedGwcLayerDialog(layer)
        dlg.show()
        dlg.exec_()
        if dlg.format is not None:
            self.explorer.run(layer.seed,
                              "GWC layer '" + layer.name + "' correctly seeded",
                              [],
                              dlg.operation, dlg.format, dlg.gridset, dlg.minzoom, dlg.maxzoom, dlg.extent)
    
    def editGwcLayer(self):
        layer = self.element   
        dlg = EditGwcLayerDialog([layer], layer)
        dlg.exec_()
        if dlg.gridsets is not None:
            self.explorer.run(layer.update,
                              "GWC layer '" + layer.name + "' correctly updated",
                              [],
                              dlg.formats, dlg.gridsets, dlg.metaWidth, dlg.metaHeight)
            


def publishDraggedLayer(self, explorer, layer, workspace):
    cat = workspace.catalog  
    ogcat = OGCatalog(cat)                                
    explorer.run(ogcat.publishLayer,
             "Layer correctly published from layer '" + layer.name() + "'",
             [],
             layer, workspace, True)
                
### PostGIS #####
        
class PgConnectionItem(TreeItem): 
    def __init__(self, conn):          
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/pg.png")        
        TreeItem.__init__(self, conn, icon)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)          
        
    def populate(self):
        stores = self.element.catalog.get_stores(self.element)
        for store in stores:
            storeItem = GsStoreItem(store)
            storeItem.populate()
            self.addChild(storeItem)
                
class PgSchemaItem(TreeItem): 
    def __init__(self, schema):          
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/pg.png")        
        TreeItem.__init__(self, schema, icon)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDropEnabled)
        
class PgTableItem(TreeItem): 
    def __init__(self, table):          
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/pg.png")        
        TreeItem.__init__(self, table, icon)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)