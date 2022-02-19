from __future__ import absolute_import
from __future__ import unicode_literals

import json
import logging
from datetime import datetime, timedelta
from itertools import tee
from json import dumps
from urllib.parse import unquote, quote_plus

import commonmark
from flask import (
    render_template, abort, url_for,
    Response, stream_with_context, request, session, jsonify
)
from pypuppetdb.QueryBuilder import (ExtractOperator, AndOperator,
                                     EqualsOperator, FunctionOperator,
                                     NullOperator, OrOperator,
                                     LessEqualOperator, RegexOperator,
                                     GreaterEqualOperator)
from requests.exceptions import HTTPError

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.forms import ENABLED_QUERY_ENDPOINTS, QueryForm
from puppetboard.utils import (get_or_abort, get_or_abort_except_client_errors, yield_or_stop,
                               get_db_version, parse_python)
from puppetboard.version import __version__


# these imports are required by Flask - DO NOT remove them although they look unused
# noinspection PyUnresolvedReferences
import puppetboard.views.index
# noinspection PyUnresolvedReferences
import puppetboard.views.nodes
# noinspection PyUnresolvedReferences
import puppetboard.views.inventory
# noinspection PyUnresolvedReferences
import puppetboard.views.facts
# noinspection PyUnresolvedReferences
import puppetboard.views.reports
# noinspection PyUnresolvedReferences
import puppetboard.views.catalogs
# noinspection PyUnresolvedReferences
import puppetboard.views.metrics
# noinspection PyUnresolvedReferences
import puppetboard.views.dailychart
# noinspection PyUnresolvedReferences
import puppetboard.views.query


app = get_app()


menu_entries = [
    ('index', 'Overview'),
    ('nodes', 'Nodes'),
    ('facts', 'Facts'),
    ('reports', 'Reports'),
    ('metrics', 'Metrics'),
    ('inventory', 'Inventory'),
    ('catalogs', 'Catalogs'),
    ('radiator', 'Radiator'),
    ('query', 'Query')
]

if not app.config.get('ENABLE_QUERY'):
    menu_entries.remove(('query', 'Query'))

if not app.config.get('ENABLE_CATALOG'):
    menu_entries.remove(('catalogs', 'Catalogs'))


app.jinja_env.globals.update(menu_entries=menu_entries)


@app.template_global()
def version():
    return __version__


@app.context_processor
def utility_processor():
    def now(format='%m/%d/%Y %H:%M:%S'):
        """returns the formated datetime"""
        return datetime.now().strftime(format)

    return dict(now=now)


@app.route('/offline/<path:filename>')
def offline_static(filename):
    mimetype = 'text/html'
    if filename.endswith('.css'):
        mimetype = 'text/css'
    elif filename.endswith('.js'):
        mimetype = 'text/javascript'

    return Response(response=render_template('static/%s' % filename),
                    status=200, mimetype=mimetype)


@app.route('/status')
def health_status():
    return 'OK'
