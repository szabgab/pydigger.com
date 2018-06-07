from pymongo import MongoClient
import os
import yaml

def get_db():
    config = yaml.load("config.yml")
    connector = "mongodb://{}:{}@{}".format(config["username"], config["password"], config["server"])
    client = MongoClient(connector)
    return(client.pydigger)

def remove_db():
    client = MongoClient()
    client.drop_database('pydigger')

def get_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_source_dir():
    return get_root() + "/src"

def remove_package(name):
    db = get_db()
    doc = db.packages.find_one({'name' : name})
    if not doc:
        exit("Could not find package {}".format(name))
    res = db.packages.remove({'name' : name})
    print(res)

