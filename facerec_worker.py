#!/usr/bin/python

import facedb
import svmclassifier as svm
import recognizer
import time
import numpy as np
import pika
import threading



def serializeArray(arr):
    return "#".join( map(lambda x: str(x), arr) )

class MQServer():
    def __init__(self):
	self.WORKER_GROUP_NAME = "default"
        self.IDENTIFIER = "Worker A"
        self.MQ_SERVER_IP = "192.168.1.3"
        self.MQ_SERVER_PORT = 5672
        self.MQ_USERNAME = "facerec"
        self.MQ_PASSWORD = "facerec"
        self.SCALE_FACTOR = 0.6
        self.RECOG_THRESHOLD = 0.575

        self.FACE_DB_FILE = "dbfile.p"
        self.DETECTOR_STEP = 3
        self.FRAME_SKIP_SYNC = 2
        self.MQ_CREDENTIALS = pika.PlainCredentials(self.MQ_USERNAME, self.MQ_PASSWORD)
        self.SVM_MODE = False

        self.currFrame = 0
        self.prevFrameNum = 0
	self.skipCounter = 0
        self.fdb = facedb.FaceDB()
        try:
            self.fdb.load(self.FACE_DB_FILE)
            self.vectors = self.fdb.getVectors()
        except:
            self.vectors = []
        print(self.fdb.labels)
        if self.SVM_MODE:
            self.smodel = svm.trainNewModel(self.vectors)
        else:
            self.smodel = None
        self.detectorStep = self.DETECTOR_STEP


    def run(self):
        self.broadcastInit()
        self.mainServiceInit()



    def recog(self, vec):
        if vec is None:
            return "NO_FACE_DETECTED"

        if True:
            pred, confidence = self.fdb.getPred(vec)
            if confidence < self.RECOG_THRESHOLD:
                pred = "unknown"
        else:
            preds = svm.predict(vec,self.smodel)
            pred = str(self.fdb.getName(np.argmax(preds)))
            
            confidence = self.fdb.getConfidence(pred, vec)
            if confidence < self.RECOG_THRESHOLD:
                pred = "unknown"

        return pred + "," + str(confidence) + "," + serializeArray(vec)


    def retrain(self):
        self.smodel = svm.trainNewModel(self.vectors)
        #dbh.saveVectors(vectors, "filedb.p")


    def splitFrame(self, framestr):
        separatorIndex = -1
        maxlen = 20
        if len(framestr)<maxlen:
            return ("0", "") 
        for i in range(maxlen):
            if framestr[i] == ",":
                separatorIndex = i
                break
        
        if separatorIndex == -1:
            print "Warning: invalid frame."
            return ("0", "")

        return (framestr[0:separatorIndex], framestr[separatorIndex+1:])

    def getResults(self, imgstring):
        startTime = time.time()
        allvecs = []
        boxes = []
        currFrameNum = int(self.currFrame)
        if currFrameNum <= 0:
            # first frame, reset counter
            self.skipCounter = 0
        if abs(self.prevFrameNum-currFrameNum) > self.FRAME_SKIP_SYNC:
            # continuity broken, reset counter
            self.skipCounter = 0
        self.prevFrameNum = currFrameNum
        print "SK", self.skipCounter, (self.skipCounter>=1 and self.skipCounter%self.detectorStep!=0)
        if self.skipCounter>=1 and self.skipCounter%self.detectorStep!=0:
            skipDetection = True
        else:
            skipDetection = False
        self.skipCounter += 1
        allvecs, boxes = recognizer.getRepFromString(imgstring, self.SCALE_FACTOR, skipDetection)
        endTime = time.time()
        print "allvecs, boxes", len(allvecs), len(boxes)
        print "Total facerec time:", endTime-startTime

        results = []
        for i in range(0, len(boxes)):
            resStr = serializeArray(boxes[i]) + "," + self.recog(allvecs[i])
            results.append(resStr)
        
        return results

    def deserializeDB(self, string):
        print "DB deserialize"
        self.fdb.deserialize(string)
        self.fdb.store(self.FACE_DB_FILE)
        self.vectors = self.fdb.getVectors()
        if self.SVM_MODE:
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
        msg = responseType + ";" + self.IDENTIFIER + ";" + str(self.currFrame) + ";" + ";".join(results)
        print "Publishing", len(msg), "bytes"
        ch.basic_publish(exchange='',
                              routing_key='feedback-'+self.WORKER_GROUP_NAME,
                              body=msg)

    def broadcastCallback(self, ch, method, properties, body):
       #print "got", len(body), "bytes"
       if len(body)<=1:
           return
       if body[0]=="0":
           print "Responding to discovery request."
           ch.basic_publish(exchange='',
                              routing_key='feedback-'+self.WORKER_GROUP_NAME,
                              body="0,"+self.IDENTIFIER)
       elif body[0]=="1":
           self.deserializeDB(body[1:])


    def mainServiceInit(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.MQ_SERVER_IP, port=self.MQ_SERVER_PORT, credentials=self.MQ_CREDENTIALS))
        channel = connection.channel()

        channel.queue_declare(queue=self.IDENTIFIER)
        channel.queue_declare(queue="feedback-"+self.WORKER_GROUP_NAME)

        channel.basic_consume(self.mainServiceCallback,
                          queue=self.IDENTIFIER,
                          no_ack=True)

        channel.start_consuming()

    def broadcastInit(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.MQ_SERVER_IP, port=self.MQ_SERVER_PORT, credentials=self.MQ_CREDENTIALS))
        channel = connection.channel()

        channel.exchange_declare(exchange='broadcast-'+self.WORKER_GROUP_NAME, exchange_type='fanout')
        channel.queue_declare(queue="feedback-"+self.WORKER_GROUP_NAME)
        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange="broadcast-"+self.WORKER_GROUP_NAME, queue=queue_name)

        channel.basic_consume(self.broadcastCallback,
                          queue=queue_name,
                          no_ack=True)

        mq_recieve_thread = threading.Thread(target=channel.start_consuming)
        mq_recieve_thread.daemon = True
        mq_recieve_thread.start()

def runserver(server):
    while 1:
        try:
            server.run()
        except KeyboardInterrupt:
            print "Closing\n"
            break
