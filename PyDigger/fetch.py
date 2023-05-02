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
import sys
from datetime import datetime
import github3
import warnings
import requests
import tempfile
import tarfile

import PyDigger.common
import shutil
from contextlib import contextmanager
import PyDigger.myflake

# https://github.com/szabgab/pydigger.com/
# https://github.com/szabgab/pydigger.com.git     # remove the .git for our purposes (GitHub would redirect anyway)
# https://gitlab.com/szabgab/gl-try
# https://gitlab.com/szabgab/gl-try.git   # remove the .git
# https://bitbucket.org/szabgab/hostlocal.com
# https://bitbucket.org/szabgab/hostlocal.com.git   #remove the .git

vcs_es = {
    'github': {
        'host': 'github.com',
        'regex': r'^https?://(www\.)?github.com/([^/]+)/([^/]+)(/.*)?$',
    },
    'gitlab': {
        'host': 'gitlab.com',
        'regex': r'^https?://(www\.)?gitlab.com/([^/]+)/([^/]+)(/.*)?$',
    },
    'bitbucket': {
        'host': 'bitbucket.org',
        'regex': r'^https?://(www\.)?bitbucket.org/([^/]+)/([^/]+)(/.*)?$',
    },
    'codeberg': {
        'host': 'codeberg.org',
        'regex': r'^https?://(www\.)?codeberg.org/([^/]+)/([^/]+)(/.*)?$',
    },
}

@contextmanager
def tempdir():
    temp_dir = tempfile.mkdtemp()
    oldpwd = os.getcwd()
    os.chdir(temp_dir)
    try:
        yield temp_dir
    finally:
        os.chdir(oldpwd)
        shutil.rmtree(temp_dir)


requirements_fields = ['requirements', 'test_requirements']

# Updated:
# 1) All the entries that don't have last_update field
# 2) All the entries that were updated more than N days ago
# 3) All the entries that were updated in the last N days ??

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen', help='Log to the screen', action='store_true')
    parser.add_argument('--log',    help='Set logging level to DEBUG or INFO (or keep it at the default WARNING)', default='WARNING')
    parser.add_argument('--logdir', help='Folder where to put the log files')
    parser.add_argument('--update', help='update the entries: rss - the ones received via rss; deps - dependencies; all - all of the packages already in the database; url - provide the url of a github repository')
    parser.add_argument('--name',   help='Name of the package to update')
    parser.add_argument('--sleep',  help='How many seconds to sleep between packages (Help avoiding the GitHub API limit)', type=float)
    parser.add_argument('--url', help='URL of a github repository')
    parser.add_argument('--limit',  help='Max number of packages to investigate. (Used during testing and development)', type=int)
    parser.add_argument('--package',  help='Name of a PyPI package that would fit this URL https://pypi.org/pypi/<package>',)
    args = parser.parse_args()
    return args


