import requests
import json


class nvdbareas:
    def __init__(self):
        self.fylke = None
        self.kommune = None
        self.kontrakt = None

    def getFylkeData(self):
        return self.fylke

    def getKommuneData(self):
        return self.kommune

    def getKontraktData(self):
        return self.kontrakt

    def setFylkeData(self, f):
        self.fylke = f

    def setKommuneData(self, k):
        self.kommune = k

    def setKontraktData(self, k):
        self.kontrakt = k


nvdb = nvdbareas()


def getRequest(req):
    response = requests.get(req)
    return json.loads(response.text)


def getAllData():
    mainReq = getRequest('https://nvdbapiles-v3.utv.atlas.vegvesen.no/omrader')
    reqList = []

    for obj in mainReq:
        link = obj['href']
        reqList.append(getRequest(link))

    nvdb.setFylkeData(reqList[0])
    nvdb.setKommuneData(reqList[1])
    nvdb.setKontraktData(reqList[3])


def getFylkeNavn():
    fylker = returnFylkeData()
    nameList = []
    for i in fylker:
        name = i['navn']
        nameList.append(name)
    return sorted(nameList)


def getKommuneNavn(index):
    kommuner = returnKommuneData()
    fylker = returnFylkeData()
    kommuneList = []
    fylkeID = None
    for i in fylker:
        if i['navn'] == index:
            fylkeID = i['nummer']
        else:
            pass
    for i in kommuner:
        if i['fylke'] == fylkeID:
            kommuneList.append(i['navn'])
        else:
            pass
    return sorted(kommuneList)


def getKontraktNavn(index):
    fylker = returnFylkeData()
    kontrakter = returnKontraktData()
    kontraktList = []
    fylkeID = None
    for i in fylker:
        if i['navn'] == index:
            fylkeID = i['nummer']
        else:
            pass
    for i in kontrakter:
        for u in i['fylker']:
            if u == fylkeID:
                kontraktList.append(i['navn'])
            else:
                pass

    return sorted(kontraktList)


def returnFylkeData():
    return nvdb.getFylkeData()


def returnKommuneData():
    return nvdb.getKommuneData()


def returnKontraktData():
    return nvdb.getKontraktData()
