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
from puppetboard.dailychart import get_daily_reports_chart
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


CATALOGS_COLUMNS = [
    {'attr': 'certname', 'name': 'Certname', 'type': 'node'},
    {'attr': 'catalog_timestamp', 'name': 'Compile Time'},
    {'attr': 'form', 'name': 'Compare'},
]

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


@app.context_processor
def utility_processor():
    def now(format='%m/%d/%Y %H:%M:%S'):
        """returns the formated datetime"""
        return datetime.now().strftime(format)

    return dict(now=now)


@app.route('/query', methods=('GET', 'POST'), defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/query', methods=('GET', 'POST'))
def query(env):
    """Allows to execute raw, user created queries against PuppetDB. This will return
    the JSON of the response or a message telling you what went wrong why nothing was returned.

    :param env: Serves no purpose for the query data but is required for the select field in
     the environment block
    :type env: :obj:`string`
    """
    if not app.config['ENABLE_QUERY']:
        log.warning('Access to query interface disabled by administrator.')
        abort(403)

    envs = environments()
    check_env(env, envs)

    form = QueryForm(meta={
        'csrf_secret': app.config['SECRET_KEY'],
        'csrf_context': session}
    )

    if form.validate_on_submit():
        if form.endpoints.data not in ENABLED_QUERY_ENDPOINTS:
            log.warning('Access to query endpoint %s disabled by administrator.',
                        form.endpoints.data)
            abort(403)

        query = form.query.data.strip()

        # automatically wrap AST queries with [], if needed
        if form.endpoints.data != 'pql' and not query.startswith('['):
            query = f"[{query}]"

        try:
            result = get_or_abort_except_client_errors(
                puppetdb._query,
                form.endpoints.data,
                query=query)

            zero_results = (len(result) == 0)
            result = result if not zero_results else None

            if not zero_results:
                columns = result[0].keys()
            else:
                columns = []

            return render_template('query.html',
                                   form=form,
                                   zero_results=zero_results,
                                   result=result,
                                   columns=columns,
                                   envs=envs,
                                   current_env=env)

        except HTTPError as e:
            error_text = e.response.text
            return render_template('query.html',
                                   form=form,
                                   error_text=error_text,
                                   envs=envs,
                                   current_env=env)

    return render_template('query.html',
                           form=form,
                           envs=envs,
                           current_env=env)


@app.route('/metrics', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/metrics')
def metrics(env):
    """Lists all available metrics that PuppetDB is aware of.

    :param env: While this parameter serves no function purpose it is required
        for the environments template block
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    db_version = get_db_version(puppetdb)
    query_type, metric_version = metric_params(db_version)
    if metric_version == 'v1':
        mbeans = get_or_abort(puppetdb._query, 'mbean')
        metrics = list(mbeans.keys())
    elif metric_version == 'v2':
        # the list response is a dict in the format:
        # {
        #   "domain1": {
        #     "property1": {
        #      ...
        #     }
        #   },
        #   "domain2": {
        #     "property2": {
        #      ...
        #     }
        #   }
        # }
        # The MBean names are the combination of the domain and the properties
        # with a ":" in between, example:
        #   domain1:property1
        #   domain2:property2
        # reference: https://jolokia.org/reference/html/protocol.html#list
        metrics_domains = get_or_abort(puppetdb.metric)
        metrics = []
        # get all of the domains
        for domain in list(metrics_domains.keys()):
            # iterate over all of the properties in this domain
            properties = list(metrics_domains[domain].keys())
            for prop in properties:
                # combine the current domain and each property with
                # a ":" in between
                metrics.append(domain + ':' + prop)
    else:
        raise ValueError("Unknown metric version {} for database version {}"
                         .format(metric_version, db_version))

    return render_template('metrics.html',
                           metrics=sorted(metrics),
                           envs=envs,
                           current_env=env)


@app.route('/metric/<path:metric>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/metric/<path:metric>')
def metric(env, metric):
    """Lists all information about the metric of the given name.

    :param env: While this parameter serves no function purpose it is required
        for the environments template block
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    db_version = get_db_version(puppetdb)
    query_type, metric_version = metric_params(db_version)

    name = unquote(metric)
    metric = get_or_abort(puppetdb.metric, metric, version=metric_version)
    return render_template(
        'metric.html',
        name=name,
        metric=sorted(metric.items()),
        envs=envs,
        current_env=env)


@app.route('/catalogs',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'compare': None})
@app.route('/<env>/catalogs', defaults={'compare': None})
@app.route('/catalogs/compare/<compare>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalogs/compare/<compare>')
def catalogs(env, compare):
    """Lists all nodes with a compiled catalog.

    :param env: Find the nodes with this catalog_environment value
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if not app.config['ENABLE_CATALOG']:
        log.warning('Access to catalog interface disabled by administrator')
        abort(403)

    return render_template(
        'catalogs.html',
        compare=compare,
        columns=CATALOGS_COLUMNS,
        envs=envs,
        current_env=env)


@app.route('/catalogs/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'compare': None})
@app.route('/<env>/catalogs/json', defaults={'compare': None})
@app.route('/catalogs/compare/<compare>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalogs/compare/<compare>/json')
def catalogs_ajax(env, compare):
    """Server data to catalogs as JSON to Jquery datatables
    """
    draw = int(request.args.get('draw', 0))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', app.config['NORMAL_TABLE_COUNT']))
    paging_args = {'limit': length, 'offset': start}
    search_arg = request.args.get('search[value]')
    order_column = int(request.args.get('order[0][column]', 0))
    order_filter = CATALOGS_COLUMNS[order_column].get(
        'filter', CATALOGS_COLUMNS[order_column]['attr'])
    order_dir = request.args.get('order[0][dir]', 'asc')
    order_args = '[{"field": "%s", "order": "%s"}]' % (order_filter, order_dir)

    envs = environments()
    check_env(env, envs)

    query = AndOperator()
    if env != '*':
        query.add(EqualsOperator("catalog_environment", env))
    if search_arg:
        query.add(RegexOperator("certname", r"%s" % search_arg))
    query.add(NullOperator("catalog_timestamp", False))

    nodes = get_or_abort(puppetdb.nodes,
                         query=query,
                         include_total=True,
                         order_by=order_args,
                         **paging_args)

    catalog_list = []
    total = None
    for node in nodes:
        if total is None:
            total = puppetdb.total

        catalog_list.append({
            'certname': node.name,
            'catalog_timestamp': node.catalog_timestamp,
            'form': compare,
        })

    if total is None:
        total = 0

    return render_template(
        'catalogs.json.tpl',
        total=total,
        total_filtered=total,
        draw=draw,
        columns=CATALOGS_COLUMNS,
        catalogs=catalog_list,
        envs=envs,
        current_env=env)


@app.route('/catalog/<node_name>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalog/<node_name>')
def catalog_node(env, node_name):
    """Fetches from PuppetDB the compiled catalog of a given node.

    :param env: Find the catalog with this environment value
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if app.config['ENABLE_CATALOG']:
        catalog = get_or_abort(puppetdb.catalog,
                               node=node_name)
        return render_template('catalog.html',
                               catalog=catalog,
                               envs=envs,
                               current_env=env)
    else:
        log.warn('Access to catalog interface disabled by administrator')
        abort(403)


@app.route('/catalogs/compare/<compare>...<against>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalogs/compare/<compare>...<against>')
def catalog_compare(env, compare, against):
    """Compares the catalog of one node, parameter compare, with that of
       with that of another node, parameter against.

    :param env: Ensure that the 2 catalogs are in the same environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if app.config['ENABLE_CATALOG']:
        compare_cat = get_or_abort(puppetdb.catalog,
                                   node=compare)
        against_cat = get_or_abort(puppetdb.catalog,
                                   node=against)

        return render_template('catalog_compare.html',
                               compare=compare_cat,
                               against=against_cat,
                               envs=envs,
                               current_env=env)
    else:
        log.warn('Access to catalog interface disabled by administrator')
        abort(403)


@app.route('/radiator', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/radiator')
def radiator(env):
    """This view generates a simplified monitoring page
    akin to the radiator view in puppet dashboard
    """
    envs = environments()
    check_env(env, envs)

    if env == '*':
        db_version = get_db_version(puppetdb)
        query_type, metric_version = metric_params(db_version)

        query = None
        metrics = get_or_abort(
            puppetdb.metric,
            'puppetlabs.puppetdb.population:%sname=num-nodes' % query_type,
            version=metric_version)
        num_nodes = metrics['Value']
    else:
        query = AndOperator()
        metric_query = ExtractOperator()

        query.add(EqualsOperator("catalog_environment", env))
        metric_query.add_field(FunctionOperator('count'))
        metric_query.add_query(query)

        metrics = get_or_abort(
            puppetdb._query,
            'nodes',
            query=metric_query)
        num_nodes = metrics[0]['count']

    nodes = puppetdb.nodes(
        query=query,
        unreported=app.config['UNRESPONSIVE_HOURS'],
        with_status=True
    )

    stats = {
        'changed_percent': 0,
        'changed': 0,
        'failed_percent': 0,
        'failed': 0,
        'noop_percent': 0,
        'noop': 0,
        'skipped_percent': 0,
        'skipped': 0,
        'unchanged_percent': 0,
        'unchanged': 0,
        'unreported_percent': 0,
        'unreported': 0,
    }

    for node in nodes:
        if node.status == 'unreported':
            stats['unreported'] += 1
        elif node.status == 'changed':
            stats['changed'] += 1
        elif node.status == 'failed':
            stats['failed'] += 1
        elif node.status == 'noop':
            stats['noop'] += 1
        elif node.status == 'skipped':
            stats['skipped'] += 1
        else:
            stats['unchanged'] += 1

    try:
        stats['changed_percent'] = int(100 * (stats['changed'] /
                                              float(num_nodes)))
        stats['failed_percent'] = int(100 * stats['failed'] / float(num_nodes))
        stats['noop_percent'] = int(100 * stats['noop'] / float(num_nodes))
        stats['skipped_percent'] = int(100 * (stats['skipped'] /
                                              float(num_nodes)))
        stats['unchanged_percent'] = int(100 * (stats['unchanged'] /
                                                float(num_nodes)))
        stats['unreported_percent'] = int(100 * (stats['unreported'] /
                                                 float(num_nodes)))
    except ZeroDivisionError:
        stats['changed_percent'] = 0
        stats['failed_percent'] = 0
        stats['noop_percent'] = 0
        stats['skipped_percent'] = 0
        stats['unchanged_percent'] = 0
        stats['unreported_percent'] = 0

    if ('Accept' in request.headers and
            request.headers["Accept"] == 'application/json'):
        return jsonify(**stats)

    return render_template(
        'radiator.html',
        stats=stats,
        total=num_nodes
    )


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
