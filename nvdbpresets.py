class nvdbpresets:
    def __init__(self):
        self.presets = None
        self.objects = None
        self.area = None
        self.road = None

    def getPresets(self):
        return self.presets

    def getObjects(self):
        return self.objects

    def getArea(self):
        return self.area

    def getRoad(self):
        return self.road

    def setPresets(self, p):
        self.presets = p

    def setObjects(self, o):
        self.objects = o

    def setArea(self, a):
        self.area = a

    def setRoad(self, r):
        self.road = r

pre = nvdbpresets()

def getAllPresetData():
    pass