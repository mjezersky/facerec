

def recArea(rectangle):
    return (rectangle.right() - rectangle.left())*(rectangle.bottom() - rectangle.top())

def recRatio(recA, recB):
    #print "--ratio"
    intersection = max(0, min(recA.right(), recB.right()) - max(recA.left(), recB.left())) * max(0, min(recA.bottom(), recB.bottom()) - max(recA.top(), recB.top()));
    intersection = float(intersection)
    #print "--union"
    union = recArea(recA) + recArea(recB) - intersection;
    return (float(intersection)/float(union))

def recSimilar(recA, recB, threshold):
    return recRatio(recA, recB) >= threshold

def recEqual(recA, recB):
    return recA.top()==recB.top() and recA.left()==recB.left() and recA.bottom()==recB.bottom() and recA.right()==recB.right()


class Tracker():
    def __init__(self, rectangle, dlibTracker):
        self.rectangle = rectangle
        self.dlibTracker = dlibTracker

    def start(self, image):
        #print "----tstart"
        self.dlibTracker.start_track(image, self.rectangle)

    def update(self, image):
        #print "----tupd"
        res = self.dlibTracker.update(image)
        self.rectangle = self.dlibTracker.get_position()
        return res

    def __eq__(self, tr):
        return recEqual(self.rectangle, tr.rectangle)



class Tracking():
    def __init__(self, dlibTrackerCreator):
        self.dlibTrackerCreator = dlibTrackerCreator
        
        self.lastFrameRectangles = []
        self.lastImage = None
        self.trackers = []
        self.trackedRectangles = []
        
        self.threshold = 0.20
        self.trackerThreshold = 4.9

    def reset(self):
        self.lastFrameRectangles = []
        self.lastImage = None
        self.trackers = []
        self.trackedRectangles = []

    def remove(self, tracker):
        self.trackers.remove(tracker)

    def getRectangles(self):
        #print "TRGET", len(self.trackedRectangles)
        return self.trackedRectangles


    def updateTrackers(self, rectangles, image):
        #print "--upda", len(rectangles)
        self.lastImage = image
        self.lastFrameRectangles = rectangles
        #print "chk", len(self.lastFrameRectangles)
        self.trackedRectangles = []
        for tr in self.trackers:
            score = tr.update(image)
            print "TRSC:", score
            if score >= self.trackerThreshold:
                #print "TRADD"
                self.trackedRectangles.append(tr.rectangle)
            else:
                self.remove(tr)
            

    def feed(self, rectangles, image):
        #print "--fi"
        # first image
        if self.lastImage is None:
            self.lastImage = image
            self.lastFrameRectangles = rectangles
            #print "-- LFR SET TO ", len(self.lastFrameRectangles)
            return

        #if len(rectangles)==0 and len(self.trackers)==0:
        #    return

        #print "--rec", len(self.lastFrameRectangles)
        # search whether box is already tracked
        for rec in rectangles:
            for tr in self.trackers:
                # if tracked and found again, remove it, update all and return
                if recSimilar(tr.rectangle, rec, self.threshold):
                    self.remove(tr)
                    #self.updateTrackers(rectangles, image)
                    #return

        #print "--lost"
        #print len(self.lastFrameRectangles), len(rectangles)
        # not tracked yet, compare last two frames for lost boxes
        lost = []
        for recA in self.lastFrameRectangles:
            found = False
            for recB in rectangles:
                if recSimilar(recA, recB, self.threshold):
                    found = True
                    break
            if not found:
                # box was lost between last two frames, assign for tracking
                lost.append(recA)

        #print len(lost)
        #print "--tra"
        # begin tracking all lost boxes
        for rec in lost:
            tr = Tracker(rec, self.dlibTrackerCreator())
            tr.start(self.lastImage)
            self.trackers.append(tr)

        # update all trackers
        self.updateTrackers(rectangles, image)
            

