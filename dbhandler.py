# actual DB not yet implemented, using local files instead

import pickle
import numpy as np
from lshash import lshash


# vectors format: dict of vectors + labels
#                   {[...] : "label", ...}


def loadVectors(fname):
    f = open(fname, "rb")
    vecs = pickle.load(f)
    f.close()
    return vecs

def saveVectors(vectors, fname):
    f = open(fname, "wb")
    pickle.dump(vectors, f)
    f.close()

def buildHashTable(vectors, dim):
    print("Creating HT with", len(vectors), "elements.")
    hashTable = lshash.LSHash(len(vectors), dim)
    for vec in vectors:
        hashTable.index(vectors[vec])
    return hashTable

def getLabel(vec, vectors):
    for label in vectors:
        if np.array_equal(vectors[label], vec):
            return label
    return None

def query(inVector, vectors, hashTable):
    tQuery = hashTable.query(inVector)
    # get most probable
    # print(tQuery)
    if len(tQuery)==0:
        return "UNKNOWN#0"
    mostProbable = tQuery[0][0]
    return getLabel(mostProbable, vectors)+"#"+str(tQuery[0][1])
