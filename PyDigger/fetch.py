import argparse
import base64
import json
import logging
import re
import requirements
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from github3 import login

import PyDigger.common


parser = argparse.ArgumentParser()
parser.add_argument('--verbose', help='Set logging level to DEBUG', action='store_true')
parser.add_argument('--update', help='update the entries: rss - the ones received via rss; all - all of the packages already in the database')
parser.add_argument('--name', help='Name of the package to update')
parser.add_argument('--sleep', help='How many seconds to sleep between packages (Help avoiding the GitHub API limit)', type=float)
args = parser.parse_args()

requirements_fields = ['requirements', 'test_requirements']

# Updated:
# 1) All the entries that don't have last_update field
# 2) All the entries that were updated more than N days ago
# 3) All the entries that were updated in the last N days ??

class PyPackage(object):
    def __init__(self, name):
        self.lcname = name.lower()
        self.entry = {}

    def get_details(self):
        log.debug("get_details of " + self.lcname)

        url = 'https://pypi.python.org/pypi/' + self.lcname + '/json'
        log.debug("Fetching url {}".format(url))
        try:
            f = urllib.request.urlopen(url)
            json_data = f.read()
            f.close()
            #print(json_data)
        except (urllib.request.HTTPError, urllib.request.URLError):
            log.exception("Could not fetch details of PyPI package from '{}'".format(url))
            return
        package_data = json.loads(json_data)
        #log.debug('package_data: {}'.format(package_data))

        if 'info' in package_data:
            info = package_data['info']
            if 'home_page' in info:
                self.entry['home_page'] = info['home_page']

            # package_url  we can deduct this from the name
            # _pypi_hidden
            # _pypi_ordering
            # release_url
            # downloads - a hash, but as we are monitoring recent uploads, this will be mostly 0
            # classifiers - an array of stuff
            # releases
            # urls
            for f in ['name', 'maintainer', 'docs_url', 'requires_python', 'maintainer_email',
            'cheesecake_code_kwalitee_id', 'cheesecake_documentation_id', 'cheesecake_installability_id',
            'keywords', 'author', 'author_email', 'download_url', 'platform', 'description', 'bugtrack_url',
            'license', 'summary', 'version']:
                if f in info:
                    self.entry[f] = info[f]

            self.entry['split_keywords'] = []
            if 'keywords' in info:
                keywords = info['keywords']
                if keywords != None and keywords != "":
                    log.debug("keywords '{}'".format(keywords))
                    log.debug("keywords type '{}'".format(keywords.__class__.__name__))
                    #if keywords.__class__.__name__ == 'bytes':
                    #    keywords = keywords.decode('utf8')

                    #keywords = keywords.encode('utf-8')
                    keywords = keywords.lower()
                    if re.search(',', keywords):
                        self.entry['split_keywords'] = keywords.split(',')
                    else:
                        self.entry['split_keywords'] = keywords.split(' ')

        self.process_release(package_data)

        if 'home_page' in self.entry and self.entry['home_page'] != None:
            match = re.search(r'^https?://github.com/([^/]+)/([^/]+)/?$', self.entry['home_page'])
            if match:
                self.entry['github'] = True
                self.entry['github_user'] = match.group(1)
                self.entry['github_project'] = match.group(2)
            else:
                self.entry['github'] = False
                #entry['error'] = 'Home page URL is not GitHub'

        if self.entry['github']:
            try:
                self.check_github()
            except Exception:
                log.exception('Error while tying to get data from GitHub:' + self.entry['home_page'])

        self.entry['lcname'] = self.entry['name'].lower()
        self.download_pkg()
        self.save()


    def process_release(self, package_data):
        version = self.entry['version']
        if 'urls' in package_data:
            self.entry['urls'] = package_data['urls']
        if not 'releases' in package_data:
            log.error("There are no releases in package {} --- {}".format(self.lcname, package_data))
        elif not version in package_data['releases']:
            log.error("Version {} is not in the releases of package {} --- {}".format(version, self.lcname, package_data))
        elif len(package_data['releases'][version]) == 0:
            log.error("Version {} has no elements in the releases of package {} --- {}".format(version, self.lcname, package_data))
        else:
            # find the one that has python_version: "source",
            # actually we find the first one that has python_version: source
            # maybe there are more?
            source = package_data['releases'][version][0]
            for version_pack in package_data['releases'][version]:
                if 'python_version' in version_pack and version_pack['python_version'] == 'source':
                    if 'url' in version_pack:
                        self.entry['download_url'] = version_pack['url']
                    else:
                        log.error("Version {} has no download_url in the releases of package {} --- {}".format(version, self.lcname, package_data))
                    source = version_pack
                    break

                #url: https://pypi.python.org/packages/ce/c7/6431a8ba802bf93d611bfd53c05abcc078165b8aad3603d66c02a847af7d/codacy-coverage-1.2.10.tar.gz
                #filename: codacy-coverage-1.2.10.tar.gz
                #url: https://pypi.python.org/packages/84/85/5ce28077fbf455ddf0ba2506cdfdc2e5caa0822b8a4a2747da41b683fad8/purepng-0.1.3.zip

            if not 'upload_time' in source:
                log.error("upload_time is missing from version {} in the releases of package {} --- {}".format(version, self.name, package_data))
            else:
                upload_time = source['upload_time']
                self.entry['upload_time'] = datetime.strptime(upload_time, "%Y-%m-%dT%H:%M:%S")

    def check_github(self):
        log.debug("check_github user='{}', project='{}".format(self.entry['github_user'], self.entry['github_project']))

        repo = github.repository(self.entry['github_user'], self.entry['github_project'])
        if not repo:
            log.error("Could not fetch GitHub repository for {}".format(self.entry['name']))
            self.entry['error'] = "Could not fetch GitHub repository"
            return

        log.debug("default_branch: {}".format(repo.default_branch))

        # get the last commit of the default branch
        branch = repo.branch(repo.default_branch)
        if not branch:
            log.error("Could not fetch GitHub branch {} for {}".format(repo.default_branch, self.entry['name']))
            self.entry['error'] = "Could not fetch GitHub branch"
            return

        last_sha = branch.commit.sha
        log.debug("last_sha: {}".format(last_sha))
        t = repo.tree(last_sha)
        self.entry['travis_ci'] = False
        self.entry['coveralls'] = False
        for e in t.tree:
            if e.path == '.travis.yml':
                    self.entry['travis_ci'] = True
            if e.path == '.coveragerc':
                    self.entry['coveralls'] = True
            if e.path == 'tox.ini':
                    self.entry['tox'] = True # http://codespeak.net/tox/
            if e.path == 'circle.yml':
                    self.entry['circle'] = True # https://circleci.com/
            if e.path == 'appveyor.yml':
                    self.entry['appveyor'] = True # https://www.appveyor.com/
            if e.path == '.appveyor.yml':
                    self.entry['appveyor'] = True # https://www.appveyor.com/
            if e.path == '.editconfig':
                    self.entry['editconfig'] = True # http://editorconfig.org/
            if e.path == 'dockbot.json':
                    self.entry['dockbot'] = True # https://github.com/CauldronDevelopmentLLC/dockbot
            if e.path == '.landscape.yml':
                    self.entry['landscape'] = True # https://help.ubuntu.com/lts/clouddocs/en/Installing-Landscape.html
            for field in requirements_fields:
                if e.path == field + '.txt':
                    self.entry[field] = []
                    try:
                        fh = urllib.request.urlopen(e.url)
                        as_json = fh.read()
                        file_info = json.loads(as_json)
                        content = base64.b64decode(file_info['content'])
                        log.debug("content type: {}".format(content.__class__.__name__))
                        log.debug("content: {}".format(content))
                        if content.__class__.__name__ == 'bytes':
                            content = content.decode('utf8')

                        # https://github.com/ingresso-group/pyticketswitch/blob/master/requirements.txt
                        # contains -r requirements/common.txt  which means we need to fetch that file as well
                        # for now let's just skip this
                        match = re.search(r'^\s*-r', content)
                        if not match:
                            for req in requirements.parse(content):
                                log.debug("{}: {} {} {}".format(field, req.name, req.specs, req.extras))
                                # we cannot use the req.name as a key in the dictionary as some of the package names have a . in them
                                # and MongoDB does not allow . in fieldnames.
                                self.entry[field].append({ 'name' : req.name, 'specs' : req.specs })
                    except Exception:
                        log.exception("Exception when handling the {}.txt".format(field))
        log.debug("github finished")
        return

    # In the database have a mark that says if the package was already
    #    downloaded (or not)
    #    extracted (or not)
    def download_pkg(self):
        """Use ``urllib.request.urlretrieve`` to download package to file in sandbox
           dir.
        """
        if not 'download_url' in self.entry:
            log.info("No download_url")
            return()

        log.info('doanload_url {}'.format(self.entry['download_url']))

        #if 'local_dir' in self.entry:
        #    log.info('')
        match = re.search(r'/([^/]+)(\.tar\.gz)$', self.entry['download_url'])
        if match:
            # local_dir is the name of the file that should be the name of the local directory
            local_dir = match.group(1)
            extension = match.group(2)
        else:
            log.warn("Unsupported download file format: {}".format(self.entry['download_url']))
            return()

        log.info("local_dir '{}' extension '{}'".format(local_dir, extension))

        src_dir = PyDigger.common.get_source_dir()
        log.info("Source directory: {}".format(src_dir))

        # TODO use the requests module to download the zipfile

        # self.downloaded_from_url = True

    def save(self):
        entry = self.entry
        log.info("save_entry: '{}'".format(entry['name']))
        #log.debug("save_entry: {}".format(e)

        #my_entries.append(e)
        #print(e)
        # TODO make sure we only add newer version!
        # Version numbers I've seen:
        # 1.0.3
        # 20160325.161225
        # 0.2.0.dev20160325161211
        # 3.1.0a12
        # 2.0.0.dev11

        #doc = db.packages.find_one({'name' : e['name']})
        #if doc:
            #print(doc)
        db.packages.remove({'name' : entry['name']})
        db.packages.remove({'name' : entry['name'].lower()})
        db.packages.insert(entry)

