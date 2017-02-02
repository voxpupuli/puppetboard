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
from pypuppetdb.errors import EmptyResponseError
from pypuppetdb.QueryBuilder import *

from puppetboard.forms import (CatalogForm, QueryForm)
from puppetboard.utils import (
    get_or_abort, yield_or_stop, get_db_version,
    jsonprint, prettyprint
)
from puppetboard.dailychart import get_daily_reports_chart

import werkzeug.exceptions as ex

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


#
# 204 doesn't have a mapping in werkzeug, we need to define a custom
# class and then set it to the mappings.
#
class NoContent(ex.HTTPException):
    code = 204
    description = '<p>No content</p'

abort.mapping[204] = NoContent

try:
    @app.errorhandler(204)
    def no_content(e):
        return '', 204
except KeyError:
    @app.errorhandler(EmptyResponseError)
    def no_content(e):
        return '', 204


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


@app.route('/', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/')
def index(env):
    """This view generates the index page and displays a set of metrics and
    latest reports on nodes fetched from PuppetDB.

    :param env: Search for nodes in this (Catalog and Fact) environment
    :type env: :obj:`string`
    """
    envs = environments()
    metrics = {
        'num_nodes': 0,
        'num_resources': 0,
        'avg_resources_node': 0}
    check_env(env, envs)

    if env == '*':
        query = app.config['OVERVIEW_FILTER']

        prefix = 'puppetlabs.puppetdb.population'
        query_type = ''

        # Puppet DB version changed the query format from 3.2.0
        # to 4.0 when querying mbeans
        if get_db_version(puppetdb) < (4, 0, 0):
            query_type = 'type=default,'

        num_nodes = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix, ':%sname=num-nodes' % query_type))
        num_resources = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix, ':%sname=num-resources' % query_type))
        avg_resources_node = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix,
                            ':%sname=avg-resources-per-node' % query_type))
        metrics['num_nodes'] = num_nodes['Value']
        metrics['num_resources'] = num_resources['Value']
        metrics['avg_resources_node'] = "{0:10.0f}".format(
            avg_resources_node['Value'])
    else:
        query = AndOperator()
        query.add(EqualsOperator('catalog_environment', env))
        query.add(EqualsOperator('facts_environment', env))

        num_nodes_query = ExtractOperator()
        num_nodes_query.add_field(FunctionOperator('count'))
        num_nodes_query.add_query(query)

        if app.config['OVERVIEW_FILTER'] is not None:
            query.add(app.config['OVERVIEW_FILTER'])

        num_resources_query = ExtractOperator()
        num_resources_query.add_field(FunctionOperator('count'))
        num_resources_query.add_query(EqualsOperator("environment", env))

        num_nodes = get_or_abort(
            puppetdb._query,
            'nodes',
            query=num_nodes_query)
        num_resources = get_or_abort(
            puppetdb._query,
            'resources',
            query=num_resources_query)
        metrics['num_nodes'] = num_nodes[0]['count']
        metrics['num_resources'] = num_resources[0]['count']
        try:
            metrics['avg_resources_node'] = "{0:10.0f}".format(
                (num_resources[0]['count'] / num_nodes[0]['count']))
        except ZeroDivisionError:
            metrics['avg_resources_node'] = 0

    nodes = get_or_abort(puppetdb.nodes,
                         query=query,
                         unreported=app.config['UNRESPONSIVE_HOURS'],
                         with_status=True)

    nodes_overview = []
    stats = {
        'changed': 0,
        'unchanged': 0,
        'failed': 0,
        'unreported': 0,
        'noop': 0
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
        else:
            stats['unchanged'] += 1

        if node.status != 'unchanged':
            nodes_overview.append(node)

    return render_template(
        'index.html',
        metrics=metrics,
        nodes=nodes_overview,
        stats=stats,
        envs=envs,
        current_env=env
    )


@app.route('/nodes', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/nodes')
def nodes(env):
    """Fetch all (active) nodes from PuppetDB and stream a table displaying
    those nodes.

    Downside of the streaming aproach is that since we've already sent our
    headers we can't abort the request if we detect an error. Because of this
    we'll end up with an empty table instead because of how yield_or_stop
    works. Once pagination is in place we can change this but we'll need to
    provide a search feature instead.

    :param env: Search for nodes in this (Catalog and Fact) environment
    :type env: :obj:`string`
    """
    envs = environments()
    status_arg = request.args.get('status', '')
    check_env(env, envs)

    query = AndOperator()

    if env != '*':
        query.add(EqualsOperator("catalog_environment", env))
        query.add(EqualsOperator("facts_environment", env))

    if status_arg in ['failed', 'changed', 'unchanged']:
        query.add(EqualsOperator('latest_report_status', status_arg))
    elif status_arg == 'unreported':
        unreported = datetime.datetime.utcnow()
        unreported = (unreported -
                      timedelta(hours=app.config['UNRESPONSIVE_HOURS']))
        unreported = unreported.replace(microsecond=0).isoformat()

        unrep_query = OrOperator()
        unrep_query.add(NullOperator('report_timestamp', True))
        unrep_query.add(LessEqualOperator('report_timestamp', unreported))

        query.add(unrep_query)

    if len(query.operations) == 0:
        query = None

    nodelist = puppetdb.nodes(
        query=query,
        unreported=app.config['UNRESPONSIVE_HOURS'],
        with_status=True)
    nodes = []
    for node in yield_or_stop(nodelist):
        if status_arg:
            if node.status == status_arg:
                nodes.append(node)
        else:
            nodes.append(node)
    return Response(stream_with_context(
        stream_template('nodes.html',
                        nodes=nodes,
                        envs=envs,
                        current_env=env)))


@app.route('/inventory', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/inventory')
def inventory(env):
    """Fetch all (active) nodes from PuppetDB and stream a table displaying
    those nodes along with a set of facts about them.

    Downside of the streaming aproach is that since we've already sent our
    headers we can't abort the request if we detect an error. Because of this
    we'll end up with an empty table instead because of how yield_or_stop
    works. Once pagination is in place we can change this but we'll need to
    provide a search feature instead.

    :param env: Search for facts in this environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    headers = []        # a list of fact descriptions to go
    # in the table header
    fact_names = []     # a list of inventory fact names
    fact_data = {}      # a multidimensional dict for node and
    # fact data

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

    query = AndOperator()
    fact_query = OrOperator()
    fact_query.add([EqualsOperator("name", name) for name in fact_names])

    if env != '*':
        query.add(EqualsOperator("environment", env))

    query.add(fact_query)

    # get all the facts from PuppetDB
    facts = puppetdb.facts(query=query)

    for fact in facts:
        if fact.node not in fact_data:
            fact_data[fact.node] = {}

        fact_data[fact.node][fact.name] = fact.value

    return Response(stream_with_context(
        stream_template(
            'inventory.html',
            headers=headers,
            fact_names=fact_names,
            fact_data=fact_data,
            envs=envs,
            current_env=env
        )))


@app.route('/node/<node_name>/',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/node/<node_name>/')
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
    facts = node.facts()
    return render_template(
        'node.html',
        node=node,
        facts=yield_or_stop(facts),
        envs=envs,
        current_env=env,
        columns=REPORTS_COLUMNS[:2])


@app.route('/reports/',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'node_name': None})
@app.route('/<env>/reports/', defaults={'node_name': None})
@app.route('/reports/<node_name>/',
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
    order_dir = request.args.get('order[0][dir]')
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
            arg_query.add(EqualsOperator('noop', False))
            status_query.add(arg_query)
            if status_arg == 'unchanged':
                arg_query = AndOperator()
                arg_query.add(EqualsOperator('noop', True))
                arg_query.add(EqualsOperator('noop_pending', False))
                status_query.add(arg_query)
        elif status_arg == 'noop':
            arg_query = AndOperator()
            arg_query.add(EqualsOperator('noop', True))
            arg_query.add(EqualsOperator('noop_pending', True))
            status_query.add(arg_query)

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
        reports, reports_events = tee(reports)
        total = None
    else:
        reports = []
        reports_events = []
        total = 0

    report_event_counts = {}
    # Create a map from the metrics data to what the templates
    # use to express the data.
    report_map = {
        'success': 'successes',
        'failure': 'failures',
        'skipped': 'skips',
        'noops': 'noop'
    }
    for report in reports_events:
        if total is None:
            total = puppetdb.total

        report_counts = {'successes': 0, 'failures': 0, 'skips': 0}
        for metrics in report.metrics:
            if 'name' in metrics and metrics['name'] in report_map:
                key_name = report_map[metrics['name']]
                report_counts[key_name] = metrics['value']

        report_event_counts[report.hash_] = report_counts

    if total is None:
        total = 0

    return render_template(
        'reports.json.tpl',
        draw=draw,
        total=total,
        total_filtered=total,
        reports=reports,
        report_event_counts=report_event_counts,
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

    if env == '*':
        facts = get_or_abort(puppetdb.fact_names)
    else:
        query = ExtractOperator()
        query.add_field(str('name'))
        query.add_query(EqualsOperator("environment", env))
        query.add_group_by(str("name"))

        for names in get_or_abort(puppetdb._query,
                                  'facts',
                                  query=query,
                                  order_by=order_by):
            facts.append(names['name'])

    facts_dict = collections.defaultdict(list)
    for fact in facts:
        letter = fact[0].upper()
        letter_list = facts_dict[letter]
        letter_list.append(fact)
        facts_dict[letter] = letter_list

    sorted_facts_dict = sorted(facts_dict.items())
    return render_template('facts.html',
                           facts_dict=sorted_facts_dict,
                           facts_len=(sum(map(len, facts_dict.values())) +
                                      len(facts_dict) * 5),
                           envs=envs,
                           current_env=env)


@app.route('/fact/<fact>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/fact/<fact>')
def fact(env, fact):
    """Fetches the specific fact from PuppetDB and displays its value per
    node for which this fact is known.

    :param env: Searches for facts in this environment
    :type env: :obj:`string`
    :param fact: Find all facts with this name
    :type fact: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    # we can only consume the generator once, lists can be doubly consumed
    # om nom nom
    render_graph = False
    if fact in graph_facts:
        render_graph = True

    if env == '*':
        query = None
    else:
        query = EqualsOperator("environment", env)

    localfacts = [f for f in yield_or_stop(puppetdb.facts(
        name=fact, query=query))]
    return Response(stream_with_context(stream_template(
        'fact.html',
        name=fact,
        render_graph=render_graph,
        facts=localfacts,
        envs=envs,
        current_env=env)))


@app.route('/fact/<fact>/<value>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/fact/<fact>/<value>')
def fact_value(env, fact, value):
    """On asking for fact/value get all nodes with that fact.

    :param env: Searches for facts in this environment
    :type env: :obj:`string`
    :param fact: Find all facts with this name
    :type fact: :obj:`string`
    :param value: Filter facts whose value is equal to this
    :type value: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if env == '*':
        query = None
    else:
        query = EqualsOperator("environment", env)

    facts = get_or_abort(puppetdb.facts,
                         name=fact,
                         value=value,
                         query=query)
    localfacts = [f for f in yield_or_stop(facts)]
    return render_template(
        'fact.html',
        name=fact,
        value=value,
        facts=localfacts,
        envs=envs,
        current_env=env)


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


@app.route('/catalogs', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalogs')
def catalogs(env):
    """Lists all nodes with a compiled catalog.

    :param env: Find the nodes with this catalog_environment value
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if app.config['ENABLE_CATALOG']:
        nodenames = []
        catalog_list = []
        query = AndOperator()

        if env != '*':
            query.add(EqualsOperator("catalog_environment", env))

        query.add(NullOperator("catalog_timestamp", False))

        order_by_str = '[{"field": "certname", "order": "asc"}]'
        nodes = get_or_abort(puppetdb.nodes,
                             query=query,
                             with_status=False,
                             order_by=order_by_str)
        nodes, temp = tee(nodes)

        for node in temp:
            nodenames.append(node.name)

        for node in nodes:
            table_row = {
                'name': node.name,
                'catalog_timestamp': node.catalog_timestamp
            }

            if len(nodenames) > 1:
                form = CatalogForm()

                form.compare.data = node.name
                form.against.choices = [(x, x) for x in nodenames
                                        if x != node.name]
                table_row['form'] = form
            else:
                table_row['form'] = None

            catalog_list.append(table_row)

        return render_template(
            'catalogs.html',
            nodes=catalog_list,
            envs=envs,
            current_env=env)
    else:
        log.warn('Access to catalog interface disabled by administrator')
        abort(403)


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


@app.route('/catalog/submit', methods=['POST'],
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalog/submit', methods=['POST'])
def catalog_submit(env):
    """Receives the submitted form data from the catalogs page and directs
       the users to the comparison page. Directs users back to the catalogs
       page if no form submission data is found.

    :param env: This parameter only directs the response page to the right
       environment. If this environment does not exist return the use to the
       catalogs page with the right environment.
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if app.config['ENABLE_CATALOG']:
        form = CatalogForm(request.form)

        form.against.choices = [(form.against.data, form.against.data)]
        if form.validate_on_submit():
            compare = form.compare.data
            against = form.against.data
            return redirect(
                url_for('catalog_compare',
                        env=env,
                        compare=compare,
                        against=against))
        return redirect(url_for('catalogs', env=env))
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
        query_type = ''
        if get_db_version(puppetdb) < (4, 0, 0):
            query_type = 'type=default,'
        query = None
        metrics = get_or_abort(
            puppetdb.metric,
            'puppetlabs.puppetdb.population:%sname=num-nodes' % query_type)
        num_nodes = metrics['Value']
    else:
        query = AndOperator()
        metric_query = ExtractOperator()

        query.add(EqualsOperator("catalog_environment", env))
        query.add(EqualsOperator("facts_environment", env))
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
