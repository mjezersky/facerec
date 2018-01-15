# actual DB not yet implemented, using local files instead

import pickle
from lshash import lshash


# vectors format: dict of vectors + labels
#                   {[...] : "label", ...}


def loadVectors(fname):
    f = open(fname, "rb")
    vecs = pickle.load(f)
    f.close()
    return vecs

def saveVectors(fname, vectors):
    f = open(fname, "wb")
    pickle.dump(f, vectors)
    f.close()

def buildHashTable(vectors):
    hashTable = LSHash(16, 124)
    for vec in vectors:
        hashTable.index(vec)
    return hashTable

def query(inVector, vectors, hashTable):
    tQuery = hashTable.query(inVector)
    # get most probable
    mostProbable = tQuery[0]
    return vectors[mostProbable]   
