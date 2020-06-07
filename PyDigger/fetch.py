import argparse
import base64
import json
import logging
import logging.handlers
import re
import requirements
import time
import http
import urllib.request
import xml.etree.ElementTree as ET
import os
from datetime import datetime
import github3
import warnings

import PyDigger.common

requirements_fields = ['requirements', 'test_requirements']

# Updated:
# 1) All the entries that don't have last_update field
# 2) All the entries that were updated more than N days ago
# 3) All the entries that were updated in the last N days ??

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen', help='Log to the screen', action='store_true')
    parser.add_argument('--log',    help='Set logging level to DEBUG or INFO (or keep it at the default WARNING)', default='WARNING')
    parser.add_argument('--update', help='update the entries: rss - the ones received via rss; deps - dependencies; all - all of the packages already in the database')
    parser.add_argument('--name',   help='Name of the package to update')
    parser.add_argument('--sleep',  help='How many seconds to sleep between packages (Help avoiding the GitHub API limit)', type=float)
    parser.add_argument('--limit',  help='Max number of packages to investigate. (Used during testing and development)', type=int)
    args = parser.parse_args()
    return args


class PyPackage(object):
    def __init__(self, name):
        self.lcname = name.lower()
        self.entry = {}

    def get_details(self):
        logger = logging.getLogger(__name__)
        logger.debug("get_details of " + self.lcname)

        url = 'https://pypi.org/pypi/' + self.lcname + '/json'
        logger.debug("Fetching url {}".format(url))
        try:
            f = urllib.request.urlopen(url)
            json_data = f.read()
            f.close()
            #print(json_data)
        except (urllib.request.HTTPError, urllib.request.URLError, http.client.InvalidURL):
            logger.exception("Could not fetch details of PyPI package from '{}'".format(url))
            return
        package_data = json.loads(json_data)
        #logger.debug('package_data: {}'.format(package_data))

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
                    logger.debug("keywords '{}'".format(keywords))
                    logger.debug("keywords type '{}'".format(keywords.__class__.__name__))
                    #if keywords.__class__.__name__ == 'bytes':
                    #    keywords = keywords.decode('utf8')

                    #keywords = keywords.encode('utf-8')
                    keywords = keywords.lower()
                    if re.search(',', keywords):
                        self.entry['split_keywords'] = keywords.split(',')
                    else:
                        self.entry['split_keywords'] = keywords.split(' ')

        self.process_release(package_data)

        self.entry['github'] = False
        if 'home_page' in self.entry and self.entry['home_page'] != None:
            match = re.search(r'^https?://github.com/([^/]+)/([^/]+)/?$', self.entry['home_page'])
            if match:
                self.entry['github'] = True
                self.entry['github_user'] = match.group(1)
                self.entry['github_project'] = match.group(2)

        if self.entry['github']:
            try:
                self.check_github()
            except github3.exceptions.NotFoundError:
                logger.error(f"404 NotFountError while trying to get data from GitHub: '{self.entry['home_page']}'")
            except Exception as err:
                logger.exception(f"Error while trying to get data from GitHub: '{self.entry['home_page']}'")

        self.entry['lcname'] = self.entry['name'].lower()
        self.download_pkg()
        self.save()


    def process_release(self, package_data):
        logger = logging.getLogger(__name__)
        version = self.entry['version']
        if 'urls' in package_data:
            self.entry['urls'] = package_data['urls']
        if not 'releases' in package_data:
            logger.error("There are no releases in package {} --- {}".format(self.lcname, package_data))
        elif not version in package_data['releases']:
            logger.error("Version {} is not in the releases of package {} --- {}".format(version, self.lcname, package_data))
        elif len(package_data['releases'][version]) == 0:
            logger.error("Version {} has no elements in the releases of package {} --- {}".format(version, self.lcname, package_data))
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
                        logger.error("Version {} has no download_url in the releases of package {} --- {}".format(version, self.lcname, package_data))
                    source = version_pack
                    break

                #url: https://pypi.org/packages/ce/c7/6431a8ba802bf93d611bfd53c05abcc078165b8aad3603d66c02a847af7d/codacy-coverage-1.2.10.tar.gz
                #filename: codacy-coverage-1.2.10.tar.gz
                #url: https://pypi.org/packages/84/85/5ce28077fbf455ddf0ba2506cdfdc2e5caa0822b8a4a2747da41b683fad8/purepng-0.1.3.zip

            if not 'upload_time' in source:
                logger.error("upload_time is missing from version {} in the releases of package {} --- {}".format(version, self.name, package_data))
            else:
                upload_time = source['upload_time']
                self.entry['upload_time'] = datetime.strptime(upload_time, "%Y-%m-%dT%H:%M:%S")

    def check_github(self):
        logger = logging.getLogger(__name__)
        logger.debug("check_github user='{}', project='{}".format(self.entry['github_user'], self.entry['github_project']))

        repo = github.repository(self.entry['github_user'], self.entry['github_project'])
        if not repo:
            logger.error("Could not fetch GitHub repository for {}".format(self.entry['name']))
            self.entry['error'] = "Could not fetch GitHub repository"
            return

        logger.debug("default_branch: {}".format(repo.default_branch))

        # get the last commit of the default branch
        branch = repo.branch(repo.default_branch)
        if not branch:
            logger.error("Could not fetch GitHub branch {} for {}".format(repo.default_branch, self.entry['name']))
            self.entry['error'] = "Could not fetch GitHub branch"
            return

        last_sha = branch.commit.sha
        logger.debug("last_sha: {}".format(last_sha))
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
                        logger.debug("content type: {}".format(content.__class__.__name__))
                        logger.debug("content: {}".format(content))
                        if content.__class__.__name__ == 'bytes':
                            content = content.decode('utf8')

                        # https://github.com/ingresso-group/pyticketswitch/blob/master/requirements.txt
                        # contains -r requirements/common.txt  which means we need to fetch that file as well
                        # for now let's just skip this
                        match = re.search(r'^\s*-r', content)
                        if not match:
                            # Capture: UserWarning: Private repos not supported. Skipping.
                            with warnings.catch_warnings(record=True) as warn:
                                warnings.simplefilter("always")
                                for req in requirements.parse(content):
                                    logger.debug("{}: {} {} {}".format(field, req.name, req.specs, req.extras))
                                    # we cannot use the req.name as a key in the dictionary as some of the package names have a . in them
                                    # and MongoDB does not allow . in fieldnames.
                                    self.entry[field].append({ 'name' : req.name, 'specs' : req.specs })
                                for w in warn:
                                    logger.warn(str(w))
                    except Exception:
                        logger.exception("Exception when handling the {}.txt".format(field))
        logger.debug("github finished")
        return

    # In the database have a mark that says if the package was already
    #    downloaded (or not)
    #    extracted (or not)
    def download_pkg(self):
        """Use ``urllib.request.urlretrieve`` to download package to file in sandbox
           dir.
        """
        logger = logging.getLogger(__name__)
        if not 'download_url' in self.entry or self.entry['download_url'] is None:
            logger.info("No download_url")
            return()

        logger.info('download_url {}'.format(self.entry['download_url']))

        #if 'local_dir' in self.entry:
        #    logger.info('')
        match = re.search(r'/([^/]+)(\.tar\.gz)$', self.entry['download_url'])
        if match:
            # local_dir is the name of the file that should be the name of the local directory
            local_dir = match.group(1)
            extension = match.group(2)
        else:
            logger.warn("Unsupported download file format: '{}'".format(self.entry['download_url']))
            return()

        logger.info("local_dir '{}' extension '{}'".format(local_dir, extension))

        src_dir = PyDigger.common.get_source_dir()
        logger.info("Source directory: {}".format(src_dir))

        # TODO use the requests module to download the zipfile

        # self.downloaded_from_url = True

    def save(self):
        logger = logging.getLogger(__name__)
        entry = self.entry
        logger.info("save_entry: '{}'".format(entry['name']))
        #logger.debug("save_entry: {}".format(e)

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
        res = db.packages.insert(entry)
        logger.info("INSERT res='{}'".format(res))


