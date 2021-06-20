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
    'has_github_no_ci' : { '$and' : [
        { 'github' : True },
        {'$or' : [ { 'travis_ci' : { '$exists' : False } }, { 'travis_ci' : False}] },
        {'$or' : [ { 'github_actions' : { '$exists' : False } }, { 'github_actions' : False}] }
    ]},
    'has_github_no_travis_ci' : { '$and' : [ { 'github' : True }, {'$or' : [ { 'travis_ci' : { '$exists' : False } }, { 'travis_ci' : False}] }] },
    'has_github_no_coveralls' : { '$and' : [ { 'github' : True }, {'$or' : [ { 'coveralls' : { '$exists' : False } }, { 'coveralls' : False}] }] },
}

for field in ['tox', 'appveyor', 'editconfig', 'dockbot', 'landscape', 'coveralls', 'travis_ci', 'circleci', 'github', 'gitlab', 'bitbucket', 'github_actions']:
    cases['has_' + field] = { field : True}
    cases['no_' + field] = {'$or' : [ { field : { '$exists' : False } }, { field : False}] }

# Combined:
cases['has_vcs']             = { '$or': [ cases['has_github'], cases['has_bitbucket'], cases['has_gitlab'] ] }
cases['no_vcs']              = { '$and': [ cases['no_github'], cases['no_gitlab'], cases['no_bitbucket']] }
cases['has_vcs_no_license']  = { '$and' : [ cases['has_vcs'], cases['no_license'] ] }
cases['has_vcs_has_license'] = { '$and' : [ cases['has_vcs'], cases['has_license'] ] }
cases['has_vcs_no_author']   = { '$and' : [ cases['has_vcs'], cases['no_author'] ] }
cases['has_vcs_has_author']  = { '$and' : [ cases['has_vcs'], cases['has_author'] ] }
cases['has_vcs_no_summary']   = { '$and' : [ cases['has_vcs'], cases['no_summary'] ] }

def get_client_and_db():
    log = logging.getLogger('PyDigger.common')
    log.info("get_client_and_db")
    config = read_config()
    log.info("username: {} server: {}".format(config["username"], config["server"] ))
    if config["username"] and config["password"]:
        connector = "mongodb://{}:{}@{}".format(config["username"], config["password"], config["server"])
    else:
        connector = "mongodb://{}".format(config["server"])
    client = MongoClient(connector, connectTimeoutMS=5000, socketTimeoutMS=5000)
    return client, client[ config["dbname"] ]

def get_db():
    client, db = get_client_and_db()
    return db

def remove_db():
    #client = MongoClient()
    #config = read_config()
    client, db = get_client_and_db()
    client.drop_database(db)

def get_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_source_dir():
    return get_root() + "/src"

def remove_package(name):
    log = logging.getLogger('PyDigger.common')
    db = get_db()
    doc = db.packages.find_one({'name' : name})
    if not doc:
        exit("Could not find package {}".format(name))
    res = db.packages.remove({'name' : name})
    log.info("res: {}".format(res))

def show_package(name):
    log = logging.getLogger('PyDigger.common')
    db = get_db()
    doc = db.packages.find_one({'name' : name})
    if not doc:
        exit("Could not find package {}".format(name))
    log.info("doc: {}".format(doc))

def read_config():
    log = logging.getLogger('PyDigger.common')
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
    last_day = now - datetime.timedelta(days = 1)
    last_week = now - datetime.timedelta(days = 7)
    stats = {
        'total'  : db.packages.count_documents({}),
        'hour'   : db.packages.count_documents({"upload_time": { '$gte': last_hour } }),
        'day'    : db.packages.count_documents({"upload_time": { '$gte': last_day } }),
        'week'   : db.packages.count_documents({"upload_time": { '$gte': last_week } }),
    }
    return stats

def get_latests_from_cache():
    db = get_db()
    data = db.cache.find_one({'_id': 'latests'})
    if not data:
        data = get_latests()
    return data

def get_flake8_report():
    # db = get_db()
    return {}
# https://stackoverflow.com/questions/16492891/mongodb-aggregation-get-counts-of-key-value-pairs
#     map = function () {
#        for (k in this.flake8_score) {
#                emit( { key: k, flake8: this.flake8_score[k]}, 1 );
#        }
#     }

# reduce = function (k, values) {
#     result = 0;
#     values.forEach( function(v) { result += v; } );
#        return result;
# }

# db.packages.find({},{_id:0,flake8:1}).pretty()

# db.packages.mapReduce(map, reduce, {out:{inline:1}})
#     data = db.packages.count_documents({ 'flake8.E221' :  })


def get_stats_from_cache():
    db = get_db()
    stats = db.cache.find_one({'_id': 'stats'})
    if not stats:
        stats = get_stats()
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

def update_cache():
    stats = get_stats()
    latests = get_latests()
    db = get_db()
    db.cache.update_one({ '_id': 'stats' }, { '$set': stats }, upsert=True)
    db.cache.update_one({ '_id': 'latests' }, { '$set': latests }, upsert=True)
