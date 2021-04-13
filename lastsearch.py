class lastsearch:
    def __init__(self):
        self.area = None
        self.areaType = None
        self.road = None

    def getArea(self):
        return self.area

    def getAreaType(self):
        return self.areaType

    def getRoad(self):
        return self.road

    def setArea(self, a):
        self.area = a

    def setAreaType(self, at):
        self.areaType = at

    def setRoad(self, r):
        self.road = r

last = lastsearch()

def setLastSearch(a, at, r):
    last.setArea(None)
    last.setAreaType(None)
    last.setRoad(None)
    last.setArea(a)
    last.setAreaType(at)
    last.setRoad(r)

def getLastSearch():
    info = [last.getArea(), last.getAreaType(), last.getRoad()]
    return info