from pymongo import MongoClient
import os
import yaml

def get_db():
    config = read_config()
    if config["username"] and config["password"]:
        connector = "mongodb://{}:{}@{}".format(config["username"], config["password"], config["server"])
    else:
        connector = "mongodb://{}".format(config["server"])
    client = MongoClient(connector)
    return client[ config["dbname"] ]

def remove_db():
    client = MongoClient()
    config = read_config()
    client.drop_database(config["dbname"])

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

def show_package(name):
    db = get_db()
    doc = db.packages.find_one({'name' : name})
    if not doc:
        exit("Could not find package {}".format(name))
    print(doc)

def read_config():
    config_file = os.environ.get('PYDIGGER_CONFIG')
    if config_file is None:
        root = os.path.dirname(os.path.dirname(__file__))
        config_file = os.path.join(root, "config.yml")

    print(config_file)
    with open(config_file) as fh:
        config = yaml.load(fh, Loader=yaml.BaseLoader)
    return config
