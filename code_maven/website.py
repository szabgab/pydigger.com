from flask import Flask, render_template, redirect, abort, request
import time, json, os
from pymongo import MongoClient
import pymongo
#import re

app = Flask(__name__)

client = MongoClient()
db = client.pydigger
#root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route("/search")
@app.route("/")
def main():
    total = db.packages.find().count()
    limit = 20
    query = {}
    q = request.args.get('q', '')
    no_summary = request.args.get('no_summary', '')
    no_license = request.args.get('no_license', '')
    if no_summary:
        query['$or'] = [ { 'summary' : ''}, { 'summary' : None } ]
        q = ''

    if no_license:
        query['$or'] = [ { 'license' : ''}, { 'license' : None } ]
        q = ''

    if q != '':
        query['name'] = { '$regex' : q, '$options' : 'i'}

    data = db.packages.find(query).sort([("pubDate", pymongo.DESCENDING)]).limit(limit)
    count = db.packages.find(query).count()

    return render_template('main.html',
        title = "PyDigger - Learning about programming in Python",
        total = total,
        count = min(count, limit),
        data = data,
        search = {
            'q' : q,
            'no_summary' : no_summary,
            'no_license' : no_license,
         },
    )

@app.route("/stats")
def stats():
    total = db.packages.find().count()
    no_summary = db.packages.find({ '$or' : [{'summary' : ''}, {'summary' : None}] }).count()
    no_license = db.packages.find({ '$or' : [{'license' : ''}, {'license' : None}] }).count()
    #licenses = db.packages.group({ key: {license : 1}, reduce: function (curr, result) { result.count++; }, initial: { count : 0} });
    licenses = db.packages.group(['license'], {}, { 'count' : 0}, 'function (curr, result) { result.count++; }' );
    for l in licenses:
        l['count'] = int(l['count'])

    return render_template('stats.html',
        title = "PyDigger - Statistics",
        total = total,
        no_summary = no_summary,
        no_license = no_license,
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
        package = package
    )


@app.route("/about")
def about():
    return render_template('about.html',
        title = "About PyDigger"
    )

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404
