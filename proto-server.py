#!/usr/bin/python

import facerecprotocol as frp
import dbhandler as dbh
import svmclassifier as svm
import neuralnet as nnet
import time
import numpy as np


def recog(vec, vectors, hashTable):
    if vec is None:
        return "NO_FACE_DETECTED"
    preds = svm.predict(vec,smodel)
    pred = str(vectors.keys()[np.argmax(preds)])
    return pred+"/"+dbh.query(vec, vectors, hashTable)+"("+str(preds)+")"
    vectors["M"] = vec
    dbh.saveVectors(vectors, "filedb.p")
    return(str(len(vec)))


def retrain():
    global vectors
    global smodel
    global htab
    htab = dbh.buildHashTable(vectors, 128)
    smodel = svm.trainNewModel(vectors)
    dbh.saveVectors(vectors, "filedb.p")


def wipedb():
    global vectors
    vectors = {}
    dbh.saveVectors(vectors, "filedb.p")


def dumpdb():
    return str(vectors.keys())

def storevec(vec, label):
    global vectors
    vectors[label] = vec


p = frp.FacerecProtocol()
p.bind("0.0.0.0", 9000)
p.listen(1)

try:
    vectors = dbh.loadVectors("filedb.p")
except:
    vectors = {}

print(vectors.keys())

htab = dbh.buildHashTable(vectors, 128)
smodel = svm.trainNewModel(vectors)


while 1:
    print "Accepting..."
    try:
        p.accept()
    except Exception as err:
        print err
        p.close()
        exit()
    while 1:
        try:
            label = ""
            print "awaiting data..."
            command = p.recv()
            p.send("ACK")

            if command == "WIPEDB":
                wipedb()
                continue
            elif command == "DUMPDB":
                p.send(dumpdb())
                continue
            elif command == "RETRAIN":
                retrain()
                continue
            elif command == "STORE":
                label = p.recv()
                p.send("ACK")

            data1 = p.recv()
            if data1 == None:
                p.closeClient()
                break
            print "received", len(data1)


            startTime = time.time()
            try:
                allvecs, boxes = nnet.getRepFromString(data1)
                vec0 = allvecs[0]
                boxStr = str(boxes[0])+"$"
                res = vec0
            except Exception as err:
                res = None
                boxStr = ""
            endTime = time.time()
            print "Total facerec time:", endTime-startTime

            if command == "RECOG":
                p.send(boxStr+recog(res, vectors, htab))
            elif command == "STORE":
                storevec(res, label)
                p.send("Stored "+label)
        
        except KeyboardInterrupt:
            print "Keyboard interrupt, closing"
            p.close()
            exit()

        except Exception as ex:
            print ex
            p.close()
            break
