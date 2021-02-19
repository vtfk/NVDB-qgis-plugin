import requests
import json


def getNvdb():
    response = requests.get('https://nvdbapiles-v3.utv.atlas.vegvesen.no/vegobjekttyper')
    return json.loads(response.text)


def getNames():
    nameList = []

    for obj in getNvdb():
        name = obj['navn']
        nameList.append(name)

    return nameList

def getCategories():
    categoryList = []

    for obj in getNvdb():
        cat = obj['kategorier']
        categoryList.append(cat)

    return categoryList

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
