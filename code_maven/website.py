from __future__ import division
from flask import Flask, render_template, redirect, abort, request
import time, json, os, math
from pymongo import MongoClient
import pymongo
import datetime
#import re

app = Flask(__name__)

client = MongoClient()
db = client.pydigger
#root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_int(field, default):
    value = request.args.get(field, default)
    try:
        value = int(value)
    except Exception:
        value = default
    return value

@app.route("/search/<word>")
@app.route("/search")
@app.route("/")
def main(word = ''):
    total_indexed = db.packages.find().count()
    limit = get_int('limit', 20)
    page = get_int('page', 1)
    query = {}
    q = request.args.get('q', '')
    license = request.args.get('license', '')
    if word == 'no-summary':
        query['$or'] = [ { 'summary' : ''}, { 'summary' : None } ]
        q = ''

    if word == 'no-github':
        query['github'] = False
        q = ''

    if word == 'no-license':
        query['$or'] = [ { 'license' : ''}, { 'license' : None } ]
        q = ''

    if q != '':
        query['name'] = { '$regex' : q, '$options' : 'i'}

    if license != '':
        query['license'] = license
        if license == 'None':
            query['license'] = None


    data = db.packages.find(query).sort([("pubDate", pymongo.DESCENDING)]).skip(limit * (page-1)).limit(limit)
#    total_found = db.packages.find(query).count()
    total_found = data.count(with_limit_and_skip=False)
    count = data.count(with_limit_and_skip=True)

    return render_template('main.html',
        title = "PyDigger - Learning about programming in Python",
        page = {
            'total_indexed' : total_indexed,
            'total_found' : total_found,
            'count' : count,
            'pages' : int(math.ceil(total_found / limit)),
            'current' : page,
            'limit' : limit,
        },
        data = data,
        search = {
            'q' : q,
         },
    )

@app.route("/stats")
def stats():
    stats = {
        'total'        : db.packages.find().count(),
        'no_summary'   : db.packages.find({ '$or' : [{'summary' : ''}, {'summary' : None}] }).count(),
        'no_license'   : db.packages.find({ '$or' : [{'license' : ''}, {'license' : None}] }).count(),
        'no_github'    : db.packages.find({ 'github' : False }).count(),
        'has_github'   : db.packages.find({ 'github' : True }).count(),
        'no_docs_url'  : db.packages.find({ '$or' : [ { 'docs_url' : { '$exists' : False} }, { 'docs_url' : None} ] }).count(),
        'has_docs_url' : db.packages.find({ 'docs_url' : { '$not' : { '$eq' : None }}}).count()
    }

    #github_not_exists = db.packages.find({ 'github' : { '$not' : { '$exists': True }}}).count()

    #licenses = db.packages.group({ key: {license : 1}, reduce: function (curr, result) { result.count++; }, initial: { count : 0} });
    licenses = db.packages.group(['license'], {}, { 'count' : 0}, 'function (curr, result) { result.count++; }' );
    for l in licenses:
        l['count'] = int(l['count'])

    return render_template('stats.html',
        title = "PyDigger - Statistics",
        stats = stats,
        licenses = licenses,
    )



@app.route("/pypi/<name>")
def pypi(name):
    package = db.packages.find_one({'name' : name})
    if not package:
        return render_template('404.html',
            title = name + " not found",
            package_name = name), 404
    return render_template('package.html',
        title = name,
        package = package,
        raw = json.dumps(package, indent=4, default = json_converter)
    )

@app.route("/robots.txt")
def robots():
    return ''


@app.route("/about")
def about():
    return render_template('about.html',
        title = "About PyDigger"
    )

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

def json_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()
