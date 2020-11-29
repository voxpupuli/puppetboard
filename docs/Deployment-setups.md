# Deployment setups

| ⚠️ These docs may be outdated. Pull Requests with updates are very welcome! |
| --- |

To run Puppetboard in production we provide instructions for the following scenarios:

-   Apache + mod\_wsgi
-   Apache + mod\_passenger
-   nginx + uwsgi
-   nginx + gunicorn

If you deploy Puppetboard through a different setup we'd welcome a pull request that adds the instructions to this section.

Installation On Linux Distros \^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^\^

[Debian Jessie Install](docs/Debian-Jessie.md).

## Apache + mod_wsgi

First we need to create the necessary directories:

``` {.sourceCode .bash}
$ mkdir -p /var/www/html/puppetboard
```

Copy Puppetboard's `default_settings.py` to the newly created puppetboard directory and name the file `settings.py`.
This file will be available at the path Puppetboard was installed, for example: `/usr/local/lib/pythonX.Y/lib/dist-packages/puppetboard/default_settings.py`.

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

Flask requires a static secret\_key, see [FlaskSession](http://flask.pocoo.org/docs/0.11/quickstart/#sessions),
in order to protect itself from CSRF exploits. The default secret\_key in `default_settings.py` generates 
a random 24 character string, however this string is re-generated on each request under httpd \>= 2.4.

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
    <Directory /usr/lib/pythonX.Y/site-packages/puppetboard/static>
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

Note the directory path, it's the path to where pip installed Puppetboard; X.Y must be replaced with your python 
version. We also alias the `/static` path so that Apache will serve the static files like the included CSS and Javascript.

## Apache + mod_passenger

It is possible to run Python applications through Passenger. Passenger has supported this since version 3 but it's 
considered experimental. Since the release of Passenger 4 it's a 'core' feature of the product.

Performance wise it also leaves something to be desired compared to the mod\_wsgi powered solution. Application 
start up is noticeably slower and loading pages takes a fraction longer.

First we need to create the necessary directories:

``` {.sourceCode .bash}
$ mkdir -p /var/www/puppetboard/{tmp,public}
```

Copy Puppetboard's `default_settings.py` to the newly created puppetboard directory and name the file `settings.py`.
This file will be available at the path Puppetboard was installed, for example: `/usr/local/lib/pythonX.Y/lib/dist-packages/puppetboard/default_settings.py`.

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

Unfortunately due to the way Passenger works we also need to configure logging inside `passenger_wsgi.py` 
else application start up issues won't be logged.

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

Note the `/static` alias path, it's the path to where pip installed Puppetboard. This is needed so that Apache 
will serve the static files like the included CSS and Javascript.

## nginx + uwsgi/gunicorn

A common Python deployment scenario is to use the uwsgi application server (which can also serve rails/rack, PHP, Perl 
and other applications) and proxy to it through something like nginx or perhaps even HAProxy.

uwsgi has a feature that every instance can run as its own user. In this example we'll use the `www-data` user 
but you can create a separate user solely for running Puppetboard and use that instead.

First we need to create the necessary directories:

``` {.sourceCode .bash}
$ mkdir -p /var/www/puppetboard
```

Copy Puppetboard's `default_settings.py` to the newly created puppetboard directory and name the file `settings.py`.
This file will be available at the path Puppetboard was installed,
for example: `/usr/local/lib/pythonX.Y/lib/dist-packages/puppetboard/default_settings.py`.

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

If all went well you should now be able to access to Puppetboard. Note the `/static` location block to make nginx 
serve static files like the included CSS and Javascript.

Because nginx natively supports the uwsgi protocol we use `uwsgi_pass` instead of the traditional `proxy_pass`.

nginx + gunicorn \^\^\^\^\^\^\^\^\^\^\^\^\^ You can use gunicorn instead of uwsgi if you prefer, the process doesn't 
differ too much. As we can't use `uwsgi_pass` with gunicorn, the nginx configuration file is going to differ a bit:

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

As we may want to serve in the background, and we need `PUPPETBOARD_SETTINGS` as an environment variable,
is recommendable to run this under supervisor. An example supervisor config with basic settings is the following:

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
chdir   = '/usr/lib/pythonX.Y/site-packages/puppetboard'
raw_env = ['PUPPETBOARD_SETTINGS=/var/www/puppetboard/settings.py', 'http_proxy=']
```

# Security

If you wish to make users authenticate before getting access to Puppetboard you can use one of the following configuration snippets.

## Apache

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

## nginx

Inside the `location / {}` block that has the `uwsgi_pass` directive:

``` {.sourceCode .nginx}
auth_basic "Puppetboard";
auth_basic_user_file /path/to/a/file.htpasswd;
```
