

def recArea(rectangle):
    return (rectangle.right - rectangle.left)*(rectangle.bottom - rectangle.top)

def recRatio(recA, recB):
    print "--ratio"
    intersection = max(0, min(recA.right, recB.right) - max(recA.left, recB.left)) * max(0, min(recA.bottom, recB.bottom) - max(recA.top, recB.top));
    intersection = float(intersection)
    print "--union"
    union = recArea(recA) + recArea(recB) - intersection;
    return (float(intersection)/float(union))

def recSimilar(recA, recB, threshold):
    return recRatio(recA, recB) >= threshold

def recEqual(recA, recB):
    return recA.top==recB.top and recA.left==recB.left and recA.bottom==recB.bottom and recA.right==recB.right


class Tracker():
    def __init__(self, rectangle, dlibTracker):
        self.rectangle = rectangle
        self.dlibTracker = dlibTracker

    def start(self, image):
        self.dlibTracker.start_track(image, self.rectangle)

    def update(self, image):
        self.dlibTracker.update(image)
        self.rectangle = self.dlibTracker.get_position()

    def __eq__(self, tr):
        return recEqual(self.rectangle, tr.rectangle)



class Tracking():
    def __init__(self, dlibTrackerCreator):
        self.dlibTrackerCreator = dlibTrackerCreator
        
        self.lastFrameRectangles = []
        self.lastImage = None
        self.trackers = []
        self.trackedRectangles = []
        
        self.threshold = 0.50
        self.trackerThreshold = 0.50

    def reset(self):
        self.lastFrameRectangles = []
        self.lastImage = None
        self.trackers = []
        self.trackedRectangles = []

    def remove(self, tracker):
        self.trackers.remove(tracker)

    def getRectangles(self):
        return self.trackedRectangles


    def updateTrackers(self, rectangles, image):
        print "--upda"
        self.lastImage = image
        self.lastFrameRectangles = rectangles
        self.trackedRectangles = []
        for tr in self.trackers:
            score = tr.update(image)
            print "!!!!!!!!!! TRSC:", score
            if score >= self.trackerThreshold:
                self.trackedRectangles.append(tr.rectangle)
            else:
                self.remove(tr)
            

    def feed(self, rectangles, image):
        print "--fi"
        # first image
        if self.lastImage is None:
            self.lastImage = image
            self.lastFrameRectangles = rectangles
            return

        print "--rec"
        # search whether box is already tracked
        for rec in rectangles:
            for tr in self.trackers:
                # if tracked and found again, remove it, update all and return
                if recSimilar(tr.rectangle, rec, self.threshold):
                    self.remove(tr)
                    self.updateTrackers(rectangles, image)
                    return

        print "--lost"
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

        print "--tra"
        # begin tracking all lost boxes
        for rec in lost:
            tr = Tracker(rec, self.dlibTrackerCreator())
            tr.start(self.lastImage)
            trackers.append(tr)

        # update all trackers
        self.updateTrackers(rectangles, image)
            

