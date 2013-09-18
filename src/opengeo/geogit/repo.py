from commitish import Commitish
from cliconnector import CLIConnector
from opengeo import geogit
from geogitexception import GeoGitException

class Repository:
    
    def __init__(self, url, connector = None, init = False):
        self.url = url        
        self.connector = CLIConnector() if connector is None else connector
        self.connector.setRepository(self) 
        if init:
            self.init()        
        #Only local repos suported so far, so we check it
        #TODO                       
        self.connector.checkisrepo()
        
    def head(self):
        '''the refspec of the current HEAD'''
        return self.connector.head()
    
    def log(self, ref = None):
        '''returns a set of logentries starting from the passed ref, or HEAD if there is no passed ref'''
        ref = geogit.HEAD if ref is None else ref
        return self.connector.log(ref)
    
    def trees(self, ref = geogit.HEAD, path = None): 
        '''returns a set of Tree objects with all the trees for the passed ref and path'''       
        return self.connector.trees(ref, path)   
    
    def features(self, ref = geogit.HEAD, path = None): 
        '''returns a set of Feature objects with all the features for the passed ref and path'''          
        return self.connector.features(ref, path)   
    
    def children(self, ref = geogit.HEAD, path = None): 
        '''returns a set of Tree and Feature objects with all the trees for the passed ref and path'''          
        return self.connector.children(ref, path)                   
            
    def master(self):
        return Commitish(self, geogit.MASTER)
        
    def branches(self):        
        ''' Returns a list of Commitish with the tips of branches in the repo'''
        return self.connector.branches()
    
    def tags(self):   
        ''' Returns a list of Commitish with the tags in the repo'''     
        return self.connector.tags()
    
    def branch(self, name):        
        '''Returns a Commitish corresponding to the branch of the passed name'''
        for branch in self.branches():
            if branch.ref == name:
                return branch
        raise GeoGitException("Specified branch does not exist")
    
    def clone(self, url):
        return self.connector.clone(url)
    
    def createbranch(self, commitish, name, force = False, checkout = False):
        return self.connector.createbranch(commitish, name, force, checkout)
        
    def createtag(self, commitish, name):
        self.connector.createtag(commitish, name)
    
    def diff(self, refa = geogit.HEAD, refb = geogit.WORK_HEAD):
        return self.connector.diff(refa, refb)
    
    def unstaged(self):
        return self.diff(geogit.STAGE_HEAD, geogit.WORK_HEAD);
    
    def staged(self):
        return self.diff(geogit.HEAD, geogit.STAGE_HEAD);
    
    def notindatabase(self):
        return self.diff(geogit.HEAD, geogit.WORK_HEAD);
    
    def conflicts(self):
        return self.connector.conflicts()
    
    def checkout(self, ref, paths = None):
        return self.connector.checkout(ref, paths)
    
    def add(self, paths = []):
        return self.connector.add(paths)

    def commit(self, message, paths = []):
        return self.connector.commit(message, paths)
    
    def blame(self, path):
        return self.connector.blame(path)
    
    def getfeature(self, ref):
        return self.connector.getfeature(ref)
    
    def getversions(self, path):
        return self.connector.getversions(path)
    
    def getfeaturediffs(self, ref, ref2, path):
        return self.connector.getfeaturediffs(ref, ref2, path)
    
    def reset(self, ref, mode = geogit.RESET_MODE_HARD):
        return self.connector.reset(ref, mode)
       
    def exportshp(self, ref, shapefile):
        self.connector.exportshp(ref, shapefile)
        
    def exportsl(self, ref, database):
        self.connector.exportsl(ref, database)        
    
    def importosm(self, osmfile, add):
        self.connector.importosm(osmfile, add)
        
    def importshp(self, shpfile, add = False, dest = None):
        self.connector.importshp(shpfile, add, dest)        
        
    def downloadosm(self, osmurl, bbox):
        self.connector.downloadosm(osmurl, bbox)      
        
    def merge(self, commitish, nocommit, message):
        self.connector.merge(commitish, nocommit, message)  
        
    def cherrypick(self, commitish):
        self.connector.cherrypick(commitish)
        
    def show(self, ref):
        return self.connector.show(ref)
        
    def remotes(self):
        return self.connector.remotes()
        
    def addremote(self, name, url):
        self.connector.addremote(name, url)        
        
    def removeremote(self, name):
        self.connector.removeremote(name)                
    
    def init(self):
        self.connector.init()
    
    
