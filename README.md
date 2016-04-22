Source code of http://pydigger.com/


TODO
======

* Search should also look into keywords



* Download zip file of the distribution, unzip it and check for certain files.

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
* List the packages that don't have a VCS listed, find out if they have VCS listed elsewhere, or if they are using some other VCS
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


Description
==============
Fetching RSS feed of recently uploaded packages https://pypi.python.org/pypi?%3Aaction=rss

Each entry in the RSS feed looks like this

  <item>
    <title>package-name 0.2.1</title>
    <link>http://pypi.python.org/pypi/package-name/0.2.1</link>
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
        "package_url": "http://pypi.python.org/pypi/PACKAGE",
        "author": "Person Name",
        "author_email": "user@domain",
        "download_url": "UNKNOWN",
        "platform": "UNKNOWN",
        "version": "1.0.0",
        "cheesecake_documentation_id": null,
        "_pypi_hidden": false,
        "description": "Some long description....",
        "release_url": "http://pypi.python.org/pypi/PACKAGE/1.0.0",
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
