from pymongo import MongoClient
import re

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
    split_keywords = []
    if 'keywords' in p:
        kw = p['keywords']
        if kw is not None and kw != "":
            kw = kw.encode('utf-8')
            print("  ", kw)
            kw = kw.lower()
            if re.search(',', kw):
                split_keywords = kw.split(',')
            else:
                split_keywords = kw.split(' ')

    print("  ", split_keywords)
    db.packages.update({'_id' : p['_id']}, {'$set' : {'split_keywords' : split_keywords}})
    #print(db.packages.find_one({'_id' : p['_id']}))
    #print(d)
#    break
