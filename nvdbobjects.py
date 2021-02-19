import requests
import json


def getNvdb():
    response = requests.get('https://nvdbapiles-v3.utv.atlas.vegvesen.no/vegobjekttyper')
    return json.loads(response.text)


"""Henter navn på alle vegobjektene"""


def getNames():
    nameList = []

    for obj in getNvdb():
        name = obj['navn']
        nameList.append(name)

    return nameList


"""Henter kategorier"""


def getCategories():
    categoryList = []

    for obj in getNvdb():
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
    for obj in getNvdb():
        if selected_item == obj['navn']:
            item_id = obj['id']
        else:
            pass

    return item_id
