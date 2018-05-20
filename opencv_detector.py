# File: 	opencv_detector.py
# Author: 	Matous Jezersky

# Adapter for opencv detector, instead of dlib


import numpy as np
import cv2
import dlib


face_cascade = cv2.CascadeClassifier("models/haarcascade.xml")

def getAllFaceBoundingBoxes(rgbimg):
    gimg = cv2.cvtColor(rgbimg, cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gimg, scaleFactor=1.1, minNeighbors=5)

    rects = dlib.rectangles()
    for (x,y,w,h) in faces:
        rects.append(dlib.rectangle(long(x),long(y),long(w-x),long(h-y)))
    return rects
