from __future__ import absolute_import
from __future__ import unicode_literals


# load python 3, fallback to python 2 if it fails
try:
    from urllib.parse import unquote, unquote_plus, quote_plus
except ImportError:
    from urllib import unquote, unquote_plus, quote_plus  # type: ignore
from datetime import datetime, timedelta
from itertools import tee
import sys
from flask import (
    render_template, abort, url_for,
    Response, stream_with_context, request, session, jsonify
)

import logging

from pypuppetdb.QueryBuilder import (ExtractOperator, AndOperator,
                                     EqualsOperator, FunctionOperator,
                                     NullOperator, OrOperator,
                                     LessEqualOperator, RegexOperator)

from puppetboard.forms import ENABLED_QUERY_ENDPOINTS, QueryForm
from puppetboard.utils import (get_or_abort, yield_or_stop,
                               get_db_version)
from puppetboard.dailychart import get_daily_reports_chart

try:
    import CommonMark as commonmark
except ImportError:
    import commonmark

from puppetboard.core import get_app, get_puppetdb, environments

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

app = get_app()
graph_facts = app.config['GRAPH_FACTS']
numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)

logging.basicConfig(level=numeric_level)
log = logging.getLogger(__name__)

puppetdb = get_puppetdb()


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

    # PuppetDB moved to a new metrics API (v2) in 6.9.1
    if db_version > (6, 9, 0):
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
        db_version = get_db_version(puppetdb)
        query_type, metric_version = metric_params(db_version)

        num_nodes = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix, ':%sname=num-nodes' % query_type),
            version=metric_version)
        num_resources = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix, ':%sname=num-resources' % query_type),
            version=metric_version)
        avg_resources_node = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix,
                            ':%sname=avg-resources-per-node' % query_type),
            version=metric_version)
        metrics['num_nodes'] = num_nodes['Value']
        metrics['num_resources'] = num_resources['Value']
        try:
            # Compute our own average because avg_resources_node['Value']
            # returns a string of the format "num_resources/num_nodes"
            # example: "1234/9" instead of doing the division itself.
            metrics['avg_resources_node'] = "{0:10.0f}".format(
                (num_resources['Value'] / num_nodes['Value']))
        except ZeroDivisionError:
            metrics['avg_resources_node'] = 0
    else:
        query = AndOperator()
        query.add(EqualsOperator('catalog_environment', env))

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
                         with_status=True,
                         with_event_numbers=app.config['WITH_EVENT_NUMBERS'])

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

    if status_arg in ['failed', 'changed', 'unchanged']:
        query.add(EqualsOperator('latest_report_status', status_arg))
    elif status_arg == 'unreported':
        unreported = datetime.utcnow()
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
        with_status=True,
        with_event_numbers=app.config['WITH_EVENT_NUMBERS'])
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

    # Convert metrics to relational dict
    metrics = {}
    for report in reports_events:
        if total is None:
            total = puppetdb.total

        metrics[report.hash_] = {}
        for m in report.metrics:
            if m['category'] not in metrics[report.hash_]:
                metrics[report.hash_][m['category']] = {}
            metrics[report.hash_][m['category']][m['name']] = m['value']

    if total is None:
        total = 0

    return render_template(
        'reports.json.tpl',
        draw=draw,
        total=total,
        total_filtered=total,
        reports=reports,
        metrics=metrics,
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

    report.version = commonmark.commonmark(report.version)

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

    value_safe = value
    if value is not None:
        value_safe = unquote_plus(value)

    return render_template(
        'fact.html',
        fact=fact,
        value=value,
        value_safe=value_safe,
        render_graph=render_graph,
        envs=envs,
        current_env=env)


@app.route('/fact/<fact>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'node': None, 'value': None})
@app.route('/<env>/fact/<fact>/json', defaults={'node': None, 'value': None})
@app.route('/fact/<fact>/<value>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'node': None})
@app.route('/fact/<fact>/<path:value>/json',
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
    try:
        value = int(value)
    except ValueError:
        if value is not None and query is not None:
            query.add(EqualsOperator('value', unquote_plus(value)))
    except TypeError:
        pass

    facts = [f for f in get_or_abort(
        puppetdb.facts,
        name=fact,
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
            fact_value = fact_h.value
            if isinstance(fact_value, str):
                fact_value = quote_plus(fact_h.value)

            line.append('<a href="{0}">{1}</a>'.format(
                url_for(
                    'fact', env=env, fact=fact_h.name, value=fact_value),
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
    if not app.config['ENABLE_QUERY']:
        log.warn('Access to query interface disabled by administrator.')
        abort(403)

    envs = environments()
    check_env(env, envs)

    form = QueryForm(meta={
        'csrf_secret': app.config['SECRET_KEY'],
        'csrf_context': session})
    if form.validate_on_submit():
        if form.endpoints.data not in ENABLED_QUERY_ENDPOINTS:
            log.warn('Access to query endpoint %s disabled by administrator.',
                     form.endpoints.data)
            abort(403)

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
                         .format(metric_version, database_version))

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
