from flask import Flask, render_template, redirect, abort
import time, json, os
from pymongo import MongoClient
import pymongo
#import re

app = Flask(__name__)

client = MongoClient()
db = client.pydigger

@app.route("/")
def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #with open(root + '/recent.json', 'r') as f:
    #    data = json.load(f)
    total = db.packages.find().count()
    limit = 20
    data = db.packages.find().sort([("pubDate", pymongo.DESCENDING)]).limit(limit)

    return render_template('main.html',
        title = "PyDigger - Learning about programming in Python",
        total = total,
        count = limit,
        data = data,
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
