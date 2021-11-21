import logging
from datetime import datetime

from flask import (
    render_template, abort, Response
)

from puppetboard.core import get_app, get_puppetdb
from puppetboard.version import __version__

app = get_app()

numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)
logging.basicConfig(level=numeric_level)
log = logging.getLogger(__name__)

puppetdb = get_puppetdb()

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


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


def check_env(env, envs):
    if env != '*' and env not in envs:
        abort(404)


def metric_params(db_version):
    query_type = ''

    # Puppet Server is enforcing new metrics API (v2)
    # starting with versions 6.9.1, 5.3.12, and 5.2.13
    if (db_version > (6, 9, 0) or
            (db_version > (5, 3, 11) and db_version < (6, 0, 0)) or
            (db_version > (5, 2, 12) and db_version < (5, 3, 10))):
        metric_version = 'v2'
    else:
        metric_version = 'v1'

    # Puppet DB version changed the query format from 3.2.0
    # to 4.0 when querying mbeans
    if db_version < (4, 0, 0):
        query_type = 'type=default,'

    return query_type, metric_version


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


from puppetboard.views.index import index
from puppetboard.views.nodes import nodes, node
from puppetboard.views.facts import facts, fact, fact_ajax
from puppetboard.views.reports import reports, reports_ajax, report
from puppetboard.views.inventory import inventory, inventory_ajax, inventory_facts
from puppetboard.views.radiator import radiator
from puppetboard.views.query import query
from puppetboard.views.catalogs import catalog_node, catalogs_ajax
from puppetboard.views.dailychart import daily_reports_chart
from puppetboard.views.metrics import metrics, metric