def main():
    log.info("Staring main")
    src_dir = PyDigger.common.get_source_dir()
    log.info("Source directory: {}".format(src_dir))
    names = []
    packages = None

    if args.update:
        log.debug("update: {}".format(args.update))
        if args.update == 'rss':
            packages = get_from_rss()
        elif args.update == 'deps':
            log.info("Listing dependencies")
            seen = {}
            for field in requirements_fields:
                packages_with_requirements = db.packages.find({field : { '$exists' : True }}, { 'name' : True, field : True})
                for p in packages_with_requirements:
                    for r in p[field]:
                        name = r['name']
                        if not name:
                            log.info("{} {} found without a name in package {}".format(field, r, p))
                            continue
                        if name not in seen:
                            seen[name] = True
                            p = db.packages.find_one({'lcname': name.lower()})
                            if not p:
                                names.append(name)
        elif args.update == 'all':
            packages = db.packages.find({}, {'name': True})
        elif re.search(r'^\d+$', args.update):
            packages = db.packages.find().sort([('pubDate', 1)]).limit(int(args.update))
        else:
            print("The update option '{}' is not implemented yet".format(args.update))
    elif args.name:
        names.append(args.name)

    if packages:
        names = [ p['name'] for p in packages ]

    log.info("Start updating packages")
    for name in names:
        package = PyPackage(name)
        package.get_details()
        if args.sleep:
            #log.debug('sleeping {}'.format(args.sleep))
            time.sleep(args.sleep)

    log.info("Finished")




