import json
import os
import secrets
import tempfile
import base64
import binascii


def cert_to_file(cert_file_or_string):
    """
    cert_to_file takes in a string, if it looks like a certificate, save the contents to a temporary
    file and return the path to that temporary file

    cert_to_file also supports base64 encoded certificates, in cases where newlines cause problems

    Note: NamedTemporaryFile does not work great with Windows, but since this is for Docker
    hopefully we'll be fine.
    """
    if isinstance(cert_file_or_string, str):
        try:
            cert_str = base64.b64decode(cert_file_or_string).decode()
        except (UnicodeDecodeError, binascii.Error):
            cert_str = cert_file_or_string

        if '-----BEGIN' in cert_str:
            with tempfile.NamedTemporaryFile(delete=False, suffix='puppetboard_cert') as tmpfile:
                tmpfile.write(cert_str.encode())
                tmpfile.close()
            return tmpfile.name
        else:
            return cert_file_or_string
    else:
        return cert_file_or_string


def coerce_bool(v, default):
    """Convert boolean-like values into a boolean."""

    if v in [True, False]:
        return v
    s = str(v).lower().strip()
    if s in ['true', 't', 'y', 'yes', '1']:
        return True
    if s in ['false', 'f', 'n', 'no', '0']:
        return False
    return default

APPLICATION_ROOT = os.getenv('PUPPETBOARD_URL_PREFIX','/')

PUPPETDB_HOST = os.getenv('PUPPETDB_HOST', 'puppetdb')
PUPPETDB_PORT = int(os.getenv('PUPPETDB_PORT', '8080'))
# This may be a bool in string - that's what coerce_bool is for
# but if it is other string, then it's a path
PUPPETDB_SSL_VERIFY = coerce_bool(
    os.getenv('PUPPETDB_SSL_VERIFY', True),
    cert_to_file(os.getenv('PUPPETDB_SSL_VERIFY'))
)

PUPPETDB_KEY = cert_to_file(os.getenv('PUPPETDB_KEY', None))
PUPPETDB_CERT = cert_to_file(os.getenv('PUPPETDB_CERT', None))
PUPPETDB_PROTO = os.getenv('PUPPETDB_PROTO', None)
PUPPETDB_TIMEOUT = int(os.getenv('PUPPETDB_TIMEOUT', '20'))
DEFAULT_ENVIRONMENT = os.getenv('DEFAULT_ENVIRONMENT', 'production')
# this empty string has to be changed, we validate it with check_secret_key()
SECRET_KEY = os.getenv('SECRET_KEY', '')  # nosec
UNRESPONSIVE_HOURS = int(os.getenv('UNRESPONSIVE_HOURS', '2'))
ENABLE_QUERY = coerce_bool(os.getenv('ENABLE_QUERY'), True)
# Uncomment to restrict the enabled PuppetDB endpoints in the query page.
# ENABLED_QUERY_ENDPOINTS = ['facts', 'nodes']

LOCALISE_TIMESTAMP = coerce_bool(os.getenv('LOCALISE_TIMESTAMP'), True)
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

OFFLINE_MODE = coerce_bool(os.getenv('OFFLINE_MODE'), False)
ENABLE_CATALOG = coerce_bool(os.getenv('ENABLE_CATALOG'), False)
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
# the tuple can be listed as a list of items
# export INVENTORY_FACTS="Hostname, fqdn, IP Address, ipaddress,.. etc"
# Define default array of of strings, this code is a bit neater than having
# a large string
INVENTORY_FACTS_DEFAULT = ','.join(['Hostname', 'trusted',
                                    'IP Address', 'networking',
                                    'OS', 'os',
                                    'Architecture', 'hardwaremodel',
                                    'Kernel Version', 'kernelrelease',
                                    'Puppet Version', 'puppetversion'])

# take either input as a list Key, Value, Key, Value,  and conver it to an
# array: ['Key', 'Value']
INV_STR = os.getenv('INVENTORY_FACTS', INVENTORY_FACTS_DEFAULT).split(',')

# To render jinja template we expect env var to be JSON
INVENTORY_FACT_TEMPLATES = {
    'trusted': (
        """<a href="{{url_for('node', env=current_env, node_name=value.certname)}}">"""
        """{{value.hostname}}"""
        """</a>"""
    ),
    'networking': """{{ value.ip }}""",
    'os': "{{ fact_os_detection(value) }}",
}

