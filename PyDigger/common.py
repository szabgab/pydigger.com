from pymongo import MongoClient

def get_db():
    client = MongoClient()
    return(client.pydigger)
