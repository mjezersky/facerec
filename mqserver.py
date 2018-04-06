#!/usr/bin/python

import facedb
import svmclassifier as svm
import neuralnet as nnet
import time
import numpy as np
import pika
import threading


IDENTIFIER = "default"
MQ_SERVER_IP = "192.168.0.101"
MQ_CREDENTIALS = pika.PlainCredentials('facerec', 'facerec')
FACE_DB_FILE = "dbfile.p"
RECOG_THRESHOLD = 0.25


def serializeArray(arr):
    return "#".join( map(lambda x: str(x), arr) )

class MQServer():
    def __init__(self):
        self.currFrame = 0
        self.fdb = facedb.FaceDB()
        try:
            self.fdb.load(FACE_DB_FILE)
            self.vectors = self.fdb.getVectors()
        except:
            self.vectors = []
        print(self.fdb.labels)
        self.smodel = svm.trainNewModel(self.vectors)


    def run(self):
        self.broadcastInit()
        self.mainServiceInit()



    def recog(self, vec):
        if vec is None:
            return "NO_FACE_DETECTED"

        if self.smodel is None:
            pred = "unknown"
            confidence = 0.0
        else:
            preds = svm.predict(vec,self.smodel)
            pred = str(self.fdb.getName(np.argmax(preds)))
            
            confidence = self.fdb.getConfidence(pred, vec)
            if confidence < RECOG_THRESHOLD:
                # reverse confidence for unknown
                pred = "unknown"
                #confidence = 1-confidence
            
        return pred + "," + str(confidence) + "," + serializeArray(vec)


    def retrain(self):
        self.smodel = svm.trainNewModel(self.vectors)
        #dbh.saveVectors(vectors, "filedb.p")


    def splitFrame(self, framestr):
        separatorIndex = -1
        maxlen = 20
        if len(framestr)<maxlen:
            print "TOO SMALL"
            return ("0", "") 
        for i in range(maxlen):
            if framestr[i] == ",":
                separatorIndex = i
                break
        
        if separatorIndex == -1:
            print "Warning: invalid frame."
            return ("0", "")

        print "OK --------"

        return (framestr[0:separatorIndex], framestr[separatorIndex+1:])

    def getResults(self, imgstring):
        startTime = time.time()
        allvecs = []
        boxes = []
        try:
            allvecs, boxes = nnet.getRepFromString(imgstring)
            vec0 = allvecs[0]
            boxStr = str(boxes[0])+"$"
            res = vec0
        except Exception as err:
            res = None
            boxStr = ""
        endTime = time.time()
        print "Total facerec time:", endTime-startTime

        results = []
        for i in range(0, len(boxes)):
            resStr = serializeArray(boxes[i]) + "," + self.recog(allvecs[i])
            results.append(resStr)
        
        return results

    def deserializeDB(self, string):
        print "DB deserialize"
        self.fdb.deserialize(string)
        self.fdb.store(FACE_DB_FILE)
        self.vectors = self.fdb.getVectors()
        self.retrain()

    def mainServiceCallback(self, ch, method, properties, body):
        print "got", len(body), "bytes"
        frameNum, data = self.splitFrame(body)
        self.currFrame = int(frameNum)
        results = self.getResults(data)
        if len(results)==0:
            results = [ "none,none,0,none" ]
        print frameNum
        if frameNum == "-1":
            responseType = "2" #DB recognition request
            print "DB frame request"
        else:
            responseType = "1"
        msg = responseType + ";" + IDENTIFIER + ";" + str(self.currFrame) + ";" + ";".join(results)
        print "Publishing"
        ch.basic_publish(exchange='',
                              routing_key='feedback',
                              body=msg)

    def broadcastCallback(self, ch, method, properties, body):
       print "got", len(body), "bytes"
       if len(body)<=1:
           return
       if body[0]=="0":
           print "Announcing 0"
           ch.basic_publish(exchange='',
                              routing_key='feedback',
                              body="0,"+IDENTIFIER)
       elif body[0]=="1":
           self.deserializeDB(body[1:])


    def mainServiceInit(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_SERVER_IP, credentials=MQ_CREDENTIALS))
        channel = connection.channel()

        channel.queue_declare(queue=IDENTIFIER)
        channel.queue_declare(queue="feedback")

        channel.basic_consume(self.mainServiceCallback,
                          queue=IDENTIFIER,
                          no_ack=True)

        channel.start_consuming()

    def broadcastInit(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_SERVER_IP, credentials=MQ_CREDENTIALS))
        channel = connection.channel()

        channel.exchange_declare(exchange='broadcast', exchange_type='fanout')
        channel.queue_declare(queue="feedback")
        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange="broadcast", queue=queue_name)

        channel.basic_consume(self.broadcastCallback,
                          queue=queue_name,
                          no_ack=True)

        mq_recieve_thread = threading.Thread(target=channel.start_consuming)
        mq_recieve_thread.daemon = True
        mq_recieve_thread.start()


while 1:
    try:
        s = MQServer()
        s.run()
    except KeyboardInterrupt:
        print "\nClosing"
        break
