import logging
from datetime import datetime

from flask import (
    render_template, abort, Response, request, jsonify
)
from pypuppetdb.QueryBuilder import (AndOperator,
                                     EqualsOperator)

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.dailychart import get_daily_reports_chart
from puppetboard.reports import REPORTS_COLUMNS
from puppetboard.utils import (get_or_abort)
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


@app.route('/node/<node_name>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/node/<node_name>')
def node(env, node_name):
    """Display a dashboard for a node showing as much data as we have on that
    node. This includes facts and reports but not Resources as that is too
    heavy to do within a single request.

    :param env: Ensure that the node, facts and reports are in this environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    query = AndOperator()

    if env != '*':
        query.add(EqualsOperator("environment", env))

    query.add(EqualsOperator("certname", node_name))

    node = get_or_abort(puppetdb.node, node_name)

    return render_template(
        'node.html',
        node=node,
        envs=envs,
        current_env=env,
        columns=REPORTS_COLUMNS[:2])


@app.route('/daily_reports_chart.json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/daily_reports_chart.json')
def daily_reports_chart(env):
    """Return JSON data to generate a bar chart of daily runs.

    If certname is passed as GET argument, the data will target that
    node only.
    """
    certname = request.args.get('certname')
    result = get_or_abort(
        get_daily_reports_chart,
        db=puppetdb,
        env=env,
        days_number=app.config['DAILY_REPORTS_CHART_DAYS'],
        certname=certname,
    )
    return jsonify(result=result)


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
