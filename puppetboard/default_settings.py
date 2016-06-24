import os

PUPPETDB_HOST = 'localhost'
PUPPETDB_PORT = 8080
PUPPETDB_SSL_VERIFY = True
PUPPETDB_KEY = None
PUPPETDB_CERT = None
PUPPETDB_TIMEOUT = 20
DEFAULT_ENVIRONMENT = 'production'
SECRET_KEY = os.urandom(24)
DEV_LISTEN_HOST = '127.0.0.1'
DEV_LISTEN_PORT = 5000
DEV_COFFEE_LOCATION = 'coffee'
UNRESPONSIVE_HOURS = 2
ENABLE_QUERY = True
LOCALISE_TIMESTAMP = True
LOGLEVEL = 'info'
REPORTS_COUNT = 10
OFFLINE_MODE = False
ENABLE_CATALOG = False
OVERVIEW_FILTER = None
GRAPH_FACTS = ['architecture',
               'clientversion',
               'domain',
               'lsbcodename',
               'lsbdistcodename',
               'lsbdistid',
               'lsbdistrelease',
               'lsbmajdistrelease',
               'netmask',
               'osfamily',
               'puppetversion',
               'processorcount']
INVENTORY_FACTS = [ ('Hostname',       'fqdn'              ),
                    ('IP Address',     'ipaddress'         ),
                    ('OS',             'lsbdistdescription'),
                    ('Architecture',   'hardwaremodel'     ),
                    ('Kernel Version', 'kernelrelease'     ),
                    ('Puppet Version', 'puppetversion'     ), ]
REFRESH_RATE = 30
