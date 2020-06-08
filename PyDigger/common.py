from pymongo import MongoClient
import datetime
import os
import yaml
import logging
import re

cases = {
    'no_summary'   : { '$or' : [{'summary' : ''}, {'summary' : None}] },
    'no_license'   : { '$or' : [{'license' : None}, {'license' : ''}] },
    'has_license'  : { '$and' : [{'license' : {'$not' : {'$eq' : None}}}, {'license' : { '$not' : { '$eq' : '' }}}] },
    'no_github'    : { 'github' : False },
    'has_github'   : { 'github' : True },
    'no_docs_url'  : { '$or' : [ { 'docs_url' : { '$exists' : False} }, { 'docs_url' : None} ] },
    'has_docs_url' : { 'docs_url' : { '$not' : { '$eq' : None }}},
    'no_requires_python' : { '$or' : [ { 'requires_python' : { '$exists' : False} }, { 'requires_python' : None}, { 'requires_python' : ''} ] },
    'has_requires_python' : { '$and' : [ { 'requires_python' : { '$exists' : True} }, { 'requires_python' : { '$regex': '.' }} ] },
    'no_cheesecake_installability_id' : { '$or' : [ { 'cheesecake_installability_id' : { '$exists' : False} }, { 'cheesecake_installability_id' : None}, { 'cheesecake_installability_id' : ''} ] },
    'no_cheesecake_kwalitee_id' : { '$or' : [ { 'cheesecake_kwaliteee_id' : { '$exists' : False} }, { 'cheesecake_kwaliteee_id' : None}, { 'cheesecake_kwalitee_id' : ''} ] },
    'no_cheesecake_documentation_id' : { '$or' : [ { 'cheesecake_documentation_id' : { '$exists' : False} }, { 'cheesecake_documentation_id' : None}, { 'cheesecake_documentation_id' : ''} ] },
    'no_author' : { '$or' : [ { 'author' : { '$exists' : False} }, { 'author' : None}, { 'author' : ''}, { 'author' : 'UNKNOWN'} ] },
    'has_author' : { '$and' : [ {'author' : { '$not' : { '$eq' : None} } }, {'author' : { '$not' : { '$eq' : ''} }}, {'author' : { '$not' : {'$eq' : 'UNKNOWN'}}} ] },
    'no_keywords'    : {'$or' : [ { 'keywords' : "" }, { 'keywords' : None } ] },
    'has_keywords'   : { '$and' : [ { 'keywords' : { '$not' : { '$eq' : "" } } }, { 'keywords' : { '$not' : { '$eq' : None } } } ] },
    'has_comma_separated_keywords'   : { 'keywords' : { '$regex' : ',' } },
    'has_no_comma_keywords'   : { '$and' : [ { 'keywords' : { '$not' : { '$eq' : "" } } }, { 'keywords' : { '$not' : { '$eq' : None } } }, {'keywords' : {'$not' : re.compile(',')}} ] },
    'has_requirements'   : { 'requirements' : { '$exists' : True, '$ne' : [] }},
    'no_requirements'   : {'$or' : [ { 'requirements' : { '$exists' : False } }, { 'requirements' : { '$eq' : [] } } ] },
    'has_bugtrack_url'   : { '$and' : [{ 'bugtrack_url' : { '$exists' : True } }, { 'bugtrack_url' : { '$regex': '.'} }  ] },
    'no_bugtrack_url'   : { '$or' : [{ 'bugtrack_url' : { '$exists' : False } }, { 'bugtrack_url' : None }, { 'bugtrack_url' : '' } ] },
    'has_github_no_travis_ci' : { '$and' : [ { 'github' : True }, {'$or' : [ { 'travis_ci' : { '$exists' : False } }, { 'travis_ci' : False}] }] },
    'has_github_no_coveralls' : { '$and' : [ { 'github' : True }, {'$or' : [ { 'coveralls' : { '$exists' : False } }, { 'coveralls' : False}] }] },
}


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
    log = logging.getLogger('fetch')
    db = get_db()
    doc = db.packages.find_one({'name' : name})
    if not doc:
        exit("Could not find package {}".format(name))
    res = db.packages.remove({'name' : name})
    log.info("res: {}".format(res))

def show_package(name):
    log = logging.getLogger('fetch')
    db = get_db()
    doc = db.packages.find_one({'name' : name})
    if not doc:
        exit("Could not find package {}".format(name))
    log.info("doc: {}".format(doc))

def read_config():
    log = logging.getLogger('fetch')
    config_file = os.environ.get('PYDIGGER_CONFIG')
    if config_file is None:
        root = os.path.dirname(os.path.dirname(__file__))
        config_file = os.path.join(root, "config.yml")

    log.info("config_file: {}".format(config_file))
    with open(config_file) as fh:
        config = yaml.load(fh, Loader=yaml.BaseLoader)
    return config

def get_latests():
    db = get_db()
    now = datetime.datetime.now()
    last_hour = now - datetime.timedelta(hours = 1)
    stats = {
        'total'  : db.packages.count_documents({}),
        'hour'   : db.packages.count_documents({"upload_time": { '$gte': last_hour } }),
    }
    return stats

def get_stats():
    db = get_db()
    stats = {
        'total'        : db.packages.count_documents({}),
    }
    for word in cases:
        stats[word] = db.packages.count_documents(cases[word])

    #github_not_exists = db.packages.find({ 'github' : { '$not' : { '$exists': True }}}).count()
    return stats
