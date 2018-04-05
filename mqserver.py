#!/usr/bin/python

import facerecprotocol as frp
import dbhandler as dbh
import svmclassifier as svm
import neuralnet as nnet
import time
import numpy as np
import pika
import threading


IDENTIFIER = "default"
MQ_SERVER_IP = "10.0.0.1"
MQ_CREDENTIALS = pika.PlainCredentials('facerec', 'facerec')

currFrame = "0"

def serializeArray(arr):
    return "#".join( map(lambda x: str(x), arr) )

def recog(vec, vectors, hashTable):
    if vec is None:
        return "NO_FACE_DETECTED"
    preds = svm.predict(vec,smodel)
    pred = str(vectors.keys()[np.argmax(preds)])
    return pred + "," + str(np.argmax(preds)) + "," + serializeArray(vec)
    #return pred+"/"+dbh.query(vec, vectors, hashTable)+"("+str(preds)+")"
    #vectors["M"] = vec
    #dbh.saveVectors(vectors, "filedb.p")
    #return(str(len(vec)))


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


#p = frp.FacerecProtocol()
#p.bind("0.0.0.0", 9000)
#p.listen(1)

try:
    vectors = dbh.loadVectors("filedb.p")
except:
    vectors = {}

print(vectors.keys())

htab = dbh.buildHashTable(vectors, 128)
smodel = svm.trainNewModel(vectors)


def splitFrame(framestr):
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

def getResults(imgstring):
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
    	resStr = serializeArray(boxes[i]) + "," + recog(allvecs[i], vectors, htab)
        results.append(resStr)
    
    return results

def deserializeDB():
    print "DB deserialize"

def mainServiceCallback(ch, method, properties, body):
    global currFrame
    print "got", len(body), "bytes"
    frameNum, data = splitFrame(body)
    currFrame = frameNum
    results = getResults(data)
    if len(results)==0:
        results = [ "none,none,0,none" ]
    print frameNum
    if frameNum == "-1":
        responseType = "2" #DB recognition request
        print "DB frame request"
    else:
        responseType = "1"
    msg = responseType + ";" + IDENTIFIER + ";" + str(currFrame) + ";" + ";".join(results)
    print "Publishing"
    ch.basic_publish(exchange='',
                          routing_key='feedback',
                          body=msg)

def broadcastCallback(ch, method, properties, body):
   print "got", len(body), "bytes"
   if len(body)<=1:
       return
   if body[0]=="0":
       print "Announcing 0"
       ch.basic_publish(exchange='',
                          routing_key='feedback',
                          body="0,"+IDENTIFIER)
   elif body[0]=="1":
       deserializeDB(body[1:])


def mainServiceInit():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_SERVER_IP, credentials=MQ_CREDENTIALS))
    channel = connection.channel()

    channel.queue_declare(queue=IDENTIFIER)
    channel.queue_declare(queue="feedback")

    channel.basic_consume(mainServiceCallback,
                      queue=IDENTIFIER,
                      no_ack=True)

    channel.start_consuming()

def broadcastInit():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_SERVER_IP, credentials=MQ_CREDENTIALS))
    channel = connection.channel()

    channel.exchange_declare(exchange='broadcast', exchange_type='fanout')
    channel.queue_declare(queue="feedback")
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange="broadcast", queue=queue_name)

    channel.basic_consume(broadcastCallback,
                      queue=queue_name,
                      no_ack=True)

    mq_recieve_thread = threading.Thread(target=channel.start_consuming)
    mq_recieve_thread.daemon = True
    mq_recieve_thread.start()


broadcastInit()
mainServiceInit()

while 0:
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


