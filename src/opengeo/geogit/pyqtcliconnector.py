from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtCore, QtGui
from opengeo.geogit.cliconnector import CLIConnector
from opengeo.geogit.geogitexception import GeoGitException
from opengeo import geogit
from opengeo.geogit.commitish import Commitish
from opengeo.geogit.tree import Tree
from opengeo.geogit.feature import Feature
from opengeo.geogit.commit import Commit
import subprocess
import os

class PyQtCLIConnector(CLIConnector):
    ''' a connector that shows a progress dialog with the output of calling geogit'''
    def run(self, command, showProgress = True):                                
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor)) 
        thread = GeogitThread(command, self.repo.url)
        if showProgress:
            dlg = ProgressDialog(thread)  
        else:
            def finish():
                pass        
                #CHECK RETURN CODE HERE!!!
            def error():
                raise GeoGitException(thread.output[0])
            thread.finish.connect(finish)
            thread.error.connect(error)  
                                       
        thread.start()
        if showProgress:
            dlg.exec_()
        thread.wait()
        QtGui.QApplication.restoreOverrideCursor()
        
        #this is temporarily disabled
        #if thread.returncode != 1 and not showProgress:
            #raise GeoGitException("\n".join(thread.output))
        return thread.output    
    
    '''these commands below are reimplemented, so they do not show the dialog, since they are meant for internal calling'''
    
    def log(self, ref, path = None):        
        commands = ['rev-list', ref, '--changed', '-n', str(geogit.LOG_LIMIT)]        
        if path is not None:
            commands.extend(["-p", path])        
        logentries = []    
        output = self.run(commands, False)
        entrylines = []
        for line in output:
            if line == '':                
                entry = self.logentryFromString(entrylines)
                if entry is not None:
                    logentries.append(entry)
                    entrylines = []
            else:
                entrylines.append(line)            
            
        if entrylines:            
            entry = self.logentryFromString(entrylines)
            if entry is not None:
                logentries.append(entry)
        return logentries             
        
    def branches(self):    
        branches = []        
        output = self.run(['show-ref'], False)    
        for line in output:        
            branches.append(Commitish(self.repo, line.strip().split(" ")[-1]))
        return branches
    
    def trees(self, ref = 'HEAD', path = None, recursive = False):
        trees = []    
        if path is None:
            fullref = ref
        else:
            fullref = ref + ':' + path 
        commands = ['ls-tree', '-d', fullref]
        if recursive:
            commands.append("-r")
        output = self.run(commands, False)    
        for line in output:
            if line != '':
                trees.append(Tree(self.repo, ref, line))
        return trees
    
    def children(self, ref = 'HEAD', path = None):
        children = []    
        if path is None:
            fullref = ref
        else:
            fullref = ref + ':' + path 
        commands = ['ls-tree', fullref, "-v"]
        output = self.run(commands, False)    
        for line in output:
            if line != '':
                tokens = line.split(" ")
                if tokens[1] == "feature":
                    children.append(Feature(self.repo, ref, tokens[3]))
                elif tokens[1] == "tree":
                    children.append(Tree(self.repo, ref, line))
        return children   
    
                    
    def features(self, ref = 'HEAD', path = None, recursive = False):
        features = []    
        if path is None:
            fullref = ref
        else:
            fullref = ref + ':' + path 
        commands = ['ls-tree', fullref, "-v"]
        if recursive:
            commands.append("-r")
        output = self.run(commands, False)    
        for line in output:
            if line != '':
                tokens = line.split(" ")
                if tokens[1] == "feature":
                    features.append(Feature(self.repo, ref, tokens[3]))
        return features 
    
    def diff(self, ref, refb):    
        diffs = []
        output = self.run(['diff-tree', ref, refb], False)    
        for line in output:
            if line != '':
                diffs.append(self.diffentryFromString(line))
        return diffs
    
    def getfeature(self, ref):        
        output = self.run(["show", "--raw", ref], False)
        return self.parseattribs(output[2:])        
        
    def getfeatures(self, refs):
        features = []
        commands = ["show", "--raw"]
        commands.extend(refs);
        output = self.run(commands, False)
        iterator = iter(output)
        lines = []    
        name = None    
        while True:
            try:
                line = iterator.next()
                if line == "":                
                    features.append((name, self.parseattribs(lines)))   
                    lines = []
                    name = None 
                else:
                    if name is None:
                        name = line
                        iterator.next() #consume id line
                    else: 
                        lines.append(line)   
            except StopIteration:
                break
        if lines:
            features[name] = self.parseattribs(lines)     
        return features

    def getfeaturediffs(self, ref, ref2, path):
        diffs = {}
        output = self.run(["diff-tree", ref, ref2, "--", path, "--describe"], False)
        lines = iter(output[1:])
        while True:
            try:
                line = lines.next()
                value1 = None
                value2 = None
                tokens = line.split(" ")
                if len(tokens) == 2:
                    changetype = tokens[0]
                    field = tokens[1]
                    if changetype == "M":
                        value1 = lines.next()
                        value2 = lines.next()
                    elif changetype == "R":
                        value1 = lines.next()
                    elif changetype == "A":
                        value2 = lines.next()
                    else:
                        value1 = value2 = lines.next()
                    diffs[field] = (value1, value2);
            except StopIteration:
                return diffs  
            
    def blame(self, path):
        attributes = {}
        output = self.run(["blame", path, "--porcelain"], False)
        for line in output:
            tokens = line.split(" ")
            name = tokens[0]
            value = " ".join(tokens[6:])
            commit = Commit(None, tokens[1], None, None, None, tokens[2], int(tokens[4]) + int(tokens[5]), None, None)
            attributes[name]=(value, commit)   
        return attributes             

