import os
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.gui import QgsFilterLineEdit


class ConfigDialog(QDialog):
    def __init__(self, toolbox):
        QDialog.__init__(self)
        self.setupUi()
        self.toolbox = toolbox
        self.groupIcon = QIcon()
        self.groupIcon.addPixmap(self.style().standardPixmap(QStyle.SP_DirClosedIcon),
                                 QIcon.Normal, QIcon.Off)
        self.groupIcon.addPixmap(self.style().standardPixmap(QStyle.SP_DirOpenIcon),
                                 QIcon.Normal, QIcon.On)

        if hasattr(self.searchBox, 'setPlaceholderText'):
            self.searchBox.setPlaceholderText(self.tr("Search..."))

        self.searchBox.textChanged.connect(self.fillTree)
        self.fillTree()
        self.tree.itemClicked.connect(self.edit)
        self.tree.itemDoubleClicked.connect(self.edit)

    def setupUi(self):        
        self.resize(640, 450)
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setMargin(0)        
        self.searchBox = QgsFilterLineEdit(self)        
        self.verticalLayout.addWidget(self.searchBox)
        self.tree = QtGui.QTreeWidget(self)
        self.tree.setAlternatingRowColors(True)        
        self.verticalLayout.addWidget(self.tree)
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)        
        self.verticalLayout.addWidget(self.buttonBox)

        self.setWindowTitle("Configuration options")
        self.searchBox.setToolTip("Enter setting name to filter list")
        self.tree.headerItem().setText(0, "Setting")
        self.tree.headerItem().setText(1, "Value")


        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        


    def edit(self, item, column):
        if column > 0:
            self.tree.editItem(item, column)

    def fillTree(self):
        self.items = {}
        self.tree.clear()
        text = unicode(self.searchBox.text())
        settings = ProcessingConfig.getSettings()
        priorityKeys = ['General', "Models", "Scripts"]
        for group in priorityKeys:
            groupItem = QTreeWidgetItem()
            groupItem.setText(0,group)
            icon = ProcessingConfig.getGroupIcon(group)
            groupItem.setIcon(0, icon)
            for setting in settings[group]:
                if setting.hidden:
                    continue
                if text =="" or text.lower() in setting.description.lower():
                    settingItem = TreeSettingItem(setting, icon)
                    self.items[setting]=settingItem
                    groupItem.addChild(settingItem)
            self.tree.addTopLevelItem(groupItem)
            if text != "":
                groupItem.setExpanded(True)

        providersItem = QTreeWidgetItem()
        providersItem.setText(0, "Providers")
        icon = QtGui.QIcon(os.path.dirname(__file__) + "/../images/alg.png")
        providersItem.setIcon(0, icon)
        for group in settings.keys():
            if group in priorityKeys:
                continue
            groupItem = QTreeWidgetItem()
            groupItem.setText(0,group)
            icon = ProcessingConfig.getGroupIcon(group)
            groupItem.setIcon(0, icon)
            for setting in settings[group]:
                if setting.hidden:
                    continue
                if text =="" or text.lower() in setting.description.lower():
                    settingItem = TreeSettingItem(setting, icon)
                    self.items[setting]=settingItem
                    groupItem.addChild(settingItem)
            if text != "":
                groupItem.setExpanded(True)
            providersItem.addChild(groupItem)
        self.tree.addTopLevelItem(providersItem)

        self.tree.sortItems(0, Qt.AscendingOrder)
        self.tree.setColumnWidth(0, 400)

    def accept(self):
        for setting in self.items.keys():
            if isinstance(setting.value,bool):
                setting.value = (self.items[setting].checkState(1) == Qt.Checked)
            elif isinstance(setting.value, (float,int, long)):
                value = str(self.items[setting].text(1))
                try:
                    value = float(value)
                    setting.value = value
                except ValueError:
                    QMessageBox.critical(self,
                                         self.tr("Wrong value"),
                                         self.tr("Wrong parameter value:\n%1").arg(value)
                                        )
                    return
            else:
                setting.value = str(self.items[setting].text(1))
            ProcessingConfig.addSetting(setting)
        ProcessingConfig.saveSettings()
        self.toolbox.updateTree()

        QDialog.accept(self)

class TreeSettingItem(QTreeWidgetItem):

    def __init__(self, setting, icon):
        QTreeWidgetItem.__init__(self)
        self.setting = setting
        self.setText(0, setting.description)
        if isinstance(setting.value,bool):
            if setting.value:
                self.setCheckState(1, Qt.Checked)
            else:
                self.setCheckState(1, Qt.Unchecked)
        else:
            self.setFlags(self.flags() | Qt.ItemIsEditable)
            self.setText(1, unicode(setting.value))
        self.setIcon(0, icon)
