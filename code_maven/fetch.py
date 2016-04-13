from __future__ import print_function
import argparse
import base64
import urllib2, json, re, sys
import xml.etree.ElementTree as ET
from pymongo import MongoClient
import logging
from datetime import datetime
from github3 import login
import requirements

parser = argparse.ArgumentParser()
parser.add_argument('--verbose', help='Set verbosity level', action='store_true')
parser.add_argument('--rss', help='fetch the RSS feed', action='store_true')
parser.add_argument('--update', help='update the entries: new - not yet updated, rss - the ones received via rss')
args = parser.parse_args()

# Updated:
# 1) All the entries that don't have last_update field
# 2) All the entries that were updated more than N days ago
# 3) All the entries that were updated in the last N days ??

with open('github-token') as fh:
    token = fh.readline().strip()
github = login(token=token)

client = MongoClient()
db = client.pydigger
logging.basicConfig(level= logging.DEBUG if args.verbose else logging.WARNING)
log=logging.getLogger('fetch')

def main():
    log.debug("Staring")

    if args.rss:
        get_rss()

    if args.update:
        #args.update == 'new' or args.update == 'old'):
        if args.update == 'all':
            packages = db.packages.find()
        elif re.search(r'^\d+$', args.update):
            packages = db.packages.find().sort([('pubDate', 1)]).limit(int(args.update))
        else:
            print("Not implemented yet")
            packages = []

        for p in packages:
            log.debug("Updating Package: {} {}".format(p['name'], p['pubDate']) )
            get_details(p)

    log.debug("Finished")




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

def check_github(entry):
    log.debug("check_github user='{}', project='{}".format(entry['github_user'], entry['github_project']))

    repo = github.repository(entry['github_user'], entry['github_project'])
    if not repo:
        log.error("Could not fetch GitHub repository for {}".format(entry['name']))
        entry['error'] = "Could not fetch GitHub repository"
        return

    log.debug("default_branch: ", repo.default_branch)

    # get the last commit of the default branch
    branch = repo.branch(repo.default_branch)
    if not branch:
        log.error("Could not fetch GitHub branch {} for {}".format(repo.default_branch, entry['name']))
        entry['error'] = "Could not fetch GitHub branch"
        return

    last_sha = branch.commit.sha
    log.debug("last_sha: ", last_sha)
    t = repo.tree(last_sha)
    entry['travis_ci'] = False
    entry['coveralis'] = False
    for e in t.tree:
        if e.path == '.travis.yml':
                entry['travis_ci'] = True
        if e.path == '.coveragerc':
                entry['coveralis'] = True
        if e.path == 'requirements.txt':
                entry['requirements'] = []
                fh = urllib2.urlopen(e.url)
                as_json = fh.read()
                file_info = json.loads(as_json)
                content = base64.b64decode(file_info['content'])
                for req in requirements.parse(content):
                    log.debug("requirements: {} {} {}".format(req.name, req.specs, req.extras))
                    # we cannot use the req.name as a key in the dictionary as some of the package names have a . in them
                    # and MongoDB does not allow . in fieldnames.
                    entry['requirements'].append({ 'name' : req.name, 'specs' : req.specs })
        # test_requirements.txt
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
        if 'keywords' in info and info['keywords']:
            entry['split_keywords'] = info['keywords'].split(' ')
        else:
            entry['split_keywords'] = []

    if 'urls' in package_data:
        entry['urls'] = package_data['urls']

    if 'home_page' in entry and entry['home_page'] != None:
        try:
            match = re.search(r'^https?://github.com/([^/]+)/([^/]+)/?$', entry['home_page'])
        except Exception as e:
            warn('Error while tying to match home_page:' + entry['home_page'])
            warn(e)

        if match:
            entry['github'] = True
            entry['github_user'] = match.group(1)
            entry['github_project'] = match.group(2)
            check_github(entry)
        else:
            entry['github'] = False
            #entry['error'] = 'Home page URL is not GitHub'
        log.debug("entry: ", entry)
    save_entry(entry)

def get_package(entry):
    log.debug('get_package')
    if not 'urls' in entry:
        return
