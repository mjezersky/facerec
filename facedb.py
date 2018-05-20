import pickle
import numpy as np
import time

class FaceDB():
    def __init__(self):
        self.faces = {}

        self.vectors = None
        self.labels = None


    def store(self, filename):
        data = [self.faces, self.vectors, self.labels]
        f = open(filename, "wb")
        pickle.dump(data, f)
        f.close()

    def load(self, filename):
        f = open(filename, "rb")
        data = pickle.load(f)
        f.close()
        self.faces = data[0]
        self.vectors = data[1]
        self.labels = data[2]

    def getVectors(self):
        return self.vectors

    def add(self, name, vector):
        if name in self.faces:
            self.faces[name].append(vector)
        else:
            self.faces[name] = [vector]

    def createVectorsAndLabels(self):
        self.vectors = []
        self.labels = []
        for name in self.faces:
            for vector in self.faces[name]:
                self.vectors.append(vector)
                self.labels.append(name)

    def getName(self, index):
        return self.labels[index]

    # for OpenFace model
    def distToConf(self, dist):
        if dist>1.2:
            return 0
        return 1.0 - (dist/1.2)


    # for ResNet model
    def dlibDistToConf(self, dist):
        conf = 1-((dist-0.4)/0.4)
        if conf<0: return 0.0
        if conf>1: return 1.0
        return conf

    def calcBestMatch(self, name, vector):
        best = 100
        for vec2 in self.faces[name]:
            dist = np.linalg.norm(vector-vec2) # DEBUG dist = distance(vec2, vector)
            print "dist:" + str(dist)
            if dist < best:
                best = dist
        return best


    #non SVM prediction
    def getPred(self, vector):
        print "predicting"
        s=time.time()
        dists = map(lambda x: np.linalg.norm(vector-x), self.vectors)
        minind = np.argmin(dists)
        print "min is", minind, ":", self.labels[minind], dists[minind], "took", time.time()-s
        
        # confidence for 0.0 to 0.4 is 1.0, lowers from 0.4 to 0.8 and past 0.8 is zero
        conf = self.dlibDistToConf(dists[minind])
        return self.labels[minind], conf
                
    def getConfidence(self, name, vector):
        return self.distToConf(self.calcBestMatch(name, vector))

    def deserializeVector(self, string):
        return map(lambda x: float(x), string.split("#"))

    def deserialize(self, string):
        self.faces = {}
        elements = string.split("\n")
        for e in elements:
            if e=="":
                continue
            data = e.split(",")
            self.add(data[0], self.deserializeVector(data[1]))
        self.createVectorsAndLabels()
        
