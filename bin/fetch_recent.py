from __future__ import print_function
import urllib2, json, re
import xml.etree.ElementTree as ET


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
        print(e, 'while fetching', latest_url)
        exit
    #print(rss_data)
    return rss_data

def save_json(entries):
    f = open('recent.json', 'w')
    f.write(json.dumps(entries))
    f.close()

def main():
    rss_data = get_latest()

    root = ET.fromstring(rss_data)

    entries = []
    for item in root.iter('item'):
        o = {}
        for name in ['title', 'link', 'description', 'pubDate']:
            o[name] = item.find(name).text

        url = o['link'] + '/json';
        #print(url)
        try:
            f = urllib2.urlopen(url)
            json_data = f.read()
            f.close()
        except urllib2.HTTPError as e:
            #print(e, 'while fetching', url)
            o['error'] = 'Could not fetch details of PyPi package'
            entries.append(o)
            continue

        package_data = json.loads(json_data)
        #print(package_data)
        if 'info' in package_data and 'home_page' in package_data['info']:
            o['home_page'] = package_data['info']['home_page']
        else:
            o['error'] = 'Could not find home_page'
            entries.append(o)
            continue

        try:
            match = re.search(r'^https?://github.com/(.*?)/?$', o['home_page'])
        except Exception as e:
            print(e)
            print(o['home_page'])
            continue

        if not match:
            o['error'] = 'Home page URL is not GitHub'
            entries.append(o)
            continue
        #print(o)

        travis_yml_url = 'https://raw.githubusercontent.com/' + match.group(1) + '/master/.travis.yml'
        #print(travis_yml_url)
        try:
            f = urllib2.urlopen(travis_yml_url)
            travis_yml = f.read()
            f.close()
        except urllib2.HTTPError as e:
            #print(e, 'while fetching', travis_yml_url)
            o['error'] = 'Could not find .travis.yml in the GitHub repository'
            entries.append(o)
            continue

        # if there is a travis.yml check the status
        travis_url = 'https://api.travis-ci.org/repos/' + match.group(1) + '/builds';
        #print(travis_url)
        try:
            req = urllib2.Request(travis_url)
            req.add_header('Accept', 'application/vnd.travis-ci.2+json')
            f = urllib2.urlopen(req)
            travis_data_json = f.read()
            f.close()
        except urllib2.HTTPError as e:
            #print(e, 'while fetching', travis_url)
            o['error'] = 'Could not get status from Travis-CI API'
            entries.append(o)
            continue

        travis_data = json.loads(travis_data_json)
        #print(travis_data)
        if not travis_data or 'builds' not in travis_data or len(travis_data['builds']) == 0:
            o['error'] = 'Could not find builds in data received from travis-ci.org'
            entries.append(o)
            continue

        o['travis_status'] = get_travis_status(travis_data['builds'])

        entries.append(o)
        #break
    save_json(entries)

main()
