#!/usr/bin/python

# File:		facerec_worker.py
# Author:	Matous Jezersky

import facedb
import svmclassifier as svm
import recognizer
import time
import numpy as np
import pika
import threading


# serialize an array into a string, with # as element separator
def serializeArray(arr):
    return "#".join( map(lambda x: str(x), arr) )

class MQServer():
    # initialize the server and all variable to their default values
    # do not edit these defaults, you can change them in facerec.py file
    def __init__(self):
	self.WORKER_GROUP_NAME = "default"
        self.IDENTIFIER = "Worker A"
        self.MQ_SERVER_IP = "127.0.0.1"
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
        if self.SVM_MODE:
            self.smodel = svm.trainNewModel(self.vectors)
        else:
            self.smodel = None
        self.detectorStep = self.DETECTOR_STEP


    # start the server
    def run(self):
        print "Worker started - ID: \""+self.IDENTIFIER+"\" Group: \""+self.WORKER_GROUP_NAME+"\""
        print "Connecting..."
        try:
            self.broadcastInit()
            print "Connected"
            self.mainServiceInit()
        except Exception as err:
            print err
            print "Connection error. Reconnecting in 3s, press CTRL+C to cancel."
            time.sleep(3)


    # get a predicted name,confidence tuple from a feature vector 
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


    # retrain SVM classifier
    def retrain(self):
        self.smodel = svm.trainNewModel(self.vectors)
        #dbh.saveVectors(vectors, "filedb.p")


    # split frame data into frame number and image data
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

    # process an image defined by bytes in imgstring, returns a list of tuples
    # where one tuple is feature_vector,bounding_box
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
        if self.skipCounter>=1 and self.skipCounter%self.detectorStep!=0:
            skipDetection = True
        else:
            skipDetection = False
        self.skipCounter += 1
        allvecs, boxes = recognizer.getRepFromString(imgstring, self.SCALE_FACTOR, skipDetection)
        endTime = time.time()

        results = []
        for i in range(0, len(boxes)):
            resStr = serializeArray(boxes[i]) + "," + self.recog(allvecs[i])
            results.append(resStr)
        
        return results

    # deserialize and load face DB
    def deserializeDB(self, string):
        self.fdb.deserialize(string)
        self.fdb.store(self.FACE_DB_FILE)
        self.vectors = self.fdb.getVectors()
        if self.SVM_MODE:
            self.retrain()

    # callback for image processing
    def mainServiceCallback(self, ch, method, properties, body):
        frameNum, data = self.splitFrame(body)
        self.currFrame = int(frameNum)
        results = self.getResults(data)
        if len(results)==0:
            results = [ "none,none,0,none" ]

        if frameNum == "-1":
            responseType = "2" #DB recognition request
        else:
            responseType = "1"
        msg = responseType + ";" + self.IDENTIFIER + ";" + str(self.currFrame) + ";" + ";".join(results)
        ch.basic_publish(exchange='',
                              routing_key='feedback-'+self.WORKER_GROUP_NAME,
                              body=msg)

    # callback for broadcast processing (discover and serialized DB)
    def broadcastCallback(self, ch, method, properties, body):
       if len(body)<=1:
           return
       if body[0]=="0":
           print "Responding to discovery request."
           ch.basic_publish(exchange='',
                              routing_key='feedback-'+self.WORKER_GROUP_NAME,
                              body="0,"+self.IDENTIFIER)
       elif body[0]=="1":
           self.deserializeDB(body[1:])


    # init for image processing
    def mainServiceInit(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.MQ_SERVER_IP, port=self.MQ_SERVER_PORT, credentials=self.MQ_CREDENTIALS))
        channel = connection.channel()

        channel.queue_declare(queue=self.IDENTIFIER)
        channel.queue_declare(queue="feedback-"+self.WORKER_GROUP_NAME)

        channel.basic_consume(self.mainServiceCallback,
                          queue=self.IDENTIFIER,
                          no_ack=True)

        channel.start_consuming()

    # init for broadcast processing (discover and serialized DB)
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

# main function to start the server, server must be MQServer instance
def runserver(server):
    while 1:
        try:
            server.run()
        except KeyboardInterrupt:
            print "\nClosing\n"
            break