INV_TPL_STR = os.getenv('INVENTORY_FACT_TEMPLATES')

if INV_TPL_STR:
    INVENTORY_FACT_TEMPLATES = json.loads(INV_TPL_STR)


# Take the Array and convert it to a tuple
INVENTORY_FACTS = [(INV_STR[i].strip(),
                    INV_STR[i + 1].strip()) for i in range(0, len(INV_STR), 2)]

REFRESH_RATE = int(os.getenv('REFRESH_RATE', '30'))

DAILY_REPORTS_CHART_ENABLED = coerce_bool(os.getenv('DAILY_REPORTS_CHART_ENABLED'), True)
DAILY_REPORTS_CHART_DAYS = int(os.getenv('DAILY_REPORTS_CHART_DAYS', '8'))

WITH_EVENT_NUMBERS = coerce_bool(os.getenv('WITH_EVENT_NUMBERS'), True)

SHOW_ERROR_AS = os.getenv('SHOW_ERROR_AS', 'friendly')
CODE_PREFIX_TO_REMOVE = os.getenv('CODE_PREFIX_TO_REMOVE', '/etc/puppetlabs/code/environments')
FAVORITE_ENVS_DEF = ','.join([
    'production',
    'staging',
    'qa',
    'dev',
])
FAVORITE_ENVS = [x.strip() for x in os.getenv('FAVORITE_ENVS', FAVORITE_ENVS_DEF).split(',')]


# Enable classes view (displays the number of changed resources
# by status and class)
ENABLE_CLASS = coerce_bool(os.getenv('ENABLE_CLASS'), False)

# Use caching if classes view is enabled
CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '3600'))
CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')
CACHE_MEMCACHED_SERVERS_DEFAULT = ','.join(['memcached:11211'])
if CACHE_TYPE == 'MemcachedCache':
    CACHE_MEMCACHED_SERVERS = os.getenv('CACHE_MEMCACHED_SERVERS', CACHE_MEMCACHED_SERVERS_DEFAULT).split(',')

# A mapping between the status of the resource events
# and the name of the columns of the table to display.
CLASS_EVENTS_STATUS_COLUMNS_DEFAULT = ','.join(['failure', 'Failure',
                                                # 'skipped', 'Skipped',
                                                'success', 'Success',
                                                'noop', 'Noop'])

CLASS_EVENTS_STATUS_COLUMNS_STR = os.getenv('CLASS_EVENTS_STATUS_COLUMNS', CLASS_EVENTS_STATUS_COLUMNS_DEFAULT).split(',')

# Take the Array and convert it to a tuple
CLASS_EVENTS_STATUS_COLUMNS = [(CLASS_EVENTS_STATUS_COLUMNS_STR[i].strip(),
                                CLASS_EVENTS_STATUS_COLUMNS_STR[i + 1].strip()) for i in range(0, len(CLASS_EVENTS_STATUS_COLUMNS_STR), 2)]

# Enabled a scheduler instance to trigger jobs in background.
SCHEDULER_ENABLED = coerce_bool(os.getenv('SCHEDULER_ENABLED'), False)

# Tuples are hard to express as an environment variable, so here
# the tuple can be listed as a list of items
# Examples:
#   export SCHEDULER_JOBS="id, <id>, func, <func>, trigger, <trigger>, seconds, <seconds>"
# The scheduled jobs are separated by the character ";".
SCHEDULER_JOBS_DEFAULT = ';'.join([','.join(['id', 'do_build_async_cache_1',
                                   'func', 'puppetboard.schedulers.classes:build_async_cache',
                                   'trigger', 'interval',
                                   'seconds', '300'])])

SCHEDULER_JOBS_STR = os.getenv('SCHEDULER_JOBS', SCHEDULER_JOBS_DEFAULT).split(';')

# Take the Array and convert it to a tuple
SCHEDULER_JOBS = []
for job in SCHEDULER_JOBS_STR:
    SCHEDULER_JOBS.append({job.split(',')[i]: (int(job.split(',')[i + 1]) if job.split(',')[i] == 'seconds' else job.split(',')[i + 1])
                           for i in range(0, len(job.split(',')), 2)})
