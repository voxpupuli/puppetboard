from __future__ import unicode_literals
from __future__ import absolute_import

import logging
import collections
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote
from datetime import datetime, timedelta
from itertools import tee

from flask import (
    Flask, render_template, abort, url_for,
    Response, stream_with_context, redirect,
    request, session, jsonify
)

from pypuppetdb import connect
from pypuppetdb.QueryBuilder import *
from pypuppetdb.utils import UTC

from puppetboard.forms import QueryForm
from puppetboard.utils import (
    get_or_abort, yield_or_stop, get_db_version,
    jsonprint, prettyprint
)
from puppetboard.dailychart import get_daily_reports_chart

import werkzeug.exceptions as ex
import CommonMark

from . import __version__

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

NODES_COLUMNS = [
    {'attr': 'catalog_timestamp', 'filter': 'catalog_timestamp',
     'name': 'Catalog', 'type': 'datetime'},
    {'attr': 'status', 'filter': 'latest_report_status',
     'name': 'Status', 'type': 'status'},
    {'attr': 'name', 'filter': 'certname',
     'name': 'Certname', 'type': 'node'},
    {'attr': 'report_timestamp', 'filter': 'report_timestamp',
     'name': 'Report', 'type': 'datetime'},
    {'attr': 'report_timestamp', 'filter': 'report_timestamp',
     'name': '', 'type': 'datetime'},
]

app = Flask(__name__)

app.config.from_object('puppetboard.default_settings')
graph_facts = app.config['GRAPH_FACTS']
app.config.from_envvar('PUPPETBOARD_SETTINGS', silent=True)
graph_facts += app.config['GRAPH_FACTS']
app.secret_key = app.config['SECRET_KEY']

app.jinja_env.filters['jsonprint'] = jsonprint
app.jinja_env.filters['prettyprint'] = prettyprint

puppetdb = connect(
    host=app.config['PUPPETDB_HOST'],
    port=app.config['PUPPETDB_PORT'],
    ssl_verify=app.config['PUPPETDB_SSL_VERIFY'],
    ssl_key=app.config['PUPPETDB_KEY'],
    ssl_cert=app.config['PUPPETDB_CERT'],
    timeout=app.config['PUPPETDB_TIMEOUT'],)

numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % app.config['LOGLEVEL'])
logging.basicConfig(level=numeric_level)
log = logging.getLogger(__name__)


@app.template_global()
def version():
    return __version__


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


def url_for_field(field, value):
    args = request.view_args.copy()
    args.update(request.args.copy())
    args[field] = value
    return url_for(request.endpoint, **args)


def environments():
    envs = get_or_abort(puppetdb.environments)
    x = []

    for env in envs:
        x.append(env['name'])

    return x


def get_reports_noop_query():
    """Compatibility function building a query string
    to select noop reports.
    Direct access fields 'noop' and 'noop_pending' are not set
    by 3.X clients on a 4.X database.
    """
    noop_event_query = EqualsOperator('status', 'noop')
    noop_subquery = SubqueryOperator('events')
    noop_subquery.add_query(noop_event_query)
    noop_extract = ExtractOperator()
    noop_extract.add_field(str('certname'))
    noop_extract.add_query(noop_subquery)
    noop_in_query = InOperator('certname')
    noop_in_query.add_query(noop_extract)

    other_event_query = NotOperator()
    other_event_query.add(EqualsOperator('status', 'noop'))
    other_subquery = SubqueryOperator('events')
    other_subquery.add_query(other_event_query)
    other_extract = ExtractOperator()
    other_extract.add_field(str('certname'))
    other_extract.add_query(other_subquery)
    other_in_query = InOperator('certname')
    other_in_query.add_query(other_extract)
    other_not_in = NotOperator()
    other_not_in.add(other_in_query)

    result = AndOperator()
    result.add([noop_in_query, other_not_in])
    return result


def get_node_unreported_time():
    return (
        datetime.datetime.utcnow() -
        timedelta(hours=app.config['UNRESPONSIVE_HOURS'])
    ).replace(microsecond=0, tzinfo=UTC())