class PyPackage:
    def __init__(self, name):
        self.lcname = name.lower()
        self.entry = {}
        self.config = PyDigger.common.read_config()
        self.setup_github()

    def setup_github(self):
        logger = logging.getLogger('PyDigger')
        token = os.environ.get('GITHUB_TOKEN')
        if not token:
            token = self.config['github-token']

        if not token:
            logger.error("No github token found")
            self.github = None
            return
        self.github = github3.login(token=token)

    def get_details(self):
        logger = logging.getLogger('PyDigger')
        logger.debug("get_details of " + self.lcname)

        url = 'https://pypi.org/pypi/' + self.lcname + '/json'
        logger.debug(f"Fetching url {url}")
        try:
            f = urllib.request.urlopen(url)
            json_data = f.read()
            f.close()
            #logger.debug(json_data)
        except (urllib.request.HTTPError, urllib.request.URLError, http.client.InvalidURL, ConnectionError) as err:
            logger.error(f"Could not fetch details of PyPI package from '{url}'. Error: {type(err)}: {err}")
            #self.entry['json_missing'] = True
            #self.save()
            return
        except Exception:
            logger.exception(f"Could not fetch details of PyPI package from '{url}'")
            return
        package_data = json.loads(json_data)
        #logger.debug(f'package_data: {package_data}'))

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
            for field in ['name', 'maintainer', 'docs_url', 'requires_python', 'maintainer_email',
            'cheesecake_code_kwalitee_id', 'cheesecake_documentation_id', 'cheesecake_installability_id',
            'keywords', 'author', 'author_email', 'download_url', 'platform', 'description', 'bugtrack_url',
            'license', 'summary', 'version', 'project_urls']:
                if field in info:
                    self.entry[field] = info[field]

            self.entry['split_keywords'] = []
            if 'keywords' in info:
                keywords = info['keywords']
                if keywords is not None and keywords != "":
                    logger.debug(f"keywords '{keywords}'")
                    logger.debug(f"keywords type '{keywords.__class__.__name__}'")
                    #if keywords.__class__.__name__ == 'bytes':
                    #    keywords = keywords.decode('utf8')

                    #keywords = keywords.encode('utf-8')
                    keywords = keywords.lower()
                    if re.search(',', keywords):
                        self.entry['split_keywords'] = keywords.split(',')
                    else:
                        self.entry['split_keywords'] = keywords.split(' ')

        self.process_release(package_data)

        self.extract_vcs()

        if self.entry['github']:
            try:
                self.check_github()
            except github3.exceptions.NotFoundError:
                logger.error(f"404 NotFoundError while trying to get data from GitHub: '{self.entry['home_page']}'")
                self.entry['github_not_found'] = True
            except Exception:
                logger.exception(f"Error while trying to get data from GitHub: '{self.entry['home_page']}'")
                self.entry['github_fetch_exception'] = True

        self.entry['lcname'] = self.entry['name'].lower()
        # self.download_pkg()
        self.analyze_source_code()
        self.save()

    def analyze_source_code(self):
        pass
        # We probably don't need to clone the repo with `git clone --depth 1 {URL}` as we already have it downloaded
        # myflake.process(directory)

    def extract_vcs(self):
        logger = logging.getLogger('PyDigger')
        vcs_found = False
        for vcs in vcs_es:
            self.entry[vcs] = False

        for vcs in vcs_es:
            if 'home_page' in self.entry and self.entry['home_page'] is not None:
                vcs_url = self.entry['home_page']
                vcs_found = self.is_this_a_vcs(vcs, vcs_url)
                if vcs_found:
                    break
            if self.entry.get('project_urls') is not None:
                logger.info(f"project_urls found in project {self.lcname} Version {self.entry['version']}")
                logger.info(f"project_urls keys: {self.entry['project_urls'].keys()}")
                # Officially https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#urls
                # this should be 'repository' but I found all kind of other keys:
                # in numpy https://pypi.org/project/numpy/  it is "Source Code"
                # in farm-haystack https://pypi.org/project/farm-haystack/ it is "GitHub: repo"
                for field_name, vcs_url in self.entry['project_urls'].items():
                    vcs_found = self.is_this_a_vcs(vcs, vcs_url)
                    if vcs_found:
                        break
            if vcs_found:
                break
        if not vcs_found:
            logger.info(f"No VCS found for project {self.lcname} Version {self.entry['version']}")

    def is_this_a_vcs(self, vcs, vcs_url):
        logger = logging.getLogger('PyDigger')
        if vcs_url is None:
            return False

        match = re.search(vcs_es[vcs]['regex'], vcs_url)
        if match:
            self.entry[vcs] = True
            self.entry[f'{vcs}_user'] = match.group(2)
            project = match.group(3)
            project = re.sub(r'\.git$', '', project)
            self.entry[f'{vcs}_project'] = project
            logger.info(f"Project {self.lcname} Version {self.entry['version']} has VCS {vcs}: {vcs_url}")
            return True
        return False

    def process_release(self, package_data):
        logger = logging.getLogger('PyDigger')
        version = self.entry['version']
        if 'urls' in package_data:
            self.entry['urls'] = package_data['urls']
        if 'releases' not in package_data:
            logger.error(f"There are no releases in package '{self.lcname}' --- {package_data}")
        elif version not in package_data['releases']:
            logger.error(f"Version '{version}' is not in the releases of package '{self.lcname}' --- {package_data}")
        elif len(package_data['releases'][version]) == 0:
            logger.error(f"Version '{version}' has no elements in the releases of package {self.lcname} --- {package_data}")
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
                        logger.error(f"Version '{version}' has no download_url in the releases of package {self.lcname} --- {package_data}")
                    source = version_pack
                    break

                #url: https://pypi.org/packages/ce/c7/6431a8ba802bf93d611bfd53c05abcc078165b8aad3603d66c02a847af7d/codacy-coverage-1.2.10.tar.gz
                #filename: codacy-coverage-1.2.10.tar.gz
                #url: https://pypi.org/packages/84/85/5ce28077fbf455ddf0ba2506cdfdc2e5caa0822b8a4a2747da41b683fad8/purepng-0.1.3.zip

            if 'upload_time' not in source:
                logger.error(f"upload_time is missing from version {version} in the releases of package {self.name} --- {package_data}")
            else:
                upload_time = source['upload_time']
                self.entry['upload_time'] = datetime.strptime(upload_time, "%Y-%m-%dT%H:%M:%S")

    def check_github(self):
        logger = logging.getLogger('PyDigger')
        logger.debug("check_github user='{}', project='{}".format(self.entry['github_user'], self.entry['github_project']))
        if not self.github:
            return

        repo = self.github.repository(self.entry['github_user'], self.entry['github_project'])
        if not repo:
            logger.error("Could not fetch GitHub repository for {}".format(self.entry['name']))
            self.entry['error'] = "Could not fetch GitHub repository"
            return

        logger.debug(f"default_branch: {repo.default_branch}")

        # get the last commit of the default branch
        branch = repo.branch(repo.default_branch)
        if not branch:
            logger.error("Could not fetch GitHub branch {} for {}".format(repo.default_branch, self.entry['name']))
            self.entry['error'] = "Could not fetch GitHub branch"
            return

        last_sha = branch.commit.sha
        logger.debug(f"last_sha: {last_sha}")
        t = repo.tree(last_sha, recursive=True)
        self.entry['travis_ci'] = False
        self.entry['coveralls'] = False
        self.entry['github_actions'] = False
        for file in t.tree:
            if file.path == '.travis.yml':
                self.entry['travis_ci'] = True
            if re.search(r'^\.github/workflows/.*\.ya?ml$', file.path):
                self.entry['github_actions'] = True
            if file.path == '.coveragerc':
                self.entry['coveralls'] = True
            if file.path == 'tox.ini':
                self.entry['tox'] = True # http://codespeak.net/tox/
            if file.path == 'circle.yml':
                self.entry['circle'] = True # https://circleci.com/
            if re.search(r'^\.circleci/.*\.ya?ml$', file.path):
                self.entry['circle'] = True # https://circleci.com/
            if file.path == 'appveyor.yml':
                self.entry['appveyor'] = True # https://www.appveyor.com/
            if file.path == '.appveyor.yml':
                self.entry['appveyor'] = True # https://www.appveyor.com/
            if file.path == '.editconfig':
                self.entry['editconfig'] = True # http://editorconfig.org/
            if file.path == 'dockbot.json':
                self.entry['dockbot'] = True # https://github.com/CauldronDevelopmentLLC/dockbot
            if file.path == '.landscape.yml':
                self.entry['landscape'] = True # https://help.ubuntu.com/lts/clouddocs/en/Installing-Landscape.html

            for field in requirements_fields:
                if file.path == field + '.txt':
                    self.entry[field] = []
                    try:
                        fh = urllib.request.urlopen(file.url)
                        as_json = fh.read()
                        file_info = json.loads(as_json)
                        content = base64.b64decode(file_info['content'])
                        logger.debug(f"content type: {content.__class__.__name__}")
                        logger.debug(f"content: {content}")
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
                                    logger.debug(f"{field}: {req.name} {req.specs} {req.extras}")
                                    # we cannot use the req.name as a key in the dictionary as some of the package names have a . in them
                                    # and MongoDB does not allow . in fieldnames.
                                    self.entry[field].append({ 'name' : req.name, 'specs' : req.specs })
                                for w in warn:
                                    logger.warning(str(w))
                    except urllib.error.HTTPError as err:
                        logger.error(f"Exception when handling the {field}.txt: {err}")
                        if "rate limit exceeded" in err:
                            time.sleep(2)
                    except Exception:
                        logger.exception(f"Exception when handling the {field}.txt")
        logger.debug("github finished")
        return

    # In the database have a mark that says if the package was already
    #    downloaded (or not)
    #    extracted (or not)
    def download_pkg(self):
        """Use ``urllib.request.urlretrieve`` to download package to file in sandbox
           dir.
        """
        logger = logging.getLogger('PyDigger')
        if 'download_url' not in self.entry or self.entry['download_url'] is None:
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
            logger.warning("Unsupported download file format: '{}'".format(self.entry['download_url']))
            return()

        logger.info(f"local_dir '{local_dir}' extension '{extension}'")

        src_dir = PyDigger.common.get_source_dir()
        logger.info(f"Source directory: {src_dir}")

        request = requests.get(self.entry['download_url'])
        with tempdir() as temp_dir:
            temp_file = os.path.join(temp_dir, f'{local_dir}{extension}')
            with open(temp_file, 'wb') as fh:
                fh.write(request.content)
            file_size = os.stat(temp_file).st_size
            self.entry['distribution_file_size'] = file_size
            logger.info(f"Downloaded {file_size} bytes into '{temp_file}'")
            tar = tarfile.open(temp_file, "r:gz")
            tar.extractall()
            tar.close()
            os.unlink(temp_file)
            dir_size = get_size(temp_dir)
            self.entry['distribution_directory_size'] = dir_size
            logger.info(f"Extracted directory size {dir_size} bytes")
            flake_report = PyDigger.myflake.process(temp_dir)
            self.entry['flake8_score'] = flake_report
            logger.info(f"flake_report: {flake_report}")
            self.downloaded_from_url = True

    def save(self):
        logger = logging.getLogger('PyDigger')
        entry = self.entry
        logger.info("save_entry: '{}'".format(entry['name']))

        # TODO make sure we only add newer version!
        # Version numbers I've seen:
        # 1.0.3
        # 20160325.161225
        # 0.2.0.dev20160325161211
        # 3.1.0a12
        # 2.0.0.dev11

        # logger.info(dir(db.packages))
        db.packages.delete_one({'name' : entry['name']})
        db.packages.delete_one({'name' : entry['name'].lower()})
        res = db.packages.insert_one(entry)
        logger.info("INSERT res='{}'".format(res))


