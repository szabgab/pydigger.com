from __future__ import print_function
import argparse
import urllib2, json, re, sys
import xml.etree.ElementTree as ET
from pymongo import MongoClient
import logging
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('--verbose', help='Set verbosity level', action='store_true')
parser.add_argument('--rss', help='fetch the RSS feed', action='store_true')
parser.add_argument('--update', help='update the entries: new - not yet updated, rss - the once received via rss')
args = parser.parse_args()

# Updated:
# 1) All the entries that don't have last_update field
# 2) All the entries that were updated more than N days ago
# 3) All the entries that were updated in the last N days ??


client = MongoClient()
db = client.pydigger
logging.basicConfig(level= logging.DEBUG if args.verbose else logging.WARNING)
log=logging.getLogger('fetch')

def main():
    log.debug("Staring")

    if args.rss:
        get_rss()

    if args.update:
        # fetch names from database
        pass


def warn(msg):
    #sys.stderr.write("ERROR: %s\n" % msg)
    log.exception(msg)

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
        warn('Error while fetching ' + latest_url)
        warn(e)
        exit
    #print(rss_data)
    return rss_data

def save_json():
    f = open('recent.json', 'w')
    f.write(json.dumps(my_entries))
    f.close()


def check_github(entry, user, package):
    travis_yml_url = 'https://raw.githubusercontent.com/' + user + '/' + package + '/master/.travis.yml'
        #print(travis_yml_url)
    try:
        f = urllib2.urlopen(travis_yml_url)
        travis_yml = f.read()
        f.close()
    except urllib2.HTTPError as e:
        #print(e, 'while fetching', travis_yml_url)
        #entry['cm']['error'] = 'Could not find .travis.yml in the GitHub repository'
        entry['travis_ci'] = False
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
        entry['error'] = 'Could not get status from Travis-CI API'
        return()

    travis_data = json.loads(travis_data_json)
    #print(travis_data)
    #return();
    if not travis_data or 'builds' not in travis_data or len(travis_data['builds']) == 0:
        entry['error'] = 'Could not find builds in data received from travis-ci.org'
        return()

    entry['travis_status'] = get_travis_status(travis_data['builds'])
    return()

def get_rss():
    log.debug("get_rss")
    rss_data = get_latest()

    root = ET.fromstring(rss_data)

    for item in root.iter('item'):
        entry = {}
        title = item.find('title').text.split(' ')
        log.debug("Seen {}".format(title))
        entry['name'] = title[0]
        entry['version'] = title[1]

        doc = db.packages.find_one({'name' : entry['name']})
        if doc:
            continue
        # add package
        log.debug("Processing {}".format(title))
        # we might want to later verify from the package_data that these are the real name and version
        entry['link'] = item.find('link').text
        entry['summary'] = item.find('description').text
        entry['pubDate'] = datetime.strptime(item.find('pubDate').text, "%d %b %Y %H:%M:%S %Z")
        save_entry(entry)
        if args.update and args.update == 'rss':
            get_details(entry)
    return


def get_details(entry):
    log.debug("get_details of " + entry['name'])
    url = entry['link'] + '/json';
    #print(url)
    try:
        f = urllib2.urlopen(url)
        json_data = f.read()
        f.close()
    except urllib2.HTTPError as e:
        #print(e, 'while fetching', url)
        entry['error'] = 'Could not fetch details of PyPi package'
        save_entry(entry)
        return

    package_data = json.loads(json_data)
    #print(package_data)

    #entry['package'] = package_data
    if 'info' in package_data:
        info = package_data['info']
        if 'home_page' in info:
            entry['home_page'] = info['home_page']

        # package_url  we can deduct this from the name, can't we?
        # version ???
        # _pypi_hidden
        # _pypi_ordering
        # release_url
        # downloads - a hash, but as we are monitoring recent uploads, this will be mostly 0
        # classifiers - an array of stuff
        # name
        # releases
        # urls
        for f in ['maintainer', 'docs_url', 'requires_python', 'maintainer_email',
        'cheesecake_code_kwalitee_id', 'cheesecake_documentation_id', 'cheesecake_installability_id',
        'keywords', 'author', 'author_email', 'download_url', 'platform', 'description', 'bugtrack_url',
        'license', 'summary']:
            if f in info:
                entry[f] = info[f]


    if 'home_page' in entry and entry['home_page'] != None:
        try:
            match = re.search(r'^https?://github.com/([^/]+)/([^/]+)/?$', entry['home_page'])
        except Exception as e:
            warn('Error while tying to match home_page:' + entry['home_page'])
            warn(e)

        if match:
            entry['github'] = True
            check_github(entry, match.group(1), match.group(2))
        else:
            entry['github'] = False
            #entry['error'] = 'Home page URL is not GitHub'
        log.debug(entry)
    save_entry(entry)
