# Install Using debian jessie

```
$ apt-get install python-pip git

$ mkdir /opt/voxpupuli-puppetboard/
$ cd /opt/voxpupuli-puppetboard/
$ git clone https://github.com/voxpupuli/puppetboard
$ cd /opt/voxpupuli-puppetboard/puppetboard
$ pip install puppetboard

```

* /etc/apache2/sites-available/voxpupuli-puppetboard.conf

```
    <VirtualHost *:80>
        ServerName puppetboard.my.domain
        WSGIDaemonProcess puppetboard user=www-data group=www-data threads=5 python-path=/usr/local/lib/python2.7/dist-packages/puppetboard:python-home=/opt/voxpupuli-puppetboard/puppetboard:/opt/voxpupuli-puppetboard/puppetboard/puppetboard:/usr/local/lib/python2.7/dist-packages/puppetboard/static
        WSGIScriptAlias / /opt/voxpupuli-puppetboard/puppetboard/wsgi.py
        ErrorLog /var/log/apache2/puppetboard.error.log
        CustomLog /var/log/apache2/puppetboard.access.log combined

        <Directory /opt/voxpupuli-puppetboard/puppetboard>
                <Files wsgi.py>
                  Order deny,allow
                  Allow from all
                Require all granted
                </Files>
        </Directory>

        Alias /static /usr/local/lib/python2.7/dist-packages/puppetboard/static
        <Directory /usr/local/lib/python2.7/dist-packages/puppetboard/static>
            Satisfy Any
            Allow from all
                Require all granted
        </Directory>

        <Directory /usr/local/lib/python2.7/dist-packages/puppetboard>
            WSGIProcessGroup puppetboard
            WSGIApplicationGroup %{GLOBAL}
            Order deny,allow
            Allow from all
                Require all granted
        </Directory>
    </VirtualHost>
```

```
$ a2ensite voxpupuli-puppetboard.conf
```

* /opt/voxpupuli-puppetboard/puppetboard/wsgi.py
```
from __future__ import absolute_import
import os

import sys
sys.path.append('/opt/voxpupuli-puppetboard/puppetboard')

from puppetboard.app import app as application
```
