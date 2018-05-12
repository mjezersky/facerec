#!/usr/bin/env python2

import sys
import dlib
import tracking
import argparse
import cv2
import os
import pickle

import numpy as np
from sklearn.mixture import GMM
import openface
import time

import opencv_detector

LOGNAME = "log_"+str(long(time.time()))+".txt"


DLIB_MODEL = "models/dlib/shape_predictor_68_face_landmarks.dat"
#DLIB_MODEL = "models/dlib/shape_predictor_5_face_landmarks.dat"
NN_MODEL = "models/openface/nn4.small2.v1.t7"
IMG_DIM = 96
TRACKING_ENABLED = False
SCALE_DOWN = True
SCALE_FACTOR = 0.6
DETECTOR_GRAYSCALE = True


CUDA = False

start = time.time()



class FRStat():
    def __init__(self):
        self.data = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.idata = [0.0, 0.0, 0.0, 0.0, 0.0]

    def rnd(self, x):
        y = x*1000
        return int(y)

    def rndmap(self):
        self.idata = map(lambda x: self.rnd(x), self.data)

    def write(self):
        self.rndmap()
        f = open(LOGNAME, "a")
        f.write(str(self.idata[0])+"#"+str(self.idata[1])+"#"+str(self.idata[2])+"#"+str(self.idata[3])+"#"+str(self.idata[4])+"\n")
        f.close()
        self.data = [0.0, 0.0, 0.0, 0.0, 0.0]


FRS = FRStat()

fileDir = os.path.dirname(os.path.realpath(__file__))
modelDir = os.path.join(fileDir, '..', 'models')
dlibModelDir = os.path.join(modelDir, 'dlib')
openfaceModelDir = os.path.join(modelDir, 'openface')


DEF_ALIGN = openface.AlignDlib(DLIB_MODEL) 
DEF_DETECTOR = DEF_ALIGN
#DEF_DETECTOR = opencv_detector
DEF_NET = openface.TorchNeuralNet(NN_MODEL, imgDim=IMG_DIM, cuda=CUDA)
if TRACKING_ENABLED:
    TRACKER = tracking.Tracking(dlib.correlation_tracker)
else:
    TRACKER = None


def scaleRect(rect, factor):
    r_l = int(rect.left()*factor)
    r_t = int(rect.top()*factor)
    r_r = int(rect.right()*factor)
    r_b = int(rect.bottom()*factor)
    return dlib.rectangle(r_l,r_t,r_r,r_b)

def bbToArray(bb):
    outArr = []
    for box in bb:
        boxArr=[]
        boxArr.append(box.left())
        boxArr.append(box.top())
        boxArr.append(box.right())
        boxArr.append(box.bottom())
        outArr.append(boxArr)
    return outArr 


def scaleRects(rects, factor):
    res = dlib.rectangles()
    for rect in rects:
        res.append(scaleRect(rect, factor))
    return res


def getRep(bgrImg, detector, align, net, tracker, skipDetection):
    start = time.time()
    if bgrImg is None:
        raise Exception("Unable to load image/frame")

    rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)
    #rgbImg = cv2.resize(rgbImg, None, fx=0.5, fy=0.5)

    #print("  + Original size: {}".format(rgbImg.shape))
    FRS.data[0] += time.time()-start
    #print("Loading the image took {} seconds.".format(FRS.data[0]))

    # Get all bounding boxes
    # optimizer

    if SCALE_DOWN and not skipDetection:
        try:
            start = time.time()
            scaleFactor = SCALE_FACTOR
            bbImg = cv2.resize(rgbImg, None, fx=scaleFactor, fy=scaleFactor)
            if DETECTOR_GRAYSCALE:
                bbImg = cv2.cvtColor(bbImg, cv2.COLOR_RGB2GRAY) 
            bb = detector.getAllFaceBoundingBoxes(bbImg)
            bb = scaleRects(bb, 1.0/scaleFactor)
            FRS.data[1] = time.time() - start
            #print "BBLEN", len(bb)
        except Exception as ex:
            print ex
    elif not skipDetection:
        start = time.time()
        if DETECTOR_GRAYSCALE:
            bbImg = cv2.cvtColor(rgbImg, cv2.COLOR_RGB2GRAY)
        else:
            bbImg = rgbImg
        bb = detector.getAllFaceBoundingBoxes(bbImg)
        FRS.data[1] = time.time() - start

    	if bb is None:
            bb = dlib.rectangles()
    else:
        bb = dlib.rectangles()
    
    #print("bb", bb)
    start = time.time()

    try:
        if not (tracker is None):
            start = time.time()
            tracker.feed(bb, rgbImg)
            trrec = tracker.getRectangles()
            newbb = dlib.rectangles()
            for r in bb:
                newbb.append(r)
            for r in trrec:
                dlr = dlib.rectangle(long(r.left()), long(r.top()), long(r.right()), long(r.bottom()))
                newbb.append(dlr)
            bb = newbb
            FRS.data[4] = time.time()-start
    except KeyboardInterrupt as err:
        return None

    start = time.time()

    alignedFaces = []
    for box in bb:
        #print "BOX", box.left(), box.top(), box.right(), box.bottom()
        alignedFaces.append(
            align.align(
                IMG_DIM,
                rgbImg,
                box,
                landmarkIndices=openface.AlignDlib.OUTER_EYES_AND_NOSE))

    if alignedFaces is None:
        raise Exception("Unable to align the frame")

    FRS.data[2] = time.time()-start #align

    start = time.time()

    reps = []
    for alignedFace in alignedFaces:
        reps.append(net.forward(alignedFace))

    FRS.data[3] = time.time()-start # NN

    # print (reps)
    arrayBoxes = bbToArray(bb)
    return reps, arrayBoxes




def getRepFromString(imgstring, skipDetection):
	st = time.time()
	arr = np.fromstring(imgstring, np.uint8)
	img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

	FRS.data[0] = time.time()-st #imload

	
	
	vectors = getRep(img, DEF_DETECTOR, DEF_ALIGN, DEF_NET, TRACKER, skipDetection)

        FRS.write()
	#print "grfs took:", time.time()-st
	return vectors


def compareVectors(vec1, vec2):
	return np.dot(vec1, vec2)


if __name__ == "__main__":
	imgA = cv2.imread(TESTIMG_A)
	imgB = cv2.imread(TESTIMG_B)


	align = openface.AlignDlib(DLIB_MODEL)
	net = openface.TorchNeuralNet(NN_MODEL, imgDim=IMG_DIM, cuda=CUDA)

	vectorsA = getRep(imgA, align, net)
	vectorsB = getRep(imgB, align, net)
	if len(vectorsA)>0 and len(vectorsB)>0:
            print "Difference:", np.dot(vectorsA[0], vectorsB[0])
