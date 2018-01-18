#!/usr/bin/env python2

import sys
import dlib


DLIB_MODEL = "models/dlib/shape_predictor_68_face_landmarks.dat"
NN_MODEL = "models/openface/nn4.small2.v1.t7"

IMG_DIM = 96

CUDA = False

import time

start = time.time()

import argparse
import cv2
import os
import pickle

import numpy as np
from sklearn.mixture import GMM
import openface

fileDir = os.path.dirname(os.path.realpath(__file__))
modelDir = os.path.join(fileDir, '..', 'models')
dlibModelDir = os.path.join(modelDir, 'dlib')
openfaceModelDir = os.path.join(modelDir, 'openface')


DEF_ALIGN = openface.AlignDlib(DLIB_MODEL)
DEF_NET = openface.TorchNeuralNet(NN_MODEL, imgDim=IMG_DIM, cuda=CUDA)



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


def getRep(bgrImg, align, net):
    scaleDown = True
    start = time.time()
    if bgrImg is None:
        raise Exception("Unable to load image/frame")

    rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)
    #rgbImg = cv2.resize(rgbImg, None, fx=0.5, fy=0.5)

    print("  + Original size: {}".format(rgbImg.shape))
    print("Loading the image took {} seconds.".format(time.time() - start))

    start = time.time()

    # Get all bounding boxes
    # optimizer

    if scaleDown:
        try:
            scaleFactor = 0.5
            bbImg = cv2.resize(rgbImg, None, fx=scaleFactor, fy=scaleFactor) 
            bb = align.getAllFaceBoundingBoxes(bbImg)
            bb = scaleRects(bb, 1.0/scaleFactor)
            print "BBLEN", len(bb)
        except Exception as ex:
            print ex
    else:
        bb = align.getAllFaceBoundingBoxes(rgbImg)

    if bb is None:
        # raise Exception("Unable to find a face: {}".format(imgPath))
        return None
    
    print("bb", bb)
    print("Face detection took {} seconds.".format(time.time() - start))

    start = time.time()

    alignedFaces = []
    for box in bb:
        alignedFaces.append(
            align.align(
                IMG_DIM,
                rgbImg,
                box,
                landmarkIndices=openface.AlignDlib.OUTER_EYES_AND_NOSE))

    if alignedFaces is None:
        raise Exception("Unable to align the frame")

    print("Alignment took {} seconds.".format(time.time() - start))

    start = time.time()

    reps = []
    for alignedFace in alignedFaces:
        reps.append(net.forward(alignedFace))

    print("Neural network forward pass took {} seconds.".format(time.time() - start))

    # print (reps)
    arrayBoxes = bbToArray(bb)
    return reps, arrayBoxes




def getRepFromString(imgstring):
	st = time.time()
	arr = np.fromstring(imgstring, np.uint8)
	img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

	print "imload took:", time.time()-st

	
	
	vectors = getRep(img, DEF_ALIGN, DEF_NET)

	print "grfs took:", time.time()-st
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
