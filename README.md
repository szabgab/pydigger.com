Source code of https://pydigger.com/

See the about page on the web site https://pydigger.com/about for some explanation.

[![Build Status](https://travis-ci.org/szabgab/pydigger.com.png)](https://travis-ci.org/szabgab/pydigger.com)

SETUP
========


```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install and launch MongoDB server.

Sign up to GitHub, get a "Personal access token" from https://github.com/settings/tokens and save it
in the github-token file in the root of the project.

```
repo
   x public_repo

user
   x read:user
   x user:email
```


Create config.yml that looks like this:

```
---
username: ""
password: ""
server: "localhost:27017"
dbname: "pydigger"
```


Run on the server in crontab:

```
source venv/bin/activate
python fetch_recent.py --update rss
python fetch_recent.py --update deps
```


Cleaning up database (during development)
```
$ mongodb      (On Ubuntu 2019.04 the client is called mongo)
> show dbs
> use pydigger
> db.dropDatabase()
```

Run the web server in development mode.

```
FLASK_APP=PyDigger.website FLASK_DEBUG=1 flask run  --port 5000 --host 127.0.0.1
```

TODO
======

* Merge the github-token in the configuration file
* Allow Travis to use a GitHub token for tests

* Be able to delete entries manually (and maybe even to set them to "not-to-index"
  if they might violate copyright or in some way might be illegal.
  mongo
  > use pydigger
  > db.packages.find({ "name" : "NAME-OF-THE-PAKAGE" })
  > db.packages.remove({ "name" : "NAME-OF-THE-PAKAGE" })

* Download zip file of the distribution, unzip it and check for certain files.
  Save the unzipped file and show the raw version of these file
  We have a central directory for all the unzipped source trees. We check the database, if the package has a
  "source_dir" we skip it.
  If it has no "source_dir" we check for "download_url" If there is a download_url we figure out what
  the "source_dir" should be. The same as the filename at the end of the download_url sans the extension.
  If that directory actually exists, we can check which other distribution had it. That should never happen, right?
  Download the zip file to a temp directory try to unzip the file and move it to the central directory.


* It seems sometimes we have entries in the RSS feed that don't have the 'releases' field updated yet. I wonder if I should include them in the database anyway?
  (They won't have an 'upload_time' either.) Maybe the entry should be included, using the PubDate as upload_time and then there should be a separate run that will
  go over all the entries with recent upload_time and if they don't have a 'download_url' then check them again.


* We might need to change the processing and update strategy so we won't rewrite the whole document every time, but we will update it.
This will allow us to process "just the JSON from PyPI" or "just the data from GitHub" or "just the data from the zip file".


* Shall we also store data about earlier versions of the packages?



When we process the RSS feed at first we only have name/version/description/pubDate, but even after fetching the JSON file we still might have only partial data.
This might be due to PyPI not processing the rest of the information yet (I think), or that the information included with this newer version of the
package lack some of the information. If we save either of these in the database we'll have packages with partial information, that might have
less data than we had earlier. If we want to notify people about lack of information we should be more patient and not rush this as some of that data might
arrive later, but then I wonder if we should already include this in the database. After all, someone might look at the database and see the package is missing some
vital information (e.g. download_url or the upload_time).


For when we will want to include all the packages from PyPI:
https://pypi.org/simple/  returns an HTML file listing all the packages on PyPI with entries looking like this:
<a href='2gis'>2gis</a><br/>
See also https://wiki.python.org/moin/PyPISimple

Write the log to a file or to the database and allow the web user to see the log. (Just make sure it does not include local path-es. Or maybe that does not matter?)
Specifically Write how many new packages were added (and which ones).
That way we will be able to see that the system is working properly.

Compute the stats from the command line and save them in the database to make it
faster to show the stats page. Use the --stats flag for that.

Convert the code to OOP

Check for various files that would indicate what testing framework each one of the projects use.


* bugtrack_url (For packages that have a home_dir pointing at github we can already fetch the issue count
    and we don't need to rely on this field but we can check if the bugtrack_url is related to the
    home_page or not. People could use this field to indicate their github repository though probably
    the best would be to have a separate field called repository_url.

* Is there a requirements.txt file? and test_requirements.txt ?
   package==version
   package>=version
   https://github.com/bitmazk/django-review  and
   https://github.com/ojarva/python-sshpubkeys
   were not stored correctly. I am not sure if this was an early version of my code
   or if my assumption about the requirement-parser is incorrect or if there is
   some other issue.


* Report when the URL provided as GitHub repo is invalid. (e.g. returns 404)
* Why are there maintainers where the value is "" and others where it is null ?
* Stats: author_email (look for null, "", "UNKNOWN", in the e_mail look for strings that don't look e-mail. e.g. no @)
* Code to update items
* Have a data for "updated" when we last updated the entry
* Create a list of "known licenses" and the names people use to refer to each license, link to the real license.
* Show licenses that don't fit in any of the "known licenses"
* On the package specific page link to explanations on how to correct where a field is missing.
* Show Green and red bars for each package on the listing page
* Find out what other services are used by Python packages
* Check for common files in Python packages
* Show which packages have strange version numbers (that cannot be parsed by ) https://www.python.org/dev/peps/pep-0396/
* Is the cheesecake_code_kwalitee_id still relevant? Integrate the old cheescake code.

* Statistics about types of "home_page" fields
* "home_page": "http://pmbio.github.io/limix/",
* "home_page": "http://ianmiell.github.io/shutit/",



Some of the packages have not a lot of details:

https://pypi.org/pypi/best_friends/json

This was the whole JSON: on

```
{
    "info": {
        "maintainer": null,
        "docs_url": null,
        "requires_python": null,
        "maintainer_email": null,
        "cheesecake_code_kwalitee_id": null,
        "keywords": null,
        "package_url": "http://pypi.org/pypi/best_friends",
        "author": "Joaish_fan",
        "author_email": "xianyunjianke@icloud.com",
        "download_url": "UNKNOWN",
        "platform": "UNKNOWN",
        "version": "1.0.0",
        "cheesecake_documentation_id": null,
        "_pypi_hidden": false,
        "description": "UNKNOWN",
        "release_url": "http://pypi.org/pypi/best_friends/1.0.0",
        "downloads": {
            "last_month": 0,
            "last_week": 0,
            "last_day": 0
        },
        "_pypi_ordering": 0,
        "classifiers": [],
        "bugtrack_url": null,
        "name": "best_friends",
        "license": "UNKNOWN",
        "summary": "A simple app for testing",
        "home_page": "http://www.xianyunjianke.com",
        "cheesecake_installability_id": null
    },
    "releases": {
        "1.0.0": []
    },
    "urls": []
}
```


Description
==============
Fetching RSS feed of recently uploaded packages https://pypi.org/rss/updates.xml

Each entry in the RSS feed looks like this

  <item>
    <title>package-name 0.2.1</title>
    <link>http://pypi.org/pypi/package-name/0.2.1</link>
    <description>short description</description>
    <pubDate>25 Mar 2016 12:36:38 GMT</pubDate>
  </item>

Accessing the link followed by /json returns a JSON structure with a lot more details about
the specific version of the given package. Like this:

{
    "info": {
        "maintainer": null,
        "docs_url": null,
        "requires_python": null,
        "maintainer_email": null,
        "cheesecake_code_kwalitee_id": null,
        "keywords": null,
        "package_url": "http://pypi.org/pypi/PACKAGE",
        "author": "Person Name",
        "author_email": "user@domain",
        "download_url": "UNKNOWN",
        "platform": "UNKNOWN",
        "version": "1.0.0",
        "cheesecake_documentation_id": null,
        "_pypi_hidden": false,
        "description": "Some long description....",
        "release_url": "http://pypi.org/pypi/PACKAGE/1.0.0",
        "downloads": {
            "last_month": 0,
            "last_week": 0,
            "last_day": 0
        },
        "_pypi_ordering": 0,
        "classifiers": [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: GNU General Public License (GPL)",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 3"
        ],
        "name": "PACKAGE",
        "bugtrack_url": null,
        "license": "GPLv3",
        "summary": "short summary",
        "home_page": "URL",
        "cheesecake_installability_id": null
    },
    "releases": {
        "1.0.0": []
    },
    "urls": []
}


We save these two data structures and in addition we try to determine if the package has Git repository and
if Travis-CI is configured in that repository.

We cannot store the data received from Pypi as it is in a MongoDB database as
it has places where the version number is a key and has . in it which cannot be
a key in MongoDB.

Show statistics about each field we show on the stats page.

Go over all the packages that have dependencies and add all the dependencies to the database.

Case sensitivity. It seems the package names in the requirements.txt file
don't always match the case that was used by the author of the package which currently
creates duplicate entries for some of the packages.
The JSON file from PyPI contains the name of the package in the proper case.
When we search for packages we should use a case insensitive search { $strcasecmp: [ <expression1>, <expression2> ] }
or maybe we should store a lowercase version of each name, in addition to the official spelling.
URLs in any case should redirect to the canonical spelling.

Keywords:
Split up the keywords that have comma in them based on the comma.
If there is no comma in the keywords we assume space to be the separator ad split based on space.
We convert all keywords to lower case to avoid "JSON" and "json" being different.

Search
  For matching name
  Exactly same keywords


Manual research

```
$ mongodb
> use pydigger
> db.packages.find().count();
> db.packages.find({ "home_page" : /gitlab/ }).count();
> db.packages.find({ $and: [{ "home_page" : { $not : /gitlab|github|bitbucket/ } } , { "home_page" : { $not : /^(UNKNOWN|)$/ } }] }, { home_page: 1 });
```

## Indexes added

```
db.packages.createIndex( { github: -1 } )
db.packages.createIndex( { split_keywords: -1 } )
db.packages.createIndex( { name: -1 } )
db.packages.createIndex( { upload_time: -1 } )

```

Failed to index:

db.packages.createIndex( { author: -1 } )
db.packages.createIndex( { license: -1 } )

Copyright and LICENSE
======================

Copyright 2020 Gábor Szabó

The source code in this repository is licensed under the MIT License.

The content of the site as collected from the various sources
are copyright the respective parties.






