from flask import Flask, render_template, redirect, abort
import time
import json
#import re

app = Flask(__name__)

@app.route("/")
def main():
    with open('recent.json', 'r') as f:
        data = json.load(f)

    return render_template('main.html', data = data)
