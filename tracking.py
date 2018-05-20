# File: 	tracking.py
# Author: 	Matous Jezersky	


# returns an area of a rectangle
def recArea(rectangle):
    return (rectangle.right() - rectangle.left())*(rectangle.bottom() - rectangle.top())

# returns the percentual overlap of two rectangles of area of their union
def recRatio(recA, recB):
    intersection = max(0, min(recA.right(), recB.right()) - max(recA.left(), recB.left())) * max(0, min(recA.bottom(), recB.bottom()) - max(recA.top(), recB.top()));
    intersection = float(intersection)
    union = recArea(recA) + recArea(recB) - intersection;
    return (float(intersection)/float(union))

# compares two rectangles for similarity with tolerance threshold
def recSimilar(recA, recB, threshold):
    return recRatio(recA, recB) >= threshold

# compares two rectangles for exact match
def recEqual(recA, recB):
    return recA.top()==recB.top() and recA.left()==recB.left() and recA.bottom()==recB.bottom() and recA.right()==recB.right()


class Tracker():
    def __init__(self, rectangle, dlibTracker):
        self.rectangle = rectangle
        self.dlibTracker = dlibTracker

        self.gainThreshold = 5 # max gain until considered stuck
        self.lowestScore = 100 # default big value

    # initializes the tracker with an image
    def start(self, image):
        self.dlibTracker.start_track(image, self.rectangle)

    # updates the tracker with an image
    def update(self, image):
        res = self.dlibTracker.update(image)
        self.rectangle = self.dlibTracker.get_position()

        gain = res-self.lowestScore

        # considered stuck, return score 0
        if gain > self.gainThreshold:
            return 0

        if res < self.lowestScore:
            self.lowestScore = res

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
        self.trackerThreshold = 4.8

    # resets and clears all trackers
    def reset(self):
        self.lastFrameRectangles = []
        self.lastImage = None
        self.trackers = []
        self.trackedRectangles = []

    # removes a tracker
    def remove(self, tracker):
        self.trackers.remove(tracker)

    # returns currently tracked rectangles
    def getRectangles(self):
        return self.trackedRectangles

    # updates all trackers with an image, takes a list of rectangles from detector as an argument
    # rectangles will be empty if detection was skipped, this method is called automatically by feed
    def updateTrackers(self, rectangles, image):
        self.lastImage = image
        self.lastFrameRectangles = rectangles
        self.trackedRectangles = []
        for tr in self.trackers:
            score = tr.update(image)
            if score >= self.trackerThreshold:
                self.trackedRectangles.append(tr.rectangle)
            else:
                self.remove(tr)
            
    # feeds an image to the trackers, takes a list of rectangles from detector as an argument
    # rectangles will be empty if detection was skipped
    def feed(self, rectangles, image):
        # first image
        if self.lastImage is None:
            self.lastImage = image
            self.lastFrameRectangles = rectangles
            return

        # search whether box is already tracked
        for rec in rectangles:
            for tr in self.trackers:
                # if tracked and found again, remove it, update all and return
                if recSimilar(tr.rectangle, rec, self.threshold):
                    self.remove(tr)
                    #self.updateTrackers(rectangles, image)
                    #return

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

        # begin tracking all lost boxes
        for rec in lost:
            tr = Tracker(rec, self.dlibTrackerCreator())
            tr.start(self.lastImage)
            self.trackers.append(tr)

        # update all trackers
        self.updateTrackers(rectangles, image)
            

