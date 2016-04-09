from __future__ import print_function
from pymongo import MongoClient

# stop the cron job
# upload new code
# convert
# start cron job

client = MongoClient()
db = client.pydigger
all = db.packages.find()
for p in all:
    #print(p)
    print(p['name'])
    kws = []
    if 'keywords' in p:
        print("  ", p['keywords'])
        kw = p['keywords']
        if kw != None and kw != "":
            kws = kw.split(' ')
    print("  ", kws)
    db.packages.update({'_id' : p['_id']}, {'$set' : {'split_keywords' : kws}})
    #print(db.packages.find_one({'_id' : p['_id']}))
    #print(d)
#    break
