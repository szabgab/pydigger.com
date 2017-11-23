import PyDigger.common

class TestDigger(object):
    def test_fix(self):
        assert 1 == 1

    def test_common(self):
        root = PyDigger.common.get_root()
        source_dir = PyDigger.common.get_source_dir()
        assert root + '/src' == source_dir