def setup_logger(args):
    if args.log and args.log.upper() in ['DEBUG', 'INFO', 'WARNING']:
        log_level = getattr(logging, args.log.upper())
    else:
        exit(f'Invalid --log parameter {args.log}')

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-10s - %(message)s')

    if args.screen:
        sh = logging.StreamHandler()
        sh.setLevel(log_level)
        sh.setFormatter(log_format)
        logger.addHandler(sh)
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file = os.path.join(project_root, 'log', 'fetch.log')
        ch = logging.handlers.RotatingFileHandler(log_file, maxBytes=100_000_000, backupCount=2)
        ch.setLevel(log_level)
        ch.setFormatter(log_format)
        logger.addHandler(ch)

    logger.info("======================== Starting =================================")

def setup_github():
    global github
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        with open('github-token') as fh:
            token = fh.readline().strip()

    if not token:
        logger.error("No github token found")
        exit()
    github = github3.login(token=token)

def setup_db():
    global db
    db = PyDigger.common.get_db()


def setup(args):
    setup_db()
    setup_logger(args)
    setup_github()


def main():
    args = get_args()
    setup(args)

    logger = logging.getLogger(__name__)
    logger.info("Starting main")
    src_dir = PyDigger.common.get_source_dir()
    logger.info("Source directory: {}".format(src_dir))
    names = []
    packages = None

    if args.update:
        logger.debug("update: {}".format(args.update))
        if args.update == 'rss':
            packages = get_from_rss()
        elif args.update == 'deps':
            logger.info("Listing dependencies")
            seen = {}
            for field in requirements_fields:
                packages_with_requirements = db.packages.find({field : { '$exists' : True }}, { 'name' : True, field : True})
                for p in packages_with_requirements:
                    for r in p[field]:
                        name = r['name']
                        if not name:
                            logger.info("{} {} found without a name in package {}".format(field, r, p))
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
            logger.error("The update option '{}' is not implemented yet".format(args.update))
    elif args.name:
        names.append(args.name)

    if packages:
        names = [ p['name'] for p in packages ]

    count = 0
    logger.info("Start updating packages")
    for name in names:
        count += 1
        if args.limit and count > args.limit:
            break

        package = PyPackage(name)
        package.get_details()
        if args.sleep:
            #logger.debug('sleeping {}'.format(args.sleep))
            time.sleep(args.sleep)

    logger.info("Finished")




