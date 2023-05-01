from PyDigger import fetch

def test_vcs():
    package = fetch.PyPackage("foo")
    package.entry['home_page'] = 'https://github.com/user/project'
    package.entry['version'] = '1.0'
    package.extract_vcs()
    assert package.entry == {
        'home_page': 'https://github.com/user/project',
        'version': '1.0',
        'github': True,
        'gitlab': False,
        'bitbucket': False,
        'github_user': 'user',
        'github_project': 'project'
    }
    pass
