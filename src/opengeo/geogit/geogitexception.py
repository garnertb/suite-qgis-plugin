class GeoGitException(Exception):
    
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return unicode(self.message)
    