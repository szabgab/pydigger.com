from pymongo import MongoClient
import os

def get_db():
    client = MongoClient()
    return(client.pydigger)

def remove_db():
    client = MongoClient()
    client.drop_database('pydigger')

def get_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_source_dir():
    return get_root() + "/src"
