from flask import Flask, render_template, redirect, request, url_for, Response, jsonify
from datetime import datetime
import hashlib
import json
import logging
import math
import os
import pymongo
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import PyDigger.common
from PyDigger.common import cases, get_stats, get_latests


max_license_length = 50

app = Flask(__name__)

def setup():
    global db
    db = PyDigger.common.get_db()

    # set up logging
    if os.environ.get('PYDIGGER_TEST'):
        app.logger.setLevel(logging.DEBUG)
    root = PyDigger.common.get_root()
    logdir = root + '/log'
    if not os.path.exists(logdir):
        os.mkdir(logdir)
    handler = logging.FileHandler(logdir + '/app.log')
    handler.setLevel(logging.ERROR)
    app.logger.addHandler(handler)
    app.logger.info("setup")


if not os.environ.get('PYDIGGER_SKIP_SETUP'):
    setup()


@app.template_filter()
def commafy(value):
    return '{:,}'.format(value)


def gravatar(email):
    if email is None:
        return ''
    return hashlib.md5(email.strip().lower().encode('utf8')).hexdigest()


def get_int(field, default):
    value = request.args.get(field, default)
    try:
        value = int(value)
    except Exception:
        value = default
    return value


for field in ['tox', 'appveyor', 'editconfig', 'dockbot', 'landscape', 'coveralls', 'travis_ci', 'circleci']:
    cases['has_' + field] = { field : True}
    cases['no_' + field] = {'$or' : [ { field : { '$exists' : False } }, { field : False}] }

@app.route("/api/0/recent")
def api_recent():
    query = {}
    skip = 0
    limit = 20
    data = db.packages.find(query).sort([("upload_time", pymongo.DESCENDING)]).skip(skip).limit(limit)
    my = []
    for entry in data:
        my.append({
            'home_page': entry.get('home_page'),
            'name': entry['name'],
        })
    app.logger.info("api_recent")
    app.logger.info(my)
    #return "OK"
    return jsonify(my)

@app.route("/author/<name>")
@app.route("/keyword/<keyword>")
@app.route("/search/<word>")
@app.route("/search")
@app.route("/")
def main(word = '', keyword = '', name = ''):
    latest = get_latests()

    total_indexed = db.packages.count_documents({})
    limit = get_int('limit', 20)
    page = get_int('page', 1)
    query = {}
    q = request.args.get('q', '').strip()
    license = request.args.get('license', '').strip()
    if limit == 0:
        limit = 20

#    keyword = request.args.get('keyword', '')

    word = word.replace('-', '_')
    if (word in cases):
        query = cases[word]
        q = ''

    if keyword:
        query = { 'split_keywords' : keyword }
        q = ''

    if name != '':
        query = {'author': name}
        q = ''

    if q != '':
        query = {'$or' : [ {'name' : { '$regex' : q, '$options' : 'i'}}, { 'split_keywords' : q.lower() } ] }

    if license != '':
        if license == '__long__':
            this_regex = '.{' + str(max_license_length) + '}'
            query = {'$and' : [ {'license': {'$exists': True} }, { 'license' : { '$regex': this_regex } }] }
        elif license == '__empty__':
            query = {'$and' : [ {'license': {'$exists': True} }, { 'license' : '' }] }
        else:
            query = {'license' : license}
        if license == 'None':
            query = {'license' : None}

    skip = max(limit * (page - 1), 0)
    data = db.packages.find(query).sort([("upload_time", pymongo.DESCENDING)]).skip(skip).limit(limit)
#    total_found = db.packages.find(query).count()
    total_found = db.packages.count_documents(query)
    count = db.packages.count_documents(query, limit=limit)

    if name and total_found > 0:
        gravatar_code = gravatar(data[0].get('author_email'))
    else:
        gravatar_code = None

    return render_template('main.html',
        title = "PyDigger - unearthing stuff about Python",
        page = {
            'total_indexed' : total_indexed,
            'total_found' : total_found,
            'count' : count,
            'pages' : int(math.ceil(total_found / limit)),
            'current' : page,
            'limit' : limit,
        },
        latest = latest,
        data = data,
        search_q = q,
        author = name,
        gravatar = gravatar_code,
    )

@app.route("/keywords")
def keywords():
    packages = db.packages.find({'$and' : [{'split_keywords' : { '$exists' : True }}, { 'split_keywords': {'$not' : { '$size' : 0}}}] }, {'split_keywords': True})
    # TODO: tshis should be really improved
    keywords = {}
    total = 0
    for p in packages:
        for k in p['split_keywords']:
            if k not in keywords:
                keywords[k] = 0
            keywords[k] += 1
            total += 1
    words = [ (k, keywords[k]) for k in keywords.keys() ]
    words.sort(key=lambda f:f[1])
    words.reverse()

    return render_template('keywords.html',
        title = "Keywords of Python packages on PyPI",
        words = words,
        total = total,
        unique = len(words),
        stats = get_stats(),
    )

@app.route("/licenses")
def licenses():
    licenses = db.packages.group(['license'], {}, { 'count' : 0}, 'function (curr, result) { result.count++; }' )
    licenses.sort(key=lambda f:f['count'])
    licenses.reverse()
    for licence in licenses:
        licence['count'] = int(licence['count'])
        if licence['license'] is None:
            licence['license'] = 'None'
        if len(licence['license']) > max_license_length:
            licence['long'] = True

    return render_template('licenses.html',
        title = "Licenses of Python packages on PyPI",
        total = db.packages.find().count(),
        has_license = db.packages.find(cases['has_license']).count(),
        no_license = db.packages.find(cases['no_license']).count(),
        licenses = licenses,
    )

@app.route("/stats")
def stats():
    stats = get_stats()

    return render_template('stats.html',
        title = "PyDigger - Statistics",
        stats = stats,
    )

@app.route("/pypi/<name>")
def pypi(name):
    package = db.packages.find_one({'lcname' : name.lower()})
    if not package:
        return render_template('404.html',
            title = name + " not found",
            package_name = name), 404

    if package['name'] != name:
        return redirect(url_for('pypi', name = package['name']))

    # if 'keywords' in package and package['keywords']:
    #     package['keywords'] = package['keywords'].split(' ')
    # else:
    #     package['keywords'] = []

    return render_template('package.html',
        title = name,
        package = package,
        gravatar = gravatar(package.get('author_email')),
        raw = json.dumps(package, indent=4, default = json_converter)
    )

@app.route("/robots.txt")
def robots():
    #robots = '''Sitemap: http://pydigger.com/sitemap.xml
    robots = '''Disallow: /static/*
'''
    return Response(robots, mimetype='text/plain')

# @app.route("/sitemap.xml")
# def sitemap():
#     xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
#     xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
#     today = datetime.now().strftime("%Y-%m-%d")
#
#     for page in ('', 'stats', 'about'):
#         xml += '  <url>\n'
#         xml += '    <loc>http://pydigger.com/{}</loc>\n'.format(page)
#         xml += '    <lastmod>{}</lastmod>\n'.format(today)
#         xml += '  </url>\n'
#
#     # fetch all
#     xml += '</urlset>\n'
#     return Response(xml, mimetype='aplication/xml')


@app.route("/about")
def about():
    return render_template('about.html',
        title = "About PyDigger"
    )

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

def json_converter(o):
    if isinstance(o, datetime):
        return o.__str__()
