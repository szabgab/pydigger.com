from __future__ import print_function
import urllib2, json, re, sys
import xml.etree.ElementTree as ET
from pymongo import MongoClient


client = MongoClient()
db = client.pydigger

def warn(msg):
    sys.stderr.write(msg + "\n")

#my_entries = []
def save_entry(e):
    #my_entries.append(e)
    #print(e)
    # TODO make sure we only add newer version!
    # Version numbers I've seen:
    # 1.0.3
    # 20160325.161225
    # 0.2.0.dev20160325161211
    # 3.1.0a12
    # 2.0.0.dev11

    doc = db.packages.find_one({'name' : e['name']})
    if doc:
        #print(doc)
        db.packages.remove({'name' : e['name']})
    db.packages.insert(e)


def get_travis_status(builds):
    if not builds:
        return 'unknown'
    state = builds[0]['state']
    #print('state: ' + state)

    if re.search(r'cancel|pend', state):
        return state
    if re.search(r'error', state):
        return 'error'
    if re.search(r'fail', state):
        return 'failing'
    if re.search('pass', state):
        return 'passing'
    return 'unknown'

def get_latest():
    latest_url = 'https://pypi.python.org/pypi?%3Aaction=rss'
    #print('Fetching ' + latest_url)
    try:
        f = urllib2.urlopen(latest_url)
        rss_data = f.read()
        f.close()
    except urllib2.HTTPError as e:
        warn(e + ' while fetching ' + latest_url)
        exit
    #print(rss_data)
    return rss_data

def save_json():
    f = open('recent.json', 'w')
    f.write(json.dumps(my_entries))
    f.close()


def check_github(o, user, package):
    travis_yml_url = 'https://raw.githubusercontent.com/' + user + '/' + package + '/master/.travis.yml'
        #print(travis_yml_url)
    try:
        f = urllib2.urlopen(travis_yml_url)
        travis_yml = f.read()
        f.close()
    except urllib2.HTTPError as e:
        #print(e, 'while fetching', travis_yml_url)
        #o['cm']['error'] = 'Could not find .travis.yml in the GitHub repository'
        o['travis-ci'] = False
        return()

    # if there is a travis.yml check the status
    travis_url = 'https://api.travis-ci.org/repos/' + user + '/' + package + '/builds';
    #print(travis_url)
    try:
        req = urllib2.Request(travis_url)
        req.add_header('Accept', 'application/vnd.travis-ci.2+json')
        f = urllib2.urlopen(req)
        travis_data_json = f.read()
        f.close()
    except urllib2.HTTPError as e:
        #print(e, 'while fetching', travis_url)
        o['error'] = 'Could not get status from Travis-CI API'
        return()

    travis_data = json.loads(travis_data_json)
    #print(travis_data)
    #return();
    if not travis_data or 'builds' not in travis_data or len(travis_data['builds']) == 0:
        o['error'] = 'Could not find builds in data received from travis-ci.org'
        return()

    o['travis_status'] = get_travis_status(travis_data['builds'])
    return()

def main():
    rss_data = get_latest()

    root = ET.fromstring(rss_data)

    for item in root.iter('item'):
        o = {}
        title = item.find('title').text.split(' ')
        o['name'] = title[0]
        o['version'] = title[1]
        # we might want to later verify from the package_data that these are the real name and version
        o['link'] = item.find('link').text
        o['short_description'] = item.find('description').text
        o['pubDate'] = item.find('pubDate').text

        url = o['link'] + '/json';
        #print(url)
        try:
            f = urllib2.urlopen(url)
            json_data = f.read()
            f.close()
        except urllib2.HTTPError as e:
            #print(e, 'while fetching', url)
            o['error'] = 'Could not fetch details of PyPi package'
            save_entry(o)
            continue

        package_data = json.loads(json_data)
        #if 'description' in package_data['info']:
        #    del package_data['info']['description'] # its too big and I am not sure what to do with it anyway, or maybe not
        #print(package_data)

        #o['package'] = package_data
        if 'info' in package_data:
            info = package_data['info']
            if 'home_page' in info:
                o['home_page'] = info['home_page']

            for f in ['maintainer', 'docs_url', 'requires_python']:
                if f in info:
                    o[f] = info[f]


        if 'home_page' in o:
            try:
                match = re.search(r'^https?://github.com/([^/]+)/([^/]+)/?$', o['home_page'])
            except Exception as e:
                warn(e)
                warn(o['home_page'])

            if match:
                o['github'] = True
                check_github(o, match.group(1), match.group(2))
            else:
                o['github'] = False
                #o['error'] = 'Home page URL is not GitHub'
            #print(o)
        save_entry(o)
