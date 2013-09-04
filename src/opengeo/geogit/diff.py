from feature import Feature

TYPE_MODIFIED = "Modified"
TYPE_ADDED = "Added"
TYPE_REMOVED = "Removed"
NULL_ID = "0" * 40

class Diffentry():
    
    '''A difference between to references for a given path''' 
    
    def __init__(self, repo, oldref, newref, path):
        self.repo = repo
        self.path = path
        self.oldref = oldref
        self.newref = newref

    def oldobject(self):
        return Feature(self.repo, self.oldref, self.path)
    
    def newobject(self):
        return Feature(self.repo, self.newref, self.path)
    
    def type(self):
        if self.oldref == NULL_ID:
            return TYPE_ADDED
        elif self.newref == NULL_ID:
            return TYPE_REMOVED
        else:
            return TYPE_MODIFIED
    
    def __str__(self):  
        return self.type() + " " + self.path                  
        #s = self.repo.getfeaturediffs(self.oldref, self.newref, self.path)
        
        

    
    