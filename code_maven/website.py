from flask import Flask, render_template, redirect, abort
import time
#import json
#import re

app = Flask(__name__)

@app.route("/")
def main():
    return "Hello World at " + time.time().__str__()