def setup_logger(args):
    if args.log and args.log.upper() in ['DEBUG', 'INFO', 'WARNING']:
        log_level = getattr(logging, args.log.upper())
    else:
        exit(f'Invalid --log parameter {args.log}')

    logger = logging.getLogger('PyDigger')
    logger.setLevel(log_level)
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-10s - %(message)s')

    if args.screen:
        sh = logging.StreamHandler()
        sh.setLevel(log_level)
        sh.setFormatter(log_format)
        logger.addHandler(sh)
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = args.logdir
        if not log_dir:
            log_dir = os.path.join(project_root, 'log')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, datetime.now().strftime("fetch-%Y-%m-%d-%H-%M-%S.log"))
        ch = logging.FileHandler(log_file)
        ch.setLevel(log_level)
        ch.setFormatter(log_format)
        logger.addHandler(ch)

    logger.info("======================== Starting =================================")

def setup_db():
    global db
    db = PyDigger.common.get_db()


def setup(args):
    setup_db()
    setup_logger(args)


def main():
    args = get_args()
    setup(args)

    logger = logging.getLogger('PyDigger')
    logger.info("Starting main")
    src_dir = PyDigger.common.get_source_dir()
    logger.info("Source directory: {}".format(src_dir))
    names = []
    packages = None

    if args.update:
        logger.debug("update: {}".format(args.update))
        if args.update == 'rss':
            packages = get_from_rss()
        elif args.update == 'package':
            packages = [{ 'name': args.package }]
        elif args.update == 'url':
            package = PyPackage("foo")
            package.entry['home_page'] = args.url
            package.entry['version'] = 0
            names = [ 'foo' ]
            package.extract_vcs()
            package.check_github()
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

        if packages:
            names = [ p['name'] for p in packages ]
    elif args.name:
        names.append(args.name)
    else:
        exit(f"Missing --update or --name.   Run '{sys.argv[0]} -h' to get help.")

    update_packages(args, names)

    PyDigger.common.update_cache()

    logger.info("Finished")