class ProgressDialog(QtGui.QDialog):
    def __init__(self, geogitThread):
        QtGui.QDialog.__init__(self, None, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint)
        self.setModal(True)        
        self.ok = False
        self.geogitThread = geogitThread
        self.setupUi()        
        geogitThread.message.connect(self.message)
        geogitThread.finish.connect(self.finish)
        geogitThread.error.connect(self.error)

    def setupUi(self):
        self.resize(400,300)
        self.setWindowTitle("Geogit runner")
        layout = QtGui.QVBoxLayout()
        self.text = QtGui.QTextEdit()                      
        self.closeButton = QtGui.QPushButton()
        self.closeButton.setText("Close")
        self.closeButton.setEnabled(False)
        self.closeButton.clicked.connect(self.closeButtonPressed)
        layout.addWidget(self.text)
        layout.addWidget(self.closeButton)
        self.setLayout(layout)
        QtCore.QMetaObject.connectSlotsByName(self) 
        
    def message(self, msg):
        if "%" in msg:
            # progress bar
            pass
        else:
            self.text.append(msg)
        
    def finish(self):
        QtGui.QApplication.restoreOverrideCursor()        
        self.text.append('\n')
        #=======================================================================
        # if self.geogitThread.returncode != 0:
        #    self.text.append('\n<span style="color:red"> GeoGit encountered problems.</span>')
        # else:
        #=======================================================================
        self.text.append('\n<span style="color:blue"> GeoGit was correctly executed.</span>')
        self.closeButton.setEnabled(True)
    
    def error(self):
        QtGui.QApplication.restoreOverrideCursor()
        self.text.append('<span style="color:red"> Error while running GeoGit:\n' + self.geogitThread.output[0] +'</span>')
        self.text.append()
        self.closeButton.setEnabled(True)
                    
    def closeButtonPressed(self):
        self.close()

class GeogitThread(QtCore.QThread):
    
    message = pyqtSignal(str)
    error = pyqtSignal(str)
    finish = pyqtSignal()
            
    def __init__(self, command, url):
        QtCore.QThread.__init__(self)       
        self.command = command       
        self.url = url                                               
                
    def run (self):                
        try:
            os.chdir(self.url)
            command = ['geogit'] + self.command
            self.message.emit(" ".join(command) + "\n")
            self.output = []    
            proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE,stderr=subprocess.PIPE, universal_newlines=True)
            for line in iter(proc.stdout.readline, ""):       
                line = line.strip("\n")
                self.output.append(line)
                self.message.emit(line)
                #print line
            self.returncode = proc.wait()
            self.finish.emit()
        except Exception, e:
            #print e
            self.returncode = -2            
            self.output = [str(e)]
            self.error.emit()        
        