def get_node_status_query(status_arg):
    """Return query selecting nodes matching status_arg status"""
    if status_arg in ['failed', 'changed']:
        arg_query = AndOperator()
        arg_query.add(EqualsOperator('latest_report_status', status_arg))
        arg_query.add(GreaterOperator(
            'report_timestamp', get_node_unreported_time().isoformat()))
        return arg_query
    elif status_arg in ['noop', 'unchanged']:
        arg_query = AndOperator()
        status_op = OrOperator()
        status_op.add(EqualsOperator('latest_report_status', 'unchanged'))
        status_op.add(EqualsOperator('latest_report_status', 'noop'))
        arg_query.add(status_op)
        arg_query.add(GreaterOperator(
            'report_timestamp', get_node_unreported_time().isoformat()))
        return arg_query
    elif status_arg == 'unreported':
        arg_query = OrOperator()
        arg_query.add(NullOperator('report_timestamp', True))
        arg_query.add(LessEqualOperator(
            'report_timestamp', get_node_unreported_time().isoformat()))
        return arg_query
    else:
        raise Exception("Status %s is unknown" % status_arg)


def get_count(endpoint, query):
    c_query = ExtractOperator()
    c_query.add_field(FunctionOperator('count'))
    if query:
        c_query.add_query(query)
    res = get_or_abort(
        puppetdb._query, endpoint,
        query=c_query)
    return res[0]['count']


def get_node_env_query(env, *args):
    query = AndOperator()
    for i in args:
        query.add(i)
    if env != '*':
        query.add(EqualsOperator('catalog_environment', env))
    elif len(query.operations) == 0:
        return None
    return query


def check_env(env, envs):
    if env != '*' and env not in envs:
        abort(404)

app.jinja_env.globals['url_for_field'] = url_for_field


@app.context_processor
def utility_processor():
    def now(format='%m/%d/%Y %H:%M:%S'):
        """returns the formated datetime"""
        return datetime.datetime.now().strftime(format)
    return dict(now=now)


@app.errorhandler(400)
def bad_request(e):
    envs = environments()
    return render_template('400.html', envs=envs), 400


@app.errorhandler(403)
def forbidden(e):
    envs = environments()
    return render_template('403.html', envs=envs), 403


@app.errorhandler(404)
def not_found(e):
    envs = environments()
    return render_template('404.html', envs=envs), 404


@app.errorhandler(412)
def precond_failed(e):
    """We're slightly abusing 412 to handle missing features
    depending on the API version."""
    envs = environments()
    return render_template('412.html', envs=envs), 412


@app.errorhandler(500)
def server_error(e):
    envs = environments()
    return render_template('500.html', envs=envs), 500


def status_count(env):
    """Method used by radiator and index.
    Return nodes count by status (with percents)
    """
    stats = {}

    # num_nodes
    stats['total'] = get_count('nodes', get_node_env_query(env))

    # per status bucket (noop handled in unchanged)
    for status_arg in ['changed', 'failed', 'unchanged', 'unreported']:
        arg_query = get_node_status_query(status_arg)
        if status_arg == 'unchanged':
            res = puppetdb.nodes(query=arg_query)
            unchanged = 0
            noop = 0
            for node in res:
                if node.status == 'unchanged':
                    unchanged += 1
                else:
                    noop += 1
            stats['unchanged'] = unchanged
            stats['noop'] = noop
        else:
            stats[status_arg] = get_count(
                'nodes', get_node_env_query(env, arg_query))
        try:
            stats["%s_percent" % status_arg] = int(
                100 * stats[status_arg] / float(stats['total']))
        except ZeroDivisionError:
            stats["%s_percent" % status_arg] = 0

    return stats