def update_packages(args, names):
    logger = logging.getLogger('PyDigger')
    count = 0
    logger.info("Start updating packages")
    for name in names:
        count += 1
        if args.limit and count > args.limit:
            break

        package = PyPackage(name)
        package.get_details()
        if args.sleep:
            #logger.debug('sleeping {args.sleep}')
            time.sleep(args.sleep)


# going over the RSS feed most recent first
def get_from_rss():
    logger = logging.getLogger('PyDigger')
    logger.debug("get_from_rss")
    rss_data = get_rss()
    packages = []
    seen_names = []

    try:
        root = ET.fromstring(rss_data)
    except Exception as err:
        logger.error(f"Could not parse rss_data\n{err}")
        return packages
        # seen: xml.etree.ElementTree.ParseError: not well-formed (invalid token)

    for item in root.iter('item'):
        title = item.find('title')
        name, version = title.text.split(' ')
        logger.debug(f"Processing '{name}' '{version}'")
        lcname = name.lower()

        # The same package can appear in the RSS feed twice. We only need to process it once.
        if lcname in seen_names:
            continue
        description = item.find('description').text
        pubDate = item.find('pubDate').text
        logger.debug(f"Description {description}")
        logger.debug(f"pubDate {pubDate}")

        # Tue, 01 Oct 2019 18:14:51 GMT
        try:
            if pubDate[-4:] == ' GMT':
                upload_time = datetime.strptime(pubDate[0:-4], "%a, %d %b %Y %H:%M:%S")
            else:
                upload_time = datetime.strptime(pubDate, "%d %b %Y %H:%M:%S %Z")
        except Exception as err:
            logger.error(f"Could not parse time '{pubDate}'\n{err}")
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
        # TODO: check if the new version number is higher than the old one!
        doc = db.packages.find_one({'lcname' : lcname})
        if doc:
            old_version = doc.get('version', '')
            if version == old_version:
                logger.debug(f"Skipping '{name}' '{version}'. It is already in the database with this version")
                continue
            logger.debug(f"Update '{name}' from '{old_version}' to '{version}'. It is already in the database with this version")

        seen_names.append(lcname)
        packages.append(entry)
    return packages

def get_rss():
    logger = logging.getLogger('PyDigger')
    latest_url = 'https://pypi.org/rss/updates.xml'
    logger.debug('get_rss from ' + latest_url)
    try:
        f = urllib.request.urlopen(latest_url)
        rss_data = f.read()
        f.close()
        #raise Exception("hello")
    except (urllib.reques.HTTPError, urllib.request.URLError):
        logger.exception(f'Error while fetching {latest_url}')
        raise Exception(f'Could not fetch RSS feed {latest_url}')
    #logger.debug(rss_data)
    return rss_data

def get_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            # skip if it is symbolic link
            if not os.path.islink(file_path):
                total_size += os.path.getsize(file_path)

    return total_size
