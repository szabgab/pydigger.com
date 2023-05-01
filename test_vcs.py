from PyDigger import fetch

import os
import yaml

def test_vcs(tmpdir):
    print(tmpdir)
    config_file = os.environ['PYDIGGER_CONFIG'] = os.path.join(tmpdir, 'config.yml')
    print(os.environ['PYDIGGER_CONFIG'])
    config = {'github-token': 'fake'}
    with open(config_file, 'w') as outfile:
            yaml.dump(config, outfile, default_flow_style=False)

    # github plain url in home_page
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

    # github plain url with trailing slash in home_page
    package = fetch.PyPackage("foo")
    package.entry['home_page'] = 'https://github.com/user/project/'
    package.entry['version'] = '1.0'
    package.extract_vcs()
    assert package.entry == {
        'home_page': 'https://github.com/user/project/',
        'version': '1.0',
        'github': True,
        'gitlab': False,
        'bitbucket': False,
        'github_user': 'user',
        'github_project': 'project'
    }


    # gitlab plain url + version is a string in home_page
    package = fetch.PyPackage("foo")
    package.entry['home_page'] = 'https://gitlab.com/user/project'
    package.entry['version'] = 'abc'
    package.extract_vcs()
    assert package.entry == {
        'home_page': 'https://gitlab.com/user/project',
        'version': 'abc',
        'github': False,
        'gitlab': True,
        'bitbucket': False,
        'gitlab_user': 'user',
        'gitlab_project': 'project'
    }

    # non-vcs URL in home_page
    package = fetch.PyPackage("foo")
    package.entry['home_page'] = 'https://pypi.org/user/project'
    package.entry['version'] = 'abc'
    package.extract_vcs()
    assert package.entry == {
        'home_page': 'https://pypi.org/user/project',
        'version': 'abc',
        'github': False,
        'gitlab': False,
        'bitbucket': False,
    }

    # github url with extra /tags in home_page
    package = fetch.PyPackage("foo")
    package.entry['home_page'] = 'https://github.com/user/project/tags'
    package.entry['version'] = '1.0'
    package.extract_vcs()
    assert package.entry == {
        'home_page': 'https://github.com/user/project/tags',
        'version': '1.0',
        'github': True,
        'gitlab': False,
        'bitbucket': False,
        'github_user': 'user',
        'github_project': 'project'
    }

    # github url with extra .git in home_page
    # package = fetch.PyPackage("foo")
    # package.entry['home_page'] = 'https://github.com/user/project.git'
    # package.entry['version'] = '1.0'
    # package.extract_vcs()
    # assert package.entry == {
    #     'home_page': 'https://github.com/user/project.git',
    #     'version': '1.0',
    #     'github': True,
    #     'gitlab': False,
    #     'bitbucket': False,
    #     'github_user': 'user',
    #     'github_project': 'project'
    # }

