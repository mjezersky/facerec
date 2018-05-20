
# File: 	recognizer.py
# Author: 	Matous Jezersky

import sys
import dlib
import tracking
import argparse
import cv2
import os
import pickle

import numpy as np
import openface
import time

import opencv_detector


DLIB_MODEL = "models/dlib/shape_predictor_68_face_landmarks.dat"
#DLIB_MODEL = "models/dlib/shape_predictor_5_face_landmarks.dat"
NN_MODEL = "models/openface/nn4.small2.v1.t7"
IMG_DIM = 96
TRACKING_ENABLED = True
SCALE_DOWN = True
DETECTOR_GRAYSCALE = True

CUDA = False

DLIB_LANDMARKS_MODEL = "models/dlib/shape_predictor_5_face_landmarks.dat"
DLIB_FACEREC_MODEL = "models/dlib/dlib_face_recognition_resnet_model_v1.dat"

# adapter for dlib neural network
class DlibNetAdapter():
    def __init__(self):
        self.sp = dlib.shape_predictor(DLIB_LANDMARKS_MODEL)
        self.net = dlib.face_recognition_model_v1(DLIB_FACEREC_MODEL)
        self.lastimg = None

    def forward(self, aligned):
        return np.array(self.net.compute_face_descriptor(self.lastimg, aligned))

    def align(self, a, img, box, landmarkIndices):
        self.lastimg = img
        return self.sp(img, box)

DLIB_NN = DlibNetAdapter()

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


# scale rectangle to factor
def scaleRect(rect, factor):
    r_l = int(rect.left()*factor)
    r_t = int(rect.top()*factor)
    r_r = int(rect.right()*factor)
    r_b = int(rect.bottom()*factor)
    return dlib.rectangle(r_l,r_t,r_r,r_b)

# convert dlib rectangle to array
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

# scale multiple rectangles
def scaleRects(rects, factor):
    res = dlib.rectangles()
    for rect in rects:
        res.append(scaleRect(rect, factor))
    return res


# get feature vectors and bounding boxes tuple for detected faces
def getRep(bgrImg, detector, align, net, tracker, scaleFactor, skipDetection):

    rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)

    # scale down images for detection
    if SCALE_DOWN and not skipDetection:
        try:
            bbImg = cv2.resize(rgbImg, None, fx=scaleFactor, fy=scaleFactor)
            # convert image to grayscale for faster detection
            if DETECTOR_GRAYSCALE:
                bbImg = cv2.cvtColor(bbImg, cv2.COLOR_RGB2GRAY) 
            bb = detector.getAllFaceBoundingBoxes(bbImg)
            bb = scaleRects(bb, 1.0/scaleFactor)
            #print "BBLEN", len(bb)
        except Exception as ex:
            print ex
    elif not skipDetection:
        # convert to grayscale even when not scaling down
        if DETECTOR_GRAYSCALE:
            bbImg = cv2.cvtColor(rgbImg, cv2.COLOR_RGB2GRAY)
        else:
            bbImg = rgbImg

        bb = detector.getAllFaceBoundingBoxes(bbImg)
    	if bb is None:
            bb = dlib.rectangles()
    else:
        bb = dlib.rectangles()
    
    # tracking
    try:
        if not (tracker is None):
            tracker.feed(bb, rgbImg)
            trrec = tracker.getRectangles()
            newbb = dlib.rectangles()
            for r in bb:
                newbb.append(r)
            for r in trrec:
                dlr = dlib.rectangle(long(r.left()), long(r.top()), long(r.right()), long(r.bottom()))
                newbb.append(dlr)
            bb = newbb
    except KeyboardInterrupt as err:
        return None


    # align detected faces
    alignedFaces = []
    for box in bb:
        alignedFaces.append( align.align(IMG_DIM, rgbImg, box, landmarkIndices=openface.AlignDlib.OUTER_EYES_AND_NOSE))

    if alignedFaces is None:
        raise Exception("Unable to align the frame")

    # get feature vectors
    reps = []
    for alignedFace in alignedFaces:
        reps.append(net.forward(alignedFace))

    arrayBoxes = bbToArray(bb)
    # return tuple of array of feature vectors and array of bounding boxes
    return reps, arrayBoxes




def getRepFromString(imgstring, scaleFactor, skipDetection):
    # decode image
    arr = np.fromstring(imgstring, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
	
    #OpenFace variant:
    #vectorsAndBoxes = getRep(img, DEF_DETECTOR, DEF_ALIGN, DEF_NET, TRACKER, scaleFactor, skipDetection)

    #dlib variant:
    vectorsAndBoxes = getRep(img, DEF_DETECTOR, DLIB_NN, DLIB_NN, TRACKER, scaleFactor, skipDetection)

    return vectorsAndBoxes
