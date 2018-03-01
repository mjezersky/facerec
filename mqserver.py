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
MQ_SERVER_IP = "192.168.1.8"
MQ_CREDENTIALS = pika.PlainCredentials('facerec', 'facerec')

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



def getResult(imgstring):
    startTime = time.time()
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

    return boxStr+recog(res, vectors, htab)


def mainServiceCallback(ch, method, properties, body):
    print "got", len(body), "bytes"
    ch.basic_publish(exchange='',
                      routing_key='feedback',
                      body="1,"+IDENTIFIER+",0,none,0,"+getResult(body))

def discoveryCallback(ch, method, properties, body):
   print "got", len(body), "bytes"
   ch.basic_publish(exchange='',
                      routing_key='feedback',
                      body="0,"+IDENTIFIER)


def mainServiceInit():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_SERVER_IP, credentials=MQ_CREDENTIALS))
    channel = connection.channel()

    channel.queue_declare(queue=IDENTIFIER)
    channel.queue_declare(queue="feedback")

    channel.basic_consume(mainServiceCallback,
                      queue=IDENTIFIER,
                      no_ack=True)

    channel.start_consuming()

def discoveryInit():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_SERVER_IP, credentials=MQ_CREDENTIALS))
    channel = connection.channel()

    channel.exchange_declare(exchange='broadcast', exchange_type='fanout')
    channel.queue_declare(queue="feedback")
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange="broadcast", queue=queue_name)

    channel.basic_consume(discoveryCallback,
                      queue=queue_name,
                      no_ack=True)

    mq_recieve_thread = threading.Thread(target=channel.start_consuming)
    mq_recieve_thread.daemon = True
    mq_recieve_thread.start()


discoveryInit()
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


