from flask import Flask, render_template, redirect, abort
import time, json, os
from pymongo import MongoClient
#import re

app = Flask(__name__)

client = MongoClient()
db = client.pydigger

@app.route("/")
def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #with open(root + '/recent.json', 'r') as f:
    #    data = json.load(f)
    data = db.packages.find()

    return render_template('main.html',
        title = "PyDigger - Learning about programming in Python",
        data = data,
    )

@app.route("/about")
def about():
    return render_template('about.html',
        title = "About PyDigger"
    )
