import requests
import json

class nvdbobjects:
    def __init__(self):
        self.categories = None

    def getCategoryData(self):
        return self.categories

    def setCategoryData(self, c):
        self.categories = c

nvdb = nvdbobjects()

def getRequest(req):
    response = requests.get(req)
    return json.loads(response.text)

def getAllObjectData():
    mainReq = getRequest('https://nvdbapiles-v3.atlas.vegvesen.no/vegobjekttyper')
    nvdb.setCategoryData(mainReq)

def returnCategoryData():
    return nvdb.getCategoryData()


"""Henter navn på alle vegobjektene"""


def getNames():
    nameList = []

    for obj in returnCategoryData():
        name = obj['navn']
        nameList.append(name)

    return sorted(nameList)


"""Henter kategorier"""


def getCategories():
    categoryList = []

    for obj in returnCategoryData():
        cat = obj['kategorier']
        categoryList.append(cat)

    return categoryList


"""Sorterer kategoriene etter primærkategorier"""


def sortCategories():
    catList = getCategories()
    sortedCatList = []

    for i in range(len(catList)):
        for u in range(len(catList[i])):
            try:
                primatyCat = catList[i][u]['primærkategori']
                if primatyCat:
                    name = catList[i][u]['navn']
                    if name in sortedCatList:
                        pass
                    else:
                        sortedCatList.append(name)
                else:
                    pass
            except IndexError:
                print('no data')
    sortedCatList.append("Alle")
    return sorted(sortedCatList)


def getObjects():
    objList = []
    names = getNames()
    categories = getCategories()
    for i in range(len(categories)):
        for u in range(len(categories[i])):
            name = names[i]
            try:
                primatyCat = categories[i][u]['primærkategori']
                if primatyCat:
                    catName = categories[i][u]['navn']
                    currentObj = [name, catName]
                    objList.append(currentObj)
                else:
                    pass
            except IndexError:
                print('no data')

    return sorted(objList)


def getObjInCat(cat):
    objList = []
    for obj in getObjects():
        if cat == obj[1]:
            objList.append(obj[0])

    return objList


def getID(selected_item):
    item_id = 0
    for obj in returnCategoryData():
        if selected_item == obj['navn']:
            item_id = obj['id']
        else:
            pass

    return item_id
