import PyDigger.common

class TestDigger(object):
    def test_fix(self):
        assert 1 == 1

    def test_common(self):
        root = PyDigger.common.get_root()
        source_dir = PyDigger.common.get_source_dir()
        assert root + '/src' == source_dir

class TestWeb(object):
    def setup_class(self):
        import PyDigger.website
        self.app = PyDigger.website.app.test_client()

    def test_main(self):
        rv = self.app.get('/')
        assert rv.status == '200 OK'
        #print(rv.data)
        assert b'<title>PyDigger - unearthing stuff about Python</title>' in rv.data


