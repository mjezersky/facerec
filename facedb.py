import pickle
import numpy as np


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

    def distToConf(self, dist):
        if dist>1.2:
            return 0
        return 100 - int(100*(dist/1.2))

    def calcBestMatch(self, name, vector):
        best = 100
        for vec2 in self.faces[name]:
            dist = np.linalg.norm(vector-vec2) # DEBUG dist = distance(vec2, vector)
            if dist < best:
                best = dist
        return best
                
    def getConfidence(self, name, vector):
        return self.distToConf(self.calcBestMatch(name, vector))

    def deserializeVector(self, string):
        return map(lambda x: float(x), string.split("#"))

    def deserialize(self, string):
        self.faces = {}
        elements = string.split("\n")
        for e in elements:
            data = e.split(",")
            self.add(data[0], self.deserializeVector(data[1]))
        self.createVectorsAndLabels()
        
