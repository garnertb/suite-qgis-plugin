from repo import Repository


def testLog():
    repo = Repository('d:\\geogit-repo')
    #get the log of the repo
    log = repo.log()
    for entry in log:
        #each entry has a commit object, and a list of diffentries
        print entry.commit
        for diff in entry.diffset:
            print diff
            
    #that was done on the current branch, but we can use other branches as well 
    branches = repo.branches()
    for branch in branches:
        if branch is not None and isinstance(branch, str):
            print branch
        else:
            pass
    
    #let's have a look at the history of branch "mybranch"    
    branch = branches[1]
    log = branch.log()
    for entry in log:
        print entry.commit
        for diff in entry.diffset:
            print diff
            
    
    #let's explore the tree corresponding to the tip of that branch
    #Tree is a tree object that points to the root tree in that snapshot
    tree = log[0].commit.tree()
    #we can see the subtrees it contains
    trees = tree.trees()
    for subtree in trees:
        print subtree
    
    #each subtree is a tree object itself, and we can see its trees and its features
    features = trees[0].features()
    for feature in features:        
        print feature
        
    #and for each feature we can see its attributes
    attrs = features[0].attributes()
    for attr in attrs:
        print attr
        
        
    
def testTrees():
    repository = Repository('d:\\geogit-repo')
    trees = repository.trees()
    for tree in trees:
        print str(tree.path)
        features = tree.features()
        for feature in features:
            print str(feature.path)
            

if __name__ == '__main__':
    testLog()
            