# going over the RSS feed most recent first
def get_from_rss():
    logger = logging.getLogger(__name__)
    logger.debug("get_from_rss")
    rss_data = get_rss()
    packages = []
    names = []

    root = ET.fromstring(rss_data)

    for item in root.iter('item'):
        title = item.find('title').text.split(' ')
        logger.debug("Seen {}".format(title))
        name = title[0]
        version = title[1]
        lcname = name.lower()



        # The same package can appear in the RSS feed twice. We only need to process it once.
        if lcname in names:
            continue
        description = item.find('description').text
        pubDate = item.find('pubDate').text
        logger.debug("Description {}".format(description))
        logger.debug("pubDate {}".format(pubDate))

        # Tue, 01 Oct 2019 18:14:51 GMT
        try:
            if pubDate[-4:] == ' GMT':
                upload_time = datetime.strptime(pubDate[0:-4], "%a, %d %b %Y %H:%M:%S")
            else:
                upload_time = datetime.strptime(pubDate, "%d %b %Y %H:%M:%S %Z")
        except Exception as ex:
            logger.error("Could not parse time '{}'\n{}".format(pubDate, ex))
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
            logger.debug("Skipping '{}'. It is already in the database with this version".format(title))
            continue

        logger.debug("Processing {}".format(title))
        names.append(lcname)
        packages.append(entry)
    return packages

def get_rss():
    logger = logging.getLogger(__name__)
    latest_url = 'https://pypi.org/rss/updates.xml'
    logger.debug('get_rss from ' + latest_url)
    try:
        f = urllib.request.urlopen(latest_url)
        rss_data = f.read()
        f.close()
        #raise Exception("hello")
    except (urllib.reques.HTTPError, urllib.request.URLError):
        logger.exception('Error while fetching ' + latest_url)
        raise Exception('Could not fetch RSS feed ' + latest_url)
    #logger.debug(rss_data)
    return rss_data



