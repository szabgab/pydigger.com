import os
import sys
import yaml
import time
import tempfile
import shutil
import logging
import PyDigger.common
import PyDigger.website

os.environ['PYDIGGER_SKIP_SETUP'] = 'oh yeah'
os.environ['PYDIGGER_TEST'] = 'oh yeah'

os.environ['PYDIGGER_SKIP_SETUP'] = ''

root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, root)

def create_config_files():
    logger = logging.getLogger('PyDigger.test')
    tmpdir = tempfile.mkdtemp()
    logger.info(f"tmpdir {tmpdir}")
    config_file = os.path.join(tmpdir, 'test_config.yml')
    os.environ['PYDIGGER_CONFIG'] = config_file

    if not os.path.exists(config_file):
        config = {
            "username": "root",
            "password": "Secret",
            "server": "mymongo:27017",
            "dbname": "test_pydigger_{}".format(str(time.time()).replace('.', '_')),
        }
        with open(config_file, 'w') as outfile:
            yaml.dump(config, outfile, default_flow_style=False)
    return tmpdir


class TestDigger:
    def test_common(self):
        root = PyDigger.common.get_root()
        source_dir = PyDigger.common.get_source_dir()
        assert root + '/src' == source_dir

# TODO: Make sure the web site can be loaded even if the configuration files are missing and there is no access to the
# databse. Report this properly in the log or on the generate web page.

class Tools():
    def setup_class(self):
        self.logger = logging.getLogger('PyDigger.test')
        self.tmpdir = create_config_files()
        self.app = PyDigger.website.app.test_client()

    def teardown_class(self):
        if not os.environ.get('KEEP_DB'):
            print(self.tmpdir)
            PyDigger.common.remove_db()
            shutil.rmtree(self.tmpdir)


class TestEmptyWeb(Tools):
    def test_main(self):
        rv = self.app.get('/')
        assert rv.status == '200 OK'
        #print(rv.data)
        assert b'<title>PyDigger - unearthing stuff about Python</title>' in rv.data

    def test_stats(self):
        rv = self.app.get('/stats')
        assert rv.status == '200 OK'
        #print(rv.data)
        assert b'<title>PyDigger - Statistics</title>' in rv.data

    def test_about(self):
        rv = self.app.get('/about')
        assert rv.status == '200 OK'
        #print(rv.data)
        assert b'<title>About PyDigger</title>' in rv.data

    def test_404(self):
        rv = self.app.get('/other-page')
        assert rv.status == '404 NOT FOUND'
        #print('----------------------------')
        #print(rv.data)
        #print('----------------------------')
        assert b'<title></title>' in rv.data  # TODO make 404 page look nicer and have some title and body

    def test_api_recent(self):
        self.logger.info("test_api_recent")
        rv = self.app.get('/api/0/recent')
        assert rv.status == '200 OK'
        assert rv.headers['Content-Type'] == 'application/json'
        assert rv.json == []

class TestWeb(Tools):
    def setup_class(self):
        super().setup_class(self)
        #os.system("printenv | sort")
        #os.system("cat $PYDIGGER_CONFIG")
        # This fails on development machines beacuse there is no GitHub token in the test code.
        # Strangely the test passes in either way
        if 'CI' in os.environ:
            os.system("{} fetch_recent.py --update rss --log DEBUG --screen --limit 5".format(sys.executable))

    # TODO: look at the log and if there are any warnings, errors, or exceptions report them or even fail the tests
    def test_recent(self):
        rv = self.app.get('/api/0/recent')
        assert rv.status == '200 OK'
        assert rv.headers['Content-Type'] == 'application/json'
        recent = rv.json
        #print(recent)
        #assert len(recent) == 5
        for entry in recent:
            assert 'name' in entry
            assert 'home_page' in entry

        if len(recent) > 0:
            rv = self.app.get('/pypi/{}'.format(recent[0]['name']))
            assert rv.status == '200 OK'
            assert rv.headers['Content-Type'] == 'text/html; charset=utf-8'
            assert '<h1>{}</h1>'.format(recent[0]['name']) in rv.data.decode('utf8')