# going over the RSS feed most recent first
def get_from_rss():
    log.debug("get_from_rss")
    rss_data = get_rss()
    packages = []
    names = []

    root = ET.fromstring(rss_data)

    for item in root.iter('item'):
        title = item.find('title').text.split(' ')
        log.debug("Seen {}".format(title))
        name = title[0]
        version = title[1]
        lcname = name.lower()



        # The same package can appear in the RSS feed twice. We only need to process it once.
        if lcname in names:
            continue
        description = item.find('description').text
        pubDate = item.find('pubDate').text
        log.debug("Description {}".format(description))
        log.debug("pubDate {}".format(pubDate))

        # Tue, 01 Oct 2019 18:14:51 GMT
        try:
            if pubDate[-4:] == ' GMT':
                upload_time = datetime.strptime(pubDate[0:-4], "%a, %d %b %Y %H:%M:%S")
            else:
                upload_time = datetime.strptime(pubDate, "%d %b %Y %H:%M:%S %Z")
        except Exception as ex:
            log.error("Could not parse time '{}'\n{}".format(pubDate, ex))
            continue

        entry = {
            'name'        : name,
            'lcname'      : lcname,
            'summary'     : description,
            'upload_time' : upload_time,
        }

        # If this package is already in the database we only need to process if
        # the one coming in the RSS feed has a different (hopefully newer) version
        # number but if it is not in the database we can already save it
        # This still does not solve the problem of packages that have no upload_time
        # in their JSON file. Especially if we try to add such a package by name
        # and not from the RSS feed
        doc = db.packages.find_one({'lcname' : lcname})
        #if not doc:
        #    save_entry(entry)

        if doc and version == doc.get('version', ''):
            log.debug("Skipping '{}'. It is already in the database with this version".format(title))
            continue

        log.debug("Processing {}".format(title))
        names.append(lcname)
        packages.append(entry)
    return packages

def get_rss():
    latest_url = 'https://pypi.python.org/pypi?%3Aaction=rss'
    log.debug('get_rss from ' + latest_url)
    try:
        f = urllib.request.urlopen(latest_url)
        rss_data = f.read()
        f.close()
        #raise Exception("hello")
    except (urllib.reques.HTTPError, urllib.request.URLError):
        log.exception('Error while fetching ' + latest_url)
        raise Exception('Could not fetch RSS feed ' + latest_url)
    #log.debug(rss_data)
    return rss_data


db = PyDigger.common.get_db()
logging.basicConfig(
    level  = logging.DEBUG if args.verbose else logging.WARNING,
    format ='%(asctime)s %(name)s %(levelname)8s %(message)s'
)
log=logging.getLogger('fetch')

log.info("Starting")
with open('github-token') as fh:
    token = fh.readline().strip()

if not token:
    log.error("No github token found")
    exit()
github = login(token=token)


