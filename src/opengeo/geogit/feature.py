class Feature(object):

    def __init__(self, repo, ref, path):
        self.repo = repo
        self.ref = ref
        self.path = path
        self._attributes = None

    def attributes(self):
        if self._attributes is None:
            self.query()
        return self._attributes

    def featuretype(self):
        pass

    def query(self):
        self._attributes = self.repo.getfeature(self.path)

    def blame(self):
        return self.repo.blame(self.path)

    def allversions(self):
        return self.repo.getversions(self.path)

    def __str__(self):
        return self.path
        
    

