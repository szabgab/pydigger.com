from datetime import datetime
from pymongo import MongoClient

# stop the cron job
# upload new code
# convert
# start cron job

client = MongoClient()
db = client.pydigger
all = db.packages.find()
for p in all:
    # print(p)
    print(p['pubDate'])
    d = datetime.strptime(p['pubDate'], "%d %b %Y %H:%M:%S %Z")
    db.packages.update({'_id': p['_id']}, {'$set': {'pubDate': d}})
    # print(db.packages.find_one({'_id' : p['_id']}))
    # print(d)
    # break
