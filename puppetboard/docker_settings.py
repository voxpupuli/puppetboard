import os

PUPPETDB_HOST = os.getenv('PUPPETDB_HOST', 'puppetdb')
PUPPETDB_PORT = int(os.getenv('PUPPETDB_PORT', '8080'))
# Since this is an env it will always be a string, we need
# to conver that string to a bool
SSL_VERIFY = os.getenv('PUPPETDB_SSL_VERIFY', 'True')
if SSL_VERIFY.upper() == 'TRUE':
    PUPPETDB_SSL_VERIFY = True
elif SSL_VERIFY.upper() == 'FALSE':
    PUPPETDB_SSL_VERIFY = False
else:
    PUPPETDB_SSL_VERIFY = SSL_VERIFY

PUPPETDB_KEY = os.getenv('PUPPETDB_KEY', None)
PUPPETDB_CERT = os.getenv('PUPPETDB_CERT', None)
PUPPETDB_PROTO = os.getenv('PUPPETDB_PROTO', None)
PUPPETDB_TIMEOUT = int(os.getenv('PUPPETDB_TIMEOUT', '20'))
DEFAULT_ENVIRONMENT = os.getenv('DEFAULT_ENVIRONMENT', 'production')
SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
DEV_LISTEN_HOST = os.getenv('DEV_LISTEN_HOST', '127.0.0.1')
DEV_LISTEN_PORT = int(os.getenv('DEV_LISTEN_PORT', '5000'))
DEV_COFFEE_LOCATION = os.getenv('DEV_COFFEE_LOCATION', 'coffee')
UNRESPONSIVE_HOURS = int(os.getenv('UNRESPONSIVE_HOURS', '2'))
ENABLE_QUERY = os.getenv('ENABLE_QUERY', 'True')
# Uncomment to restrict the enabled PuppetDB endpoints in the query page.
# ENABLED_QUERY_ENDPOINTS = ['facts', 'nodes']

LOCALISE_TIMESTAMP = bool(os.getenv('LOCALISE_TIMESTAMP',
                                    'True').upper() == 'TRUE')
LOGLEVEL = os.getenv('LOGLEVEL', 'info')
NORMAL_TABLE_COUNT = int(os.getenv('REPORTS_COUNT', '100'))
LITTLE_TABLE_COUNT = int(os.getenv('LITTLE_TABLE_COUNT', '10'))

TABLE_COUNT_DEF = "10,20,50,100,500"
TABLE_COUNT_SELECTOR = [int(x) for x in os.getenv('TABLE_COUNT_SELECTOR',
                                                  TABLE_COUNT_DEF).split(',')]

DISP_METR_DEF = ','.join(['resources.total', 'events.failure',
                          'events.success', 'resources.skipped',
                          'events.noop'])

DISPLAYED_METRICS = [x.strip() for x in os.getenv('DISPLAYED_METRICS',
                                                  DISP_METR_DEF).split(',')]

OFFLINE_MODE = bool(os.getenv('OFFLINE_MODE', 'False').upper() == 'TRUE')
ENABLE_CATALOG = bool(os.getenv('ENABLE_CATALOG', 'False').upper() == 'TRUE')
OVERVIEW_FILTER = os.getenv('OVERVIEW_FILTER', None)
PAGE_TITLE = os.getenv('PAGE_TITLE', 'Puppetboard')

GRAPH_FACTS_DEFAULT = ','.join(['architecture', 'clientversion', 'domain',
                                'lsbcodename', 'lsbdistcodename', 'lsbdistid',
                                'lsbdistrelease', 'lsbmajdistrelease',
                                'netmask', 'osfamily', 'puppetversion',
                                'processorcount'])

GRAPH_FACTS = [x.strip() for x in os.getenv('GRAPH_FACTS',
                                            GRAPH_FACTS_DEFAULT).split(',')]

GRAPH_TYPE = os.getenv('GRAPH_TYPE', 'pie')

# Tuples are hard to express as an environment variable, so here
# the tupple can be listed as a list of items
# export INVENTORY_FACTS="Hostname, fqdn, IP Address, ipaddress,.. etc"
# Define default array of of strings, this code is a bit neater than having
# a large string
INVENTORY_FACTS_DEFAULT = ','.join(['Hostname', 'fqdn',
                                    'IP Address', 'ipaddress',
                                    'OS', 'lsbdistdescription',
                                    'Architecture', 'hardwaremodel',
                                    'Kernel Version', 'kernelrelease',
                                    'Puppet Version', 'puppetversion'])

# take either input as a list Key, Value, Key, Value,  and conver it to an
# array: ['Key', 'Value']
INV_STR = os.getenv('INVENTORY_FACTS', INVENTORY_FACTS_DEFAULT).split(',')

# Take the Array and convert it to a tuple
INVENTORY_FACTS = [(INV_STR[i].strip(),
                    INV_STR[i + 1].strip()) for i in range(0, len(INV_STR), 2)]

REFRESH_RATE = int(os.getenv('REFRESH_RATE', '30'))

DAILY_REPORTS_CHART_ENABLED = bool(os.getenv('DAILY_REPORTS_CHART_ENABLED',
                                             'True').upper() == 'TRUE')
DAILY_REPORTS_CHART_DAYS = int(os.getenv('DAILY_REPORTS_CHART_DAYS', '8'))
