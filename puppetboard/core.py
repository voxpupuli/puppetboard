import logging

from flask import Flask
from pypuppetdb import connect

from puppetboard.utils import (get_or_abort, jsonprint,
                               url_for_field, url_static_offline, quote_columns_data)


REPORTS_COLUMNS = [
    {'attr': 'end', 'filter': 'end_time',
     'name': 'End time', 'type': 'datetime'},
    {'attr': 'status', 'name': 'Status', 'type': 'status'},
    {'attr': 'certname', 'name': 'Certname', 'type': 'node'},
    {'attr': 'version', 'filter': 'configuration_version',
     'name': 'Configuration version'},
    {'attr': 'agent_version', 'filter': 'puppet_version',
     'name': 'Agent version'},
]

CATALOGS_COLUMNS = [
    {'attr': 'certname', 'name': 'Certname', 'type': 'node'},
    {'attr': 'catalog_timestamp', 'name': 'Compile Time'},
    {'attr': 'form', 'name': 'Compare'},
]

APP = None
PUPPETDB = None


def get_app():
    global APP

    if APP is None:
        app = Flask(__name__)
        app.config.from_object('puppetboard.default_settings')
        app.config.from_envvar('PUPPETBOARD_SETTINGS', silent=True)
        app.secret_key = app.config['SECRET_KEY']

        logging.basicConfig(level=app.config['LOGLEVEL'].upper())

        app.jinja_env.filters['jsonprint'] = jsonprint
        app.jinja_env.globals['url_for_field'] = url_for_field
        app.jinja_env.globals['url_static_offline'] = url_static_offline
        app.jinja_env.globals['quote_columns_data'] = quote_columns_data
        APP = app

    return APP


def get_puppetdb():
    global PUPPETDB

    if PUPPETDB is None:
        app = get_app()
        puppetdb = connect(host=app.config['PUPPETDB_HOST'],
                           port=app.config['PUPPETDB_PORT'],
                           ssl_verify=app.config['PUPPETDB_SSL_VERIFY'],
                           ssl_key=app.config['PUPPETDB_KEY'],
                           ssl_cert=app.config['PUPPETDB_CERT'],
                           timeout=app.config['PUPPETDB_TIMEOUT'],
                           protocol=app.config['PUPPETDB_PROTO'], )
        PUPPETDB = puppetdb

    return PUPPETDB


def environments():
    puppetdb = get_puppetdb()
    envs = get_or_abort(puppetdb.environments)
    x = []

    for env in envs:
        x.append(env['name'])

    return x


# as documented in
# https://flask.palletsprojects.com/en/2.0.x/patterns/streaming/#streaming-from-templates
def stream_template(template_name, **context):
    app = get_app()
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv
