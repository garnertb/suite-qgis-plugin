import subprocess
import os
from opengeo.geogit.feature import Feature
from opengeo.geogit.tree import Tree
from opengeo.geogit.commit import Commit
from opengeo.geogit.log import Logentry
import datetime
from opengeo.geogit.diff import Diffentry
from opengeo.geogit.commitish import Commitish
from opengeo.geogit.geogitexception import GeoGitException
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtCore, QtGui
from opengeo import geogit

class CLIConnector():
    ''' A connector that calls the cli version of geogit and parses cli output'''
    
    def setRepository(self, repo):
        self.repo = repo        
        
    def run(self, command):         
        cursor = QApplication.overrideCursor()
        if cursor == None or cursor == 0:
            changeCursor = True
        else:
            changeCursor = cursor.shape() != Qt.WaitCursor                        
        if changeCursor:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))                                                                                           
        os.chdir(self.repo.url)
        command = ['geogit'] + command
        output = []    
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
                                stdin=subprocess.PIPE,stderr=subprocess.STDOUT, universal_newlines=True)
        first = True
        for line in iter(proc.stdout.readline, ""):
            #print line
            if not first:        
                line = line.strip("\n")
                output.append(line)
            else:
                first = False
        returncode = proc.returncode
        if changeCursor:
            QtGui.QApplication.restoreOverrideCursor()
        if returncode:
            raise GeoGitException("\n".join(output))          
        return output
           
    def head(self):
        self.checkisrepo()
        headfile = os.path.join(self.repo.url, '.geogit', 'HEAD')
        f = open(headfile)
        line = f.readline()
        f.close()
        return line.strip().split(' ')[-1]
    
    def checkisrepo(self):
        if not os.path.exists(os.path.join(self.repo.url, '.geogit')):
            raise GeoGitException("Not a valid GeoGit repository: " + self.repo.url)
        
    def trees(self, ref = 'HEAD', path = None, recursive = False):
        trees = []    
        if path is None:
            fullref = ref
        else:
            fullref = ref + ':' + path 
        commands = ['ls-tree', '-d', fullref]
        if recursive:
            commands.append("-r")
        output = self.run(commands)    
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
        output = self.run(commands)    
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
        output = self.run(commands)    
        for line in output:
            if line != '':
                tokens = line.split(" ")
                if tokens[1] == "feature":
                    features.append(Feature(self.repo, ref, tokens[3]))
        return features 
         
    def logentryFromString(self, lines):
        diffs = []
        changes = False
        message = False
        messagetext = None
        parent = None
        commitid = None
        for line in lines:
            tokens = line.split(' ')
            if message:
                if line.startswith("\t") or line.startswith(" "):
                    messagetext = line.strip() if messagetext is None else messagetext + "\n" + line.strip()
                else:
                    message = False
            if changes:    
                changeTokens =  line.strip().split(' ')                         
                diffs.append(Diffentry(self.repo, changeTokens[1], changeTokens[2], changeTokens[0]))             
            else:                
                if tokens[0] == 'commit':
                    commitid = tokens[1]
                if tokens[0] == 'tree':
                    tree = tokens[1]                    
                if tokens[0] == 'parent':
                    if len(tokens) == 2 and tokens[1] != "":
                        parent = tokens[1]                    
                elif tokens[0] == 'author':
                    author = " ".join(tokens[1:-3])
                    authordate = datetime.datetime.fromtimestamp(int(tokens[-2])//1000)                
                elif tokens[0] == 'committer':
                    committer = tokens[1]
                    committerdate = datetime.datetime.fromtimestamp(int(tokens[-2])//1000)
                elif tokens[0] == 'message':
                    message = True
                elif tokens[0] == 'changes':
                    changes = True                
            
        if commitid is not None:
            c = Commit(self.repo, commitid, tree, parent, messagetext, author, authordate, committer, committerdate)
            return Logentry(c, diffs)
        else:
            return None

    def log(self, ref, path = None):
        logentries = []
        commands = ['rev-list', ref, '--changed']        
        if path is not None:
            commands.extend(["-p", path])
        output = self.run(commands)
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
    
    def checkout(self, ref, path = None):
        commands = ['checkout', ref]
        if path is not None:
            commands.extend(["-p", path])
        self.run(commands)
        
    def reset(self, ref, mode = 'hard'):
        self.run(['reset', ref, "--" + mode])        
        
    def branches(self):    
        branches = []        
        output = self.run(['show-ref'])    
        for line in output:        
            branches.append(Commitish(self.repo, line.strip().split(" ")[-1]))
        return branches
    
    def tags(self):
        #TODO
        return []
    
    def createbranch(self, ref, name, force = False, checkout = False):
        commands = ['branch', name, ref]
        if force:
            commands.append('-f')
        if checkout:
            commands.append('-c')            
        self.run(commands)

        
    def createtag(self, commitish, name):        
        self.run(['tag', name, commitish.ref])

       
    def add(self, paths = []):
        commands = ['add']  
        commands.extend(paths)      
        self.run(commands)     
            
    def commit(self, message, paths = []):
        commands = ['commit', '-m']
        commands.append(message)
        commands.extend(paths)
        self.run(commands)               
             
    def diffentryFromString(self,line):
        tokens = line.strip().split(" ")
        path = tokens[0]
        oldref = tokens[1]
        newref = tokens[2]
        return Diffentry(self.repo, oldref, newref, path) 
    
    
    def diff(self, ref, refb):    
        diffs = []
        output = self.run(['diff-tree', ref, refb])    
        for line in output:
            if line != '':
                diffs.append(self.diffentryFromString(line))
        return diffs
    
    def importosm(self, osmfile, add):
        commands = ["osm", "import", osmfile]        
        if add:
            commands.extend(["--add"])
        self.run(commands)
        
    def downloadosm(self, osmurl, bbox):
        commands = ["osm", "download", osmurl, "--bbox"]
        commands.extend([str(c) for c in bbox])                
        self.run(commands)        
        
    def importshp(self, shapefile, add, dest):
        commands = ["shp", "import", shapefile]
        if dest is not None:
            commands.extend(["--dest", dest])
        if add:
            commands.extend(["--add"])
        self.run(commands)
        
    def exportshp(self, ref, shapefile):
        self.run(["shp", "export", ref, shapefile])
        
    def exportsl(self, ref, database):
        self.run(["sl", "export", ref, ref, database])
        
    def getfeature(self, ref):        
        output = self.run(["show", "--raw", ref])
        return self.parseattribs(output[2:])        
        
    def parseattribs(self, lines):
        attributes = []
        iterator = iter(lines)
        while True:
            try:
                name = iterator.next()
                value = iterator.next()
                attributes.append((name, value))
            except StopIteration:
                return attributes 
    
    def getversions(self, path):
        entries = self.log(geogit.HEAD, path)
        refs = [entry.commit.ref + ":" + path for entry in entries]
        features = self.getfeatures(refs)        
        versions = []
        for i in range(len(features)):
            feature = features[i][1]
            commit = entries[i].commit
            versions.append((commit, feature))
        return versions
        
    def getfeatures(self, refs):
        features = {}
        commands = ["show", "--raw"]
        commands.extend(refs);
        output = self.run(commands)
        iterator = iter(output)
        lines = []    
        name = None    
        while True:
            try:
                line = iterator.next()
                if line == "":                
                    features[name] = self.parseattribs(lines)   
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
        output = self.run(["diff-tree", ref, ref2, "--", path, "--describe"])
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
        output = self.run(["blame", path, "--porcelain"])
        for line in output:
            tokens = line.split(" ")
            name = tokens[0]
            value = tokens[-1]
            commit = Commit(None, tokens[1], None, None, None, tokens[2], int(tokens[4]) + int(tokens[5]), None, None)
            attributes[name]=(value, commit)   
        return attributes 
    
    def merge (self, commitish, nocommit = False, message = None):
        commands = ["merge", commitish]
        if nocommit:
            commands.append("--no-commit")
        elif message is not None:
            commands.append("-m")
            commands.apend(message)
        self.run(commands) 
        
    def cherrypick(self, commitish):
        commands = ["cherry-pick", commitish]
        self.run(commands)
    
    def init(self):
        self.run(["init"])
        
        