@app.route('/radiator', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/radiator')
def radiator(env):
    """This view generates a simplified monitoring page
    akin to the radiator view in puppet dashboard
    """
    envs = environments()
    check_env(env, envs)

    stats = status_count(env)

    if ('Accept' in request.headers and
            request.headers["Accept"] == 'application/json'):
        return jsonify(**stats)

    return render_template(
        'radiator.html',
        stats=stats,
    )


@app.route('/', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/')
def index(env):
    """This view generates the index page and displays a set of metrics and
    latest reports on nodes fetched from PuppetDB.

    :param env: Search for nodes in this (Catalog and Fact) environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    stats = status_count(env)
    if stats['total'] < 1000:
        stats['num_resources'] = get_count(
            'resources', EqualsOperator("environment", env))

        # average resource / node
        try:
            stats['avg_resources_node'] = "{0:10.0f}".format(
                (stats['num_resources'] / stats['total']))
        except ZeroDivisionError:
            stats['avg_resources_node'] = 0

    else:
        prefix = 'puppetlabs.puppetdb.population'
        query_type = ''

        # Puppet DB version changed the query format from 3.2.0
        # to 4.0 when querying mbeans
        if get_db_version(puppetdb) < (4, 0, 0):
            query_type = 'type=default,'

        stats['num_resources'] = get_or_abort(
            puppetdb.metric, "{0}{1}".format(
                prefix, ':%sname=num-resources' % query_type))['Value']
        stats['avg_resources_node'] = int(get_or_abort(
            puppetdb.metric, "{0}{1}".format(
                prefix,
                ':%sname=avg-resources-per-node' % query_type))['Value'])

    paging_args = {'limit': app.config['NORMAL_TABLE_COUNT'], 'offset': 0}
    order_arg = '[{"field": "catalog_timestamp", "order": "desc"}]'
    nodes = get_or_abort(puppetdb.nodes,
                         query=get_node_env_query(env),
                         unreported=app.config['UNRESPONSIVE_HOURS'],
                         with_status=True,
                         order_by=order_arg,
                         **paging_args)

    return render_template(
        'index.html',
        nodes=nodes,
        stats=stats,
        envs=envs,
        current_env=env
    )


@app.route('/nodes',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'status': None})
@app.route('/<env>/nodes', defaults={'status': None})
@app.route('/nodes/<status>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/nodes/<status>')
def nodes(env, status):
    """Display all (active) nodes from PuppetDB (with Jquery datatables)

    :param env: Search for nodes in this (Catalog and Fact) environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    return render_template(
        'nodes.html',
        envs=envs,
        current_env=env,
        status_pick=status,
        columns=NODES_COLUMNS)


@app.route('/nodes/json', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/nodes/json')
def nodes_ajax(env):
    """Query and return JSON data for nodes pages

    :param env: Search for nodes in this (Catalog and Fact) environment
    :type env: :obj:`string`
    """
    draw = int(request.args.get('draw', 0))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', app.config['NORMAL_TABLE_COUNT']))
    paging_args = {'limit': length, 'offset': start}
    search_arg = request.args.get('search[value]')
    order_column = int(request.args.get('order[0][column]', 0))
    order_filter = NODES_COLUMNS[order_column].get(
        'filter', NODES_COLUMNS[order_column]['attr'])
    order_dir = request.args.get('order[0][dir]', 'desc')
    order_args = '[{"field": "%s", "order": "%s"}]' % (order_filter, order_dir)
    status_args = request.args.get('columns[1][search][value]', '').split('|')

    envs = environments()
    check_env(env, envs)
    query = AndOperator()

    if env != '*':
        query.add(EqualsOperator("catalog_environment", env))

    if search_arg:
        search_query = OrOperator()
        search_query.add(RegexOperator("certname", r"%s" % search_arg))
        query.add(search_query)

    status_query = OrOperator()
    for status_arg in status_args:
        if status_arg not in ['', '*', 'none']:
            arg_query = get_node_status_query(status_arg)
            if arg_query:
                status_query.add(arg_query)

    if len(status_query.operations) == 0:
        if len(query.operations) == 0:
            query = None
    else:
        query.add(status_query)

    if status_args[0] != 'none':
        nodes = get_or_abort(
            puppetdb.nodes,
            query=query,
            order_by=order_args,
            with_status=True,
            unreported=app.config['UNRESPONSIVE_HOURS'],
            include_total=True,
            **paging_args)
        nodes, nodes_events = tee(nodes)
        for r in nodes_events:
            break
        total = puppetdb.total
        if total is None:
            total = 0
    else:
        nodes = []
        total = 0

    return render_template(
        'nodes.json.tpl',
        draw=draw,
        total=total,
        total_filtered=total,
        nodes=nodes,
        envs=envs,
        current_env=env,
        columns=NODES_COLUMNS)


def inventory_facts():
    # a list of facts descriptions to go in table header
    headers = []
    # a list of inventory fact names
    fact_names = []

    # load the list of items/facts we want in our inventory
    try:
        inv_facts = app.config['INVENTORY_FACTS']
    except KeyError:
        inv_facts = [('Hostname', 'fqdn'),
                     ('IP Address', 'ipaddress'),
                     ('OS', 'lsbdistdescription'),
                     ('Architecture', 'hardwaremodel'),
                     ('Kernel Version', 'kernelrelease')]

    # generate a list of descriptions and a list of fact names
    # from the list of tuples inv_facts.
    for desc, name in inv_facts:
        headers.append(desc)
        fact_names.append(name)

    return headers, fact_names


@app.route('/inventory', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/inventory')
def inventory(env):
    """Fetch all (active) nodes from PuppetDB and stream a table displaying
    those nodes along with a set of facts about them.

    :param env: Search for facts in this environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    headers, fact_names = inventory_facts()

    return render_template(
        'inventory.html',
        envs=envs,
        current_env=env,
        fact_headers=headers)


@app.route('/inventory/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/inventory/json')
def inventory_ajax(env):
    """Backend endpoint for inventory table"""
    draw = int(request.args.get('draw', 0))

    envs = environments()
    check_env(env, envs)
    headers, fact_names = inventory_facts()

    query = AndOperator()
    fact_query = OrOperator()
    fact_query.add([EqualsOperator("name", name) for name in fact_names])
    query.add(fact_query)

    if env != '*':
        query.add(EqualsOperator("environment", env))

    facts = puppetdb.facts(query=query)

    fact_data = {}
    for fact in facts:
        if fact.node not in fact_data:
            fact_data[fact.node] = {}
        fact_data[fact.node][fact.name] = fact.value

    total = len(fact_data)

    return render_template(
        'inventory.json.tpl',
        draw=draw,
        total=total,
        total_filtered=total,
        fact_data=fact_data,
        columns=fact_names)


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


@app.route('/reports',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'node_name': None})
@app.route('/<env>/reports', defaults={'node_name': None})
@app.route('/reports/<node_name>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/reports/<node_name>')
def reports(env, node_name):
    """Query and Return JSON data to reports Jquery datatable

    :param env: Search for all reports in this environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    return render_template(
        'reports.html',
        envs=envs,
        current_env=env,
        node_name=node_name,
        columns=REPORTS_COLUMNS)


@app.route('/reports/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'node_name': None})
@app.route('/<env>/reports/json', defaults={'node_name': None})
@app.route('/reports/<node_name>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/reports/<node_name>/json')
def reports_ajax(env, node_name):
    """Query and Return JSON data to reports Jquery datatable

    :param env: Search for all reports in this environment
    :type env: :obj:`string`
    """
    draw = int(request.args.get('draw', 0))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', app.config['NORMAL_TABLE_COUNT']))
    paging_args = {'limit': length, 'offset': start}
    search_arg = request.args.get('search[value]')
    order_column = int(request.args.get('order[0][column]', 0))
    order_filter = REPORTS_COLUMNS[order_column].get(
        'filter', REPORTS_COLUMNS[order_column]['attr'])
    order_dir = request.args.get('order[0][dir]', 'desc')
    order_args = '[{"field": "%s", "order": "%s"}]' % (order_filter, order_dir)
    status_args = request.args.get('columns[1][search][value]', '').split('|')
    max_col = len(REPORTS_COLUMNS)
    for i in range(len(REPORTS_COLUMNS)):
        if request.args.get("columns[%s][data]" % i, None):
            max_col = i + 1

    envs = environments()
    check_env(env, envs)
    reports_query = AndOperator()

    if env != '*':
        reports_query.add(EqualsOperator("environment", env))

    if node_name:
        reports_query.add(EqualsOperator("certname", node_name))

    if search_arg:
        search_query = OrOperator()
        search_query.add(RegexOperator("certname", r"%s" % search_arg))
        search_query.add(RegexOperator("puppet_version", r"%s" % search_arg))
        search_query.add(RegexOperator(
            "configuration_version", r"%s" % search_arg))
        reports_query.add(search_query)

    status_query = OrOperator()
    for status_arg in status_args:
        if status_arg in ['failed', 'changed', 'unchanged']:
            arg_query = AndOperator()
            arg_query.add(EqualsOperator('status', status_arg))
            if status_arg == 'unchanged':
                noop_query = NotOperator()
                noop_query.add(get_reports_noop_query())
                arg_query.add(noop_query)
            status_query.add(arg_query)
        elif status_arg == 'noop':
            status_query.add(get_reports_noop_query())

    if len(status_query.operations) == 0:
        if len(reports_query.operations) == 0:
            reports_query = None
    else:
        reports_query.add(status_query)

    if status_args[0] != 'none':
        reports = get_or_abort(
            puppetdb.reports,
            query=reports_query,
            order_by=order_args,
            include_total=True,
            **paging_args)
        reports, reports_total = tee(reports)
        for r in reports_total:
            break
        total = puppetdb.total
        if total is None:
            total = 0
    else:
        reports = []
        total = 0

    return render_template(
        'reports.json.tpl',
        draw=draw,
        total=total,
        total_filtered=total,
        reports=reports,
        envs=envs,
        current_env=env,
        columns=REPORTS_COLUMNS[:max_col])


@app.route('/report/<node_name>/<report_id>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/report/<node_name>/<report_id>')
def report(env, node_name, report_id):
    """Displays a single report including all the events associated with that
    report and their status.

    The report_id may be the puppetdb's report hash or the
    configuration_version. This allows for better integration
    into puppet-hipchat.

    :param env: Search for reports in this environment
    :type env: :obj:`string`
    :param node_name: Find the reports whose certname match this value
    :type node_name: :obj:`string`
    :param report_id: The hash or the configuration_version of the desired
        report
    :type report_id: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    query = AndOperator()
    report_id_query = OrOperator()

    report_id_query.add(EqualsOperator("hash", report_id))
    report_id_query.add(EqualsOperator("configuration_version", report_id))

    if env != '*':
        query.add(EqualsOperator("environment", env))

    query.add(EqualsOperator("certname", node_name))
    query.add(report_id_query)

    reports = puppetdb.reports(query=query)

    try:
        report = next(reports)
    except StopIteration:
        abort(404)

    report.version = CommonMark.commonmark(report.version)

    return render_template(
        'report.html',
        report=report,
        events=yield_or_stop(report.events()),
        logs=report.logs,
        metrics=report.metrics,
        envs=envs,
        current_env=env)


@app.route('/facts', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/facts')
def facts(env):
    """Displays an alphabetical list of all facts currently known to
    PuppetDB.

    :param env: Serves no purpose for this function, only for consistency's
        sake
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    facts = []
    order_by = '[{"field": "name", "order": "asc"}]'
    facts = get_or_abort(puppetdb.fact_names)

    facts_columns = [[]]
    letter = None
    letter_list = None
    break_size = (len(facts) / 4) + 1
    next_break = break_size
    count = 0
    for fact in facts:
        count += 1

        if letter != fact[0].upper() or not letter:
            if count > next_break:
                # Create a new column
                facts_columns.append([])
                next_break += break_size
            if letter_list:
                facts_columns[-1].append(letter_list)
            # Reset
            letter = fact[0].upper()
            letter_list = []

        letter_list.append(fact)
    facts_columns[-1].append(letter_list)

    return render_template('facts.html',
                           facts_columns=facts_columns,
                           envs=envs,
                           current_env=env)


@app.route('/fact/<fact>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'value': None})
@app.route('/<env>/fact/<fact>', defaults={'value': None})
@app.route('/fact/<fact>/<value>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/fact/<fact>/<value>')
def fact(env, fact, value):
    """Fetches the specific fact(/value) from PuppetDB and displays per
    node for which this fact is known.

    :param env: Searches for facts in this environment
    :type env: :obj:`string`
    :param fact: Find all facts with this name
    :type fact: :obj:`string`
    :param value: Find all facts with this value
    :type value: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    render_graph = False
    if fact in graph_facts and not value:
        render_graph = True

    return render_template(
        'fact.html',
        fact=fact,
        value=value,
        render_graph=render_graph,
        envs=envs,
        current_env=env)


@app.route('/fact/<fact>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'node': None, 'value': None})
@app.route('/<env>/fact/<fact>/json', defaults={'node': None, 'value': None})
@app.route('/fact/<fact>/<value>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'node': None})
@app.route('/<env>/fact/<fact>/<value>/json', defaults={'node': None})
@app.route('/node/<node>/facts/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'fact': None, 'value': None})
@app.route('/<env>/node/<node>/facts/json',
           defaults={'fact': None, 'value': None})
def fact_ajax(env, node, fact, value):
    """Fetches the specific facts matching (node/fact/value) from PuppetDB and
    return a JSON table

    :param env: Searches for facts in this environment
    :type env: :obj:`string`
    :param node: Find all facts for this node
    :type node: :obj:`string`
    :param fact: Find all facts with this name
    :type fact: :obj:`string`
    :param value: Filter facts whose value is equal to this
    :type value: :obj:`string`
    """
    draw = int(request.args.get('draw', 0))

    envs = environments()
    check_env(env, envs)

    render_graph = False
    if fact in graph_facts and not value and not node:
        render_graph = True

    query = AndOperator()
    if node:
        query.add(EqualsOperator("certname", node))

    if env != '*':
        query.add(EqualsOperator("environment", env))

    if len(query.operations) == 0:
        query = None

    # Generator needs to be converted (graph / total)
    facts = [f for f in get_or_abort(
        puppetdb.facts,
        name=fact,
        value=value,
        query=query)]

    total = len(facts)

    counts = {}
    json = {
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': []}

    for fact_h in facts:
        line = []
        if not fact:
            line.append(fact_h.name)
        if not node:
            line.append('<a href="{0}">{1}</a>'.format(
                url_for('node', env=env, node_name=fact_h.node),
                fact_h.node))
        if not value:
            line.append('<a href="{0}">{1}</a>'.format(
                url_for(
                    'fact', env=env, fact=fact_h.name, value=fact_h.value),
                fact_h.value))

        json['data'].append(line)

        if render_graph:
            if fact_h.value not in counts:
                counts[fact_h.value] = 0
            counts[fact_h.value] += 1

    if render_graph:
        json['chart'] = [
            {"label": "{0}".format(k).replace('\n', ' '),
             "value": counts[k]}
            for k in sorted(counts, key=lambda k: counts[k], reverse=True)]

    return jsonify(json)


@app.route('/query', methods=('GET', 'POST'),
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/query', methods=('GET', 'POST'))
def query(env):
    """Allows to execute raw, user created querries against PuppetDB. This is
    currently highly experimental and explodes in interesting ways since none
    of the possible exceptions are being handled just yet. This will return
    the JSON of the response or a message telling you what whent wrong /
    why nothing was returned.

    :param env: Serves no purpose for the query data but is required for the
        select field in the environment block
    :type env: :obj:`string`
    """
    if app.config['ENABLE_QUERY']:
        envs = environments()
        check_env(env, envs)

        form = QueryForm(meta={
            'csrf_secret': app.config['SECRET_KEY'],
            'csrf_context': session})
        if form.validate_on_submit():
            if form.endpoints.data == 'pql':
                query = form.query.data
            elif form.query.data[0] == '[':
                query = form.query.data
            else:
                query = '[{0}]'.format(form.query.data)
            result = get_or_abort(
                puppetdb._query,
                form.endpoints.data,
                query=query)
            return render_template('query.html',
                                   form=form,
                                   result=result,
                                   envs=envs,
                                   current_env=env)
        return render_template('query.html',
                               form=form,
                               envs=envs,
                               current_env=env)
    else:
        log.warn('Access to query interface disabled by administrator..')
        abort(403)


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

    metrics = get_or_abort(puppetdb._query, 'mbean')
    return render_template('metrics.html',
                           metrics=sorted(metrics.keys()),
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

    name = unquote(metric)
    metric = get_or_abort(puppetdb.metric, metric)
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
        log.warn('Access to catalog interface disabled by administrator')
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
