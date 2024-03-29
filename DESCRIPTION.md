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


Enabled monitoring in the Docker version of the production server.

```
db.enableFreeMonitoring()
```

