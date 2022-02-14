import logging

from flask import Flask
from pypuppetdb import connect

from puppetboard.utils import (get_or_abort, jsonprint,
                               url_for_field, url_static_offline, quote_columns_data)

APP = None
PUPPETDB = None


def get_app():
    global APP

    if APP is None:
        app = Flask(__name__)
        app.config.from_object('puppetboard.default_settings')
        app.config.from_envvar('PUPPETBOARD_SETTINGS', silent=True)
        app.secret_key = app.config['SECRET_KEY']

        numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % app.config['LOGLEVEL'])

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
