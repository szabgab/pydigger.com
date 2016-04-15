from __future__ import division
from flask import Flask, render_template, redirect, abort, request, url_for
import datetime
import hashlib
import json
import math
import os
import pymongo
import time

max_license_length = 50

app = Flask(__name__)

client = pymongo.MongoClient()
db = client.pydigger
#root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.template_filter()
def commafy(value):
        return '{:,}'.format(value)

def gravatar(email):
    if email == None:
        return ''
    return hashlib.md5(email.strip().lower()).hexdigest()


def get_int(field, default):
    value = request.args.get(field, default)
    try:
        value = int(value)
    except Exception:
        value = default
    return value

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
    'has_requirements'   : { 'requirements' : { '$exists' : True, '$ne' : [] }},
    'no_requirements'   : {'$or' : [ { 'requirements' : { '$exists' : False } }, { 'requirements' : { '$eq' : [] } } ] },
    'has_bugtrack_url'   : { '$and' : [{ 'bugtrack_url' : { '$exists' : True } }, { 'bugtrack_url' : { '$regex': '.'} }  ] },
    'no_bugtrack_url'   : { '$or' : [{ 'bugtrack_url' : { '$exists' : False } }, { 'bugtrack_url' : None }, { 'bugtrack_url' : '' } ] },
}


@app.route("/author/<name>")
@app.route("/keyword/<kw>")
@app.route("/search/<word>")
@app.route("/search")
@app.route("/")
def main(word = '', kw = '', name = ''):
    total_indexed = db.packages.find().count()
    limit = get_int('limit', 20)
    page = get_int('page', 1)
    query = {}
    q = request.args.get('q', '')
    license = request.args.get('license', '')

    word = word.replace('-', '_')
    if (word in cases):
        query = cases[word]
        q = ''

    if kw:
        import re
        regx = re.compile(kw)
        query = { 'keywords' : regx}
        q = ''

    if q != '':
        query['name'] = { '$regex' : q, '$options' : 'i'}

    if license != '':
        if license == '__long__':
            this_regex = '.{' + str(max_license_length) + '}'
            query = {'$and' : [ {'license': {'$exists': True} }, { 'license' : { '$regex': this_regex } }] }
        elif license == '__empty__':
            query = {'$and' : [ {'license': {'$exists': True} }, { 'license' : '' }] }
        else:
            query['license'] = license
        if license == 'None':
            query['license'] = None
    if name != '':
        query = {'author': name}


    data = db.packages.find(query).sort([("upload_time", pymongo.DESCENDING)]).skip(limit * (page-1)).limit(limit)
#    total_found = db.packages.find(query).count()
    total_found = data.count(with_limit_and_skip=False)
    count = data.count(with_limit_and_skip=True)

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
        data = data,
        search = {
            'q' : q,
        },
        author = name,
        gravatar = gravatar_code,
    )

@app.route("/licenses")
def licenses():
    #licenses = db.packages.group({ key: {license : 1}, reduce: function (curr, result) { result.count++; }, initial: { count : 0} });
    licenses = db.packages.group(['license'], {}, { 'count' : 0}, 'function (curr, result) { result.count++; }' );
    licenses.sort(key=lambda f:f['count'])
    licenses.reverse()
    for l in licenses:
        l['count'] = int(l['count'])
        if l['license'] == None:
            l['license'] = 'None'
        if len(l['license']) > max_license_length:
            l['long'] = True

    return render_template('licenses.html',
        title = "Licenses of Python packages on PyPI",
        total = db.packages.find().count(),
        has_license = db.packages.find(cases['has_license']).count(),
        no_license = db.packages.find(cases['no_license']).count(),
        licenses = licenses,
    )

@app.route("/stats")
def stats():
    stats = {
        'total'        : db.packages.find().count(),
    }
    for word in cases:
        stats[word] = db.packages.find(cases[word]).count()

    #github_not_exists = db.packages.find({ 'github' : { '$not' : { '$exists': True }}}).count()

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
