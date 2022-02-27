import os

PUPPETDB_HOST = 'localhost'
PUPPETDB_PORT = 8080
PUPPETDB_PROTO = None
PUPPETDB_SSL_VERIFY = True
PUPPETDB_KEY = None
PUPPETDB_CERT = None
PUPPETDB_TIMEOUT = 20
DEFAULT_ENVIRONMENT = 'production'
SECRET_KEY = os.urandom(24)
DEV_LISTEN_HOST = '127.0.0.1'
DEV_LISTEN_PORT = 5555
DEV_COFFEE_LOCATION = 'coffee'
UNRESPONSIVE_HOURS = 2
ENABLE_QUERY = True
# Uncomment to restrict the enabled PuppetDB endpoints in the query page.
# ENABLED_QUERY_ENDPOINTS = ['facts', 'nodes']
LOCALISE_TIMESTAMP = True
LOGLEVEL = 'info'
NORMAL_TABLE_COUNT = 100
LITTLE_TABLE_COUNT = 10
TABLE_COUNT_SELECTOR = [10, 20, 50, 100, 500]
DISPLAYED_METRICS = ['resources.total',
                     'events.failure',
                     'events.success',
                     'resources.skipped',
                     'events.noop']
OFFLINE_MODE = False
ENABLE_CATALOG = False
OVERVIEW_FILTER = None
PAGE_TITLE = "Puppetboard"
GRAPH_TYPE = 'pie'
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
INVENTORY_FACTS = [('Hostname', 'fqdn'),
                   ('IP Address', 'ipaddress'),
                   ('OS', 'lsbdistdescription'),
                   ('Architecture', 'hardwaremodel'),
                   ('Kernel Version', 'kernelrelease'),
                   ('Puppet Version', 'puppetversion'), ]
REFRESH_RATE = 30
DAILY_REPORTS_CHART_ENABLED = True
DAILY_REPORTS_CHART_DAYS = 8
WITH_EVENT_NUMBERS = True

SHOW_ERROR_AS = 'friendly'  # or 'raw'
CODE_PREFIX_TO_REMOVE = '/etc/puppetlabs/code/environments'
