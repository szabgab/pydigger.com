from flask import Flask, render_template, redirect, abort
import time, json, os
#import re

app = Flask(__name__)

@app.route("/")
def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(root + '/recent.json', 'r') as f:
        data = json.load(f)

    return render_template('main.html', data = data)
