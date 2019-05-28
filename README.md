Puppetboard
===========

[![image](https://travis-ci.org/voxpupuli/puppetboard.svg?branch=master)](https://travis-ci.org/voxpupuli/puppetboard)

[![image](https://coveralls.io/repos/github/voxpupuli/puppetboard/badge.svg?branch=master)](https://coveralls.io/github/voxpupuli/puppetboard?branch=master)

Puppetboard is a web interface to [PuppetDB](https://puppet.com/docs/puppetdb/latest/index.html) aiming to replace the reporting functionality of [Puppet Dashboard](http://docs.puppetlabs.com/dashboard/).

Puppetboard relies on the [pypuppetdb](https://pypi.python.org/pypi/pypuppetdb) library to fetch data from PuppetDB and is built with the help of the [Flask](http://flask.pocoo.org) microframework.

As of version 0.1.0 and higher, Puppetboard **requires** PuppetDB 3. Version 0.3.0 has been tested with PuppetDB versions 3 through 6.

At the current time of writing, Puppetboard supports the following Python versions:

* Python 2.7
* Python 3.5
* Python 3.6
* Python 3.7

![View of a node](screenshots/overview.png)

Installation
------------

Puppetboard is now packaged and available on PyPi.

### Production

#### Puppet module

There is a [Puppet module](https://forge.puppetlabs.com/puppet/puppetboard) by [Spencer Krum](https://github.com/nibalizer) that takes care of installing Puppetboard for you.

You can install it with:

> puppet module install puppet-puppetboard

To see how to get it working with EL7 check out these [docs](https://github.com/voxpupuli/puppetboard/blob/master/docs/EL7.md).

#### Manual

To install it simply issue the following command:

``` {.sourceCode .bash}
$ pip install puppetboard
```

This will install Puppetboard and take care of the dependencies. If you do this Puppetboard will be installed in the so called site-packages or dist-packages of your Python distribution.

The complete path on Debian and Ubuntu systems would be `/usr/local/lib/pythonX.Y/lib/dist-packages/puppetboard` and on Fedora would be `/usr/lib/pythonX.Y/site-packages/puppetboard`

where X and Y are replaced by your major and minor python versions.

You will need this path in order to configure your HTTPD and WSGI-capable application server.

#### Packages

Native packages for your operating system will be provided in the near future.

<table>
<colgroup>
<col width="25%" />
<col width="15%" />
<col width="58%" />
</colgroup>
<thead>
<tr class="header">
<th align="left">OS</th>
<th align="left">Status</th>
<th align="left"></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td align="left">Debian 6/Squeeze</td>
<td align="left">planned</td>
<td align="left">Requires Backports</td>
</tr>
<tr class="even">
<td align="left">Debian 7/Wheezy</td>
<td align="left">planned</td>
<td align="left"></td>
</tr>
<tr class="odd">
<td align="left">Ubuntu 13.04</td>
<td align="left">planned</td>
<td align="left"></td>
</tr>
<tr class="even">
<td align="left">Ubuntu 13.10</td>
<td align="left">planned</td>
<td align="left"></td>
</tr>
<tr class="odd">
<td align="left">CentOS/RHEL 5</td>
<td align="left">n/a</td>
<td align="left">Python 2.4</td>
</tr>
<tr class="even">
<td align="left">CentOS/RHEL 6</td>
<td align="left">planned</td>
<td align="left"></td>
</tr>
<tr class="odd">
<td align="left"><a href="https://build.opensuse.org/package/show/systemsmanagement:puppet/python-puppetboard">OpenSuSE 12/13</a></td>
<td align="left">available</td>
<td align="left">Maintained on <a href="https://build.opensuse.org/package/show/systemsmanagement:puppet/python-puppetboard">OpenSuSE Build Service</a></td>
</tr>
<tr class="even">
<td align="left"><a href="https://build.opensuse.org/package/show/systemsmanagement:puppet/python-puppetboard">SuSE LE 11 SP3</a></td>
<td align="left">available</td>
<td align="left">Maintained on <a href="https://build.opensuse.org/package/show/systemsmanagement:puppet/python-puppetboard">OpenSuSE Build Service</a></td>
</tr>
<tr class="odd">
<td align="left"><a href="https://aur.archlinux.org/packages/python2-puppetboard/">ArchLinux</a></td>
<td align="left">available</td>
<td align="left">Maintained by <a href="https://github.com/bastelfreak">Tim Meusel</a></td>
</tr>
<tr class="even">
<td align="left"><a href="http://www.openbsd.org/cgi-bin/cvsweb/ports/www/puppetboard/">OpenBSD</a></td>
<td align="left">available</td>
<td align="left">Maintained by <a href="https://github.com/buzzdeee">Sebastian Reitenbach</a></td>
</tr>
</tbody>
</table>

#### Docker Images

A [Dockerfile](https://github.com/voxpupuli/puppetboard/blob/master/Dockerfile) was added to the source-code in the 0.2.0 release. An officially image is planned for the 0.2.x series.

Usage:

``` {.sourceCode .bash}
$ docker build -t puppetboard .
$ docker run -it -p 9080:80 -v /etc/puppetlabs/puppet/ssl:/etc/puppetlabs/puppet/ssl \
  -e PUPPETDB_HOST=<hostname> \
  -e PUPPETDB_PORT=8081 \
  -e PUPPETDB_SSL_VERIFY=/etc/puppetlabs/puppetdb/ssl/ca.pem \
  -e PUPPETDB_KEY=/etc/puppetlabs/puppetdb/ssl/private.pem \
  -e PUPPETDB_CERT=/etc/puppetlabs/puppetdb/ssl/public.pem \
  -e INVENTORY_FACTS='Hostname,fqdn, IP Address,ipaddress' \
  -e ENABLE_CATALOG=True \
  -e GRAPH_FACTS='architecture,puppetversion,osfamily' \
  puppetboard
```

To set a URL prefix you can use the optional `PUPPETBOARD_URL_PREFIX`
environment variable.

### Development

If you wish to hack on Puppetboard you should fork/clone the Github repository and then install the requirements through:

``` {.sourceCode .bash}
$ pip install -r requirements-test.txt
```

You're advised to do this inside a virtualenv specifically created to work on Puppetboard as to not pollute your global Python installation.

Configuration
-------------

The following instructions will help you configure Puppetboard and your HTTPD.

### Puppet

Puppetboard is built completely around PuppetDB which means your environment needs to be configured [to do that](https://puppet.com/docs/puppetdb/latest/connect_puppet_master.html#step-2-edit-config-files).

In order to get the reports to show up in Puppetboard you need to configure your environment to store those reports in PuppetDB. Have a look at [the documentation](https://puppet.com/docs/puppetdb/latest/connect_puppet_master.html#edit-puppetconf) about this, specifically the *Enabling report storage* section.

### Settings

Puppetboard will look for a file pointed at by the `PUPPETBOARD_SETTINGS` environment variable. The file has to be identical to `default_settings.py` but should only override the settings you need changed.

You can grab a copy of `default_settings.py` from the path where pip installed Puppetboard to or by looking in the source checkout.

If you run PuppetDB and Puppetboard on the same machine the default settings provided will be enough to get you started and you won't need a custom settings file.

Assuming your webserver and PuppetDB machine are not identical you will at least have to change the following settings:

-   `PUPPETDB_HOST`
-   `PUPPETDB_PORT`

By default PuppetDB requires SSL to be used when a non-local client wants to connect. Therefor you'll also have to supply the following settings:

-   `PUPPETDB_SSL_VERIFY = /path/to/ca/keyfile.pem`
-   `PUPPETDB_KEY = /path/to/private/keyfile.pem`
-   `PUPPETDB_CERT = /path/to/public/keyfile.crt`

For information about how to generate the correct keys please refer to the [pypuppetdb documentation](http://pypuppetdb.readthedocs.org/en/v0.1.0/quickstart.html#ssl). Alternatively is possible to explicitly specify the protocol to be used setting the `PUPPETDB_PROTO` variable.

Other settings that might be interesting in no particular order:

-   `SECRET_KEY`: Refer to [Flask documentation](http://flask.pocoo.org/docs/0.10/quickstart/#sessions), section sessions: How to generate good secret keys, to set the value. Defaults to a random 24-char string generated by os.random(24)
-   `PUPPETDB_TIMEOUT`: Defaults to 20 seconds but you might need to increase this value. It depends on how big the results are when querying PuppetDB. This behaviour will change in a future release when pagination will be introduced.
-   `UNRESPONSIVE_HOURS`: The amount of hours since the last check-in after which a node is considered unresponsive.
-   `LOGLEVEL`: A string representing the loglevel. It defaults to `'info'` but can be changed to `'warning'` or `'critical'` for less verbose logging or `'debug'` for more information.
-   `ENABLE_QUERY`: Defaults to `True` causing a Query tab to show up in the web interface allowing users to write and execute arbitrary queries against a set of endpoints in PuppetDB. Change this to `False` to disable this. See `ENABLED_QUERY_ENDPOINTS` to fine-tune which endpoints are allowed.
-   `ENABLED_QUERY_ENDPOINTS`: If `ENABLE_QUERY` is `True`, allow to fine tune the endpoints of PuppetDB APIs that can be queried. It must be a list of strings of PuppetDB endpoints for which the query is enabled. See the `QUERY_ENDPOINTS` constant in the `puppetboard.app` module for a list of the available endpoints.
-   `GRAPH_TYPE`: Specify the type of graph to display.   Default is
    pie, other good option is donut.   Other choices can be found here:
    \_C3JS\_documentation\`
-   `GRAPH_FACTS`: A list of fact names to tell PuppetBoard to generate a pie-chart on the fact page. With some fact values being unique per node, like ipaddress, uuid, and serial number, as well as structured facts it was no longer feasible to generate a graph for everything.
-   `INVENTORY_FACTS`: A list of tuples that serve as the column header and the fact name to search for to create the inventory page. If a fact is not found for a node then `undef` is printed.
-   `ENABLE_CATALOG`: If set to `True` allows the user to view a node's latest catalog. This includes all managed resources, their file-system locations and their relationships, if available. Defaults to `False`.
-   `REFRESH_RATE`: Defaults to `30` the number of seconds to wait until the index page is automatically refreshed.
-   `DEFAULT_ENVIRONMENT`: Defaults to `'production'`, as the name suggests, load all information filtered by this environment value.
-   `REPORTS_COUNT`: Defaults to `10` the limit of the number of reports to load on the node or any reports page.
-   `OFFLINE_MODE`: If set to `True` load static assets (jquery, semantic-ui, etc) from the local web server instead of a CDN. Defaults to `False`.
-   `DAILY_REPORTS_CHART_ENABLED`: Enable the use of daily chart graphs when looking at dashboard and node view.
-   `DAILY_REPORTS_CHART_DAYS`: Number of days to show history for on the daily report graphs.
-   `DISPLAYED_METRICS`: Metrics to show when displaying node summary. Example: `'resources.total'`, `'events.noop'`.
-   `TABLE_COUNT_SELECTOR`: Configure the dropdown to limit number of hosts to show per page.
-   `LITTLE_TABLE_COUNT`: Default number of reports to show when when looking at a node.
-   `NORMAL_TABLE_COUNT`: Default number of nodes to show when displaying reports and catalog nodes.
-   `LOCALISE_TIMESTAMP`: Normalize time based on localserver time.
-   `DEV_LISTEN_HOST`: For use with dev.py for development. Default is localhost
-   `DEV_LISTEN_PORT`: For use with dev.py for development. Default is 5000

### Puppet Enterprise

Puppet Enterprise maintains a certificate white-list for which certificates are allowed to access data from PuppetDB. This whitelist is maintained in `/etc/puppetlabs/puppetdb/certificate-whitelist` and you have to add the certificate name to that file.

Afterwards you'll need to restart `pe-puppetdb` and you should be able to query PuppetDB freely now.

### Development

You can run it in development mode by simply executing:

``` {.sourceCode .bash}
$ python dev.py
```

Use `PUPPETBOARD_SETTINGS` to change the different settings or patch `default_settings.py` directly. Take care not to include your local changes on that file when submitting patches for Puppetboard. Place a settings.py file inside the base directory of the git repository that will be used, if the environment variable is not set.

### Production

To run Puppetboard in production we provide instructions for the following scenarios:

-   Apache + mod\_wsgi
-   Apache + mod\_passenger
-   nginx + uwsgi
-   nginx + gunicorn

If you deploy Puppetboard through a different setup we'd welcome a pull request that adds the instructions to this section.

Installation On Linux Distros \^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^

[Debian Jessie Install](docs/Debian-Jessie.md).

#### Apache + mod\_wsgi

First we need to create the necessary directories:

``` {.sourceCode .bash}
$ mkdir -p /var/www/html/puppetboard
```

Copy Puppetboard's `default_settings.py` to the newly created puppetboard directory and name the file `settings.py`. This file will be available at the path Puppetboard was installed, for example: `/usr/local/lib/pythonX.Y/lib/dist-packages/puppetboard/default_settings.py`.

Change the settings that need changing to match your environment and delete or comment with a `#` the rest of the entries.

If you don't need to change any settings you can skip the creation of the `settings.py` file entirely.

Now create a `wsgi.py` with the following content in the newly created puppetboard directory:

``` {.sourceCode .python}
from __future__ import absolute_import
import os

# Needed if a settings.py file exists
os.environ['PUPPETBOARD_SETTINGS'] = '/var/www/html/puppetboard/settings.py'
from puppetboard.app import app as application
```

Make sure this file is readable by the user the webserver runs as.

Flask requires a static secret\_key, see [FlaskSession](http://flask.pocoo.org/docs/0.11/quickstart/#sessions), in order to protect itself from CSRF exploits. The default secret\_key in `default_settings.py` generates a random 24 character string, however this string is re-generated on each request under httpd \>= 2.4.

To generate your own secret\_key create a python script with the following content and run it once:

``` {.sourceCode .python}
import os
os.urandom(24)
'\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8'
```

Copy the output and add the following to your `wsgi.py` file:

``` {.sourceCode .python}
application.secret_key = '<your secret key>'
```

The last thing we need to do is configure Apache.

Here is a sample configuration for Debian and Ubuntu:

``` {.sourceCode .apache}
<VirtualHost *:80>
    ServerName puppetboard.example.tld
    WSGIDaemonProcess puppetboard user=www-data group=www-data threads=5
    WSGIScriptAlias / /var/www/html/puppetboard/wsgi.py
    ErrorLog /var/log/apache2/puppetboard.error.log
    CustomLog /var/log/apache2/puppetboard.access.log combined

    Alias /static /usr/local/lib/pythonX.Y/dist-packages/puppetboard/static
    <Directory /usr/local/lib/pythonX.X/dist-packages/puppetboard/static>
        Satisfy Any
        Allow from all
    </Directory>

    <Directory /usr/local/lib/pythonX.Y/dist-packages/puppetboard>
        WSGIProcessGroup puppetboard
        WSGIApplicationGroup %{GLOBAL}
        Order deny,allow
        Allow from all
    </Directory>
</VirtualHost>
```

Here is a sample configuration for Fedora:

``` {.sourceCode .apache}
<VirtualHost *:80>
    ServerName puppetboard.example.tld
    WSGIDaemonProcess puppetboard user=apache group=apache threads=5
    WSGIScriptAlias / /var/www/html/puppetboard/wsgi.py
    ErrorLog logs/puppetboard-error_log
    CustomLog logs/puppetboard-access_log combined

    Alias /static /usr/lib/pythonX.Y/site-packages/puppetboard/static
    <Directory /usr/lib/python2.X/site-packages/puppetboard/static>
        Satisfy Any
        Allow from all
    </Directory>

    <Directory /usr/lib/pythonX.Y/site-packages/puppetboard>
        WSGIProcessGroup puppetboard
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>
</VirtualHost>
```

Note the directory path, it's the path to where pip installed Puppetboard; X.Y must be replaced with your python version. We also alias the `/static` path so that Apache will serve the static files like the included CSS and Javascript.

#### Apache + mod\_passenger

It is possible to run Python applications through Passenger. Passenger has supported this since version 3 but it's considered experimental. Since the release of Passenger 4 it's a 'core' feature of the product.

Performance wise it also leaves something to be desired compared to the mod\_wsgi powered solution. Application start up is noticeably slower and loading pages takes a fraction longer.

First we need to create the necessary directories:

``` {.sourceCode .bash}
$ mkdir -p /var/www/puppetboard/{tmp,public}
```

Copy Puppetboard's `default_settings.py` to the newly created puppetboard directory and name the file `settings.py`. This file will be available at the path Puppetboard was installed, for example: `/usr/local/lib/pythonX.Y/lib/dist-packages/puppetboard/default_settings.py`.

Change the settings that need changing to match your environment and delete or comment with a `#` the rest of the entries.

If you don't need to change any settings you can skip the creation of the `settings.py` file entirely.

Now create a `passenger_wsgi.py` with the following content in the newly created puppetboard directory:

``` {.sourceCode .python}
from __future__ import absolute_import
import os
import logging

logging.basicConfig(filename='/path/to/file/for/logging', level=logging.INFO)

# Needed if a settings.py file exists
os.environ['PUPPETBOARD_SETTINGS'] = '/var/www/puppetboard/settings.py'

try:
    from puppetboard.app import app as application
except Exception, inst:
    logging.exception("Error: %s", str(type(inst)))
```

Unfortunately due to the way Passenger works we also need to configure logging inside `passenger_wsgi.py` else application start up issues won't be logged.

This means that even though `LOGLEVEL` might be set in your `settings.py` this setting will take precedence over it.

Now the only thing left to do is configure Apache:

``` {.sourceCode .apache}
<VirtualHost *:80>
    ServerName puppetboard.example.tld
    DocumentRoot /var/www/puppetboard/public
    ErrorLog /var/log/apache2/puppetboard.error.log
    CustomLog /var/log/apache2/puppetboard.access.log combined

    RackAutoDetect On
    Alias /static /usr/local/lib/pythonX.Y/dist-packages/puppetboard/static
</VirtualHost>
```

Note the `/static` alias path, it's the path to where pip installed Puppetboard. This is needed so that Apache will serve the static files like the included CSS and Javascript.

#### nginx + uwsgi

A common Python deployment scenario is to use the uwsgi application server (which can also serve rails/rack, PHP, Perl and other applications) and proxy to it through something like nginx or perhaps even HAProxy.

uwsgi has a feature that every instance can run as its own user. In this example we'll use the `www-data` user but you can create a separate user solely for running Puppetboard and use that instead.

First we need to create the necessary directories:

``` {.sourceCode .bash}
$ mkdir -p /var/www/puppetboard
```

Copy Puppetboard's `default_settings.py` to the newly created puppetboard directory and name the file `settings.py`. This file will be available at the path Puppetboard was installed, for example: `/usr/local/lib/pythonX.Y/lib/dist-packages/puppetboard/default_settings.py`.

Change the settings that need changing to match your environment and delete or comment with a `#` the rest of the entries.

If you don't need to change any settings you can skip the creation of the `settings.py` file entirely.

Now create a `wsgi.py` with the following content in the newly created puppetboard directory:

``` {.sourceCode .python}
from __future__ import absolute_import
import os

# Needed if a settings.py file exists
os.environ['PUPPETBOARD_SETTINGS'] = '/var/www/puppetboard/settings.py'
from puppetboard.app import app as application
```

Make sure this file is owned by the user and group the uwsgi instance will run as.

Now we need to start uwsgi:

``` {.sourceCode .bash}
$ uwsgi --socket :9090 --wsgi-file /var/www/puppetboard/wsgi.py
```

Feel free to change the port to something other than `9090`.

The last thing we need to do is configure nginx to proxy the requests:

``` {.sourceCode .nginx}
upstream puppetboard {
    server 127.0.0.1:9090;
}

server {
    listen      80;
    server_name puppetboard.example.tld;
    charset     utf-8;

    location /static {
        alias /usr/local/lib/pythonX.Y/dist-packages/puppetboard/static;
    }

    location / {
        uwsgi_pass puppetboard;
        include    /path/to/uwsgi_params/probably/etc/nginx/uwsgi_params;
    }
}
```

If all went well you should now be able to access to Puppetboard. Note the `/static` location block to make nginx serve static files like the included CSS and Javascript.

Because nginx natively supports the uwsgi protocol we use `uwsgi_pass` instead of the traditional `proxy_pass`.

nginx + gunicorn \^\^\^\^\^\^\^\^\^\^\^\^\^ You can use gunicorn instead of uwsgi if you prefer, the process doesn't differ too much. As we can't use `uwsgi_pass` with gunicorn, the nginx configuration file is going to differ a bit:

``` {.sourceCode .nginx}
server {
    listen      80;
    server_name puppetboard.example.tld;
    charset     utf-8;

    location /static {
        alias /usr/local/lib/pythonX.Y/dist-packages/puppetboard/static;
    }

    location / {
        add_header Access-Control-Allow-Origin *;
        proxy_pass_header Server;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Scheme $scheme;
        proxy_connect_timeout 10;
        proxy_read_timeout 10;
        proxy_pass http://127.0.0.1:9090;
    }
}
```

Now, for running it with gunicorn:

``` {.sourceCode .bash}
$ cd /usr/local/lib/pythonX.Y/dist-packages/puppetboard
$ gunicorn -b 127.0.0.1:9090 puppetboard.app:app
```

As we may want to serve in the background, and we need `PUPPETBOARD_SETTINGS` as an environment variable, is recommendable to run this under supervisor. An example supervisor config with basic settings is the following:

``` {.sourceCode .ini}
[program:puppetboard]
command=gunicorn -b 127.0.0.1:9090 puppetboard.app:app
user=www-data
stdout_logfile=/var/log/supervisor/puppetboard/puppetboard.out
stderr_logfile=/var/log/supervisor/puppetboard/puppetboard.err
environment=PUPPETBOARD_SETTINGS="/var/www/puppetboard/settings.py"
```

For newer systems with systemd (for example CentOS7), you can use the following service file (`/usr/lib/systemd/system/gunicorn@.service`):

``` {.sourceCode .ini}
[Unit]
Description=gunicorn daemon for %i
After=network.target

[Service]
ExecStart=/usr/bin/gunicorn --config /etc/sysconfig/gunicorn/%i.conf %i
ExecReload=/bin/kill -s HUP $MAINPID
PrivateTmp=true
User=gunicorn
Group=gunicorn
```

And the corresponding gunicorn config (`/etc/sysconfig/gunicorn/puppetboard.app\:app.conf`):

``` {.sourceCode .ini}
import multiprocessing

bind    = '127.0.0.1:9090'
workers = multiprocessing.cpu_count() * 2 + 1
chdir   = '/usr/lib/python2.7/site-packages/puppetboard'
raw_env = ['PUPPETBOARD_SETTINGS=/var/www/puppetboard/settings.py', 'http_proxy=']
```

### Security

If you wish to make users authenticate before getting access to Puppetboard you can use one of the following configuration snippets.

#### Apache

Inside the `VirtualHost`:

``` {.sourceCode .apache}
<Location "/">
    AuthType Basic
    AuthName "Puppetboard"
    Require valid-user
    AuthBasicProvider file
    AuthUserFile /path/to/a/file.htpasswd
</Location>
```

#### nginx

Inside the `location / {}` block that has the `uwsgi_pass` directive:

``` {.sourceCode .nginx}
auth_basic "Puppetboard";
auth_basic_user_file /path/to/a/file.htpasswd;
```

Getting Help
------------

This project is still very new so it's not inconceivable you'll run into issues.

For bug reports you can file an [issue](https://github.com/voxpupuli/puppetboard/issues). If you need help with something feel free to hit up the maintainers by e-mail or on IRC. They can usually be found on [IRCnet](http://www.ircnet.org) and [Freenode](http://freenode.net) and idles in \#puppetboard.

There's now also the \#puppetboard channel on [Freenode](http://freenode.net) where we hang out and answer questions related to pypuppetdb and Puppetboard.

There is also a [GoogleGroup](https://groups.google.com/forum/?hl=en#!forum/puppet-community) to exchange questions and discussions. Please note that this group contains discussions of other Puppet Community projects.

Third party
-----------

Some people have already started building things with and around Puppetboard.

[Hunter Haugen](https://github.com/hunner) has provided a Vagrant setup:

-   <https://github.com/hunner/puppetboard-vagrant>

### Packages

-   An OpenBSD port is being maintained by [Sebastian Reitenbach](https://github.com/buzzdeee) and can be viewed [here](http://www.openbsd.org/cgi-bin/cvsweb/ports/www/puppetboard/).
-   A Docker image is being maintained by [Julien K.](https://github.com/juliengk) and can be viewed [here](https://registry.hub.docker.com/u/kassis/puppetboard/).

Contributing
------------

We welcome contributions to this project. However, there are a few ground rules contributors should be aware of.

### License

This project is licensed under the Apache v2.0 License. As such, your contributions, once accepted, are automatically covered by this license.

### Commit messages

Write decent commit messages. Don't use swear words and refrain from uninformative commit messages as 'fixed typo'.

The preferred format of a commit message:

    docs/quickstart: Fixed a typo in the Nodes section.

    If needed, elaborate further on this commit. Feel free to write a
    complete blog post here if that helps us understand what this is
    all about.

    Fixes #4 and resolves #2.

If you'd like a more elaborate guide on how to write and format your commit messages have a look at this post by [Tim Pope](http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html).

Examples
--------

[vagrant-puppetboard](https://github.com/visibilityspots/vagrant-puppet/tree/puppetboard)

A vagrant project to show off the puppetboard functionality using the puppetboard puppet module on a puppetserver with puppetdb.

Screenshots
-----------

![Overview / Index / Homepage](screenshots/overview.png)

![Nodes view, all active nodes](screenshots/nodes.png)

![Single node page / overview](screenshots/node.png)

![Report view](screenshots/report.png)

![Facts view](screenshots/facts.png)

![Single fact, with graphs](screenshots/fact.png)

![All nodes that have this fact with that value](screenshots/fact_value.png)

![Metrics view](screenshots/metrics.png)

![Single metric](screenshots/metric.png)

![Query view](screenshots/query.png)

![Error page](screenshots/broken.png)
