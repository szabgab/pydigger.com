from __future__ import print_function
import json, os

def main():
    with open('recent.json', 'r') as f:
        data = json.load(f)

    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport"
         content="width=device-width, initial-scale=1, user-scalable=yes">
      <title>Python for Code-Maven</title>
    </head>
    <body>
    <h1>Python for Code-Maven</h1>
    <table>
    <tr>
      <th>Name</th><th>Travis-CI</th><th>Error</th>
    </tr>
    '''

    for e in data:
        html += "<tr>"
        if 'home_page' in e:
            html += '<td><a href="' + e['home_page'] + '">' + e['title'] + '</a></td>'
        else:
            html += '<td>' + e['title'] + '</td>'

        if 'travis_status' in e:
            html += '<td><img src="/img/build-' + e['travis_status'] + '.png"></td>'
        else:
            html += '<td>na</td>'

    	html += '<td>' + e['error'] if 'error' in e else '&nbsp;' + '</td>';

        html += '</tr>\n'

    html += '''
    </table>

    <script>
      (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
      (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
      m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
      })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

      ga('create', 'UA-12199211-25', 'auto');
      ga('send', 'pageview');

    </script>


    </body>
    </html>
    '''

    d = 'html'
    try:
    	os.mkdir(d)
    except:
        pass

    fh = open('html/index.html', 'w')
    fh.write(html)
    fh.close
