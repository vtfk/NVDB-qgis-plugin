import os
class nvdbpresets:
    def __init__(self):
        self.presets = []
        self.objects = []
        self.areaType = []
        self.area = []
        self.road = []

    def getPresets(self):
        return self.presets

    def getObjects(self):
        return self.objects

    def getAreaType(self):
        return self.areaType

    def getArea(self):
        return self.area

    def getRoad(self):
        return self.road

    def setPresets(self, p):
        self.presets = p

    def setObjects(self, o):
        self.objects = o

    def setAreaType(self, at):
        self.areaType = at

    def setArea(self, a):
        self.area = a

    def setRoad(self, r):
        self.road = r


pre = nvdbpresets()


def getAllPresetData():
    relPath = os.path.dirname(os.path.abspath(__file__))
    presetPath = os.path.join(relPath, "presets")
    presetList = []
    objectList = []
    areaTypeList = []
    areaList = []
    roadList = []
    for file in os.listdir(presetPath):
        filepath = os.path.join(presetPath, file)
        f = open(filepath, "r")
        info = f.read()
        infosplit = info.split(";")
        presetList.append(info)
        objectList.append(infosplit[0])
        areaTypeList.append(infosplit[1])
        areaList.append(infosplit[2])
        roadList.append(infosplit[3])
    addPresetData(presetList)
    addObjectsData(objectList)
    addAreaTypeData(areaTypeList)
    addAreaData(areaList)
    addRoadData(roadList)


def addPresetData(index):
    pre.setPresets(index)


def addObjectsData(index):
    pre.setObjects(index)


def addAreaTypeData(index):
    pre.setAreaType(index)


def addAreaData(index):
    pre.setArea(index)


def addRoadData(index):
    pre.setRoad(index)


def returnPresetData():
    return pre.getPresets()


def returnObjectData():
    return pre.getObjects()


def returnAreaTypeData():
    return pre.getAreaType()


def returnAreaData():
    return pre.getArea()


def returnRoadData():
    return pre.getRoad()
