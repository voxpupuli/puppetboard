from __future__ import unicode_literals
from __future__ import absolute_import

import logging
import collections
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote
from datetime import datetime
from itertools import tee

from flask import (
    Flask, render_template, abort, url_for,
    Response, stream_with_context, redirect,
    request
    )

from pypuppetdb import connect

from puppetboard.forms import (CatalogForm, QueryForm)
from puppetboard.utils import (
    get_or_abort, yield_or_stop,
    jsonprint, Pagination
    )


app = Flask(__name__)

app.config.from_object('puppetboard.default_settings')
graph_facts = app.config['GRAPH_FACTS']
app.config.from_envvar('PUPPETBOARD_SETTINGS', silent=True)
graph_facts += app.config['GRAPH_FACTS']
app.secret_key = app.config['SECRET_KEY']

app.jinja_env.filters['jsonprint'] = jsonprint

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

def url_for_pagination(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

def url_for_environments(env):
    args = request.view_args.copy()
    args['env'] = env
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

app.jinja_env.globals['url_for_pagination'] = url_for_pagination
app.jinja_env.globals['url_for_environments'] = url_for_environments

@app.context_processor
def utility_processor():
    def now(format='%m/%d/%Y %H:%M:%S'):
        """returns the formated datetime"""
        return datetime.now().strftime(format)
    return dict(now=now)


@app.errorhandler(400)
def bad_request(e):
    envs = environments()
    return render_template('400.html', envs=envs), 400


@app.errorhandler(403)
def forbidden(e):
    envs = environments()
    return render_template('403.html', envs=envs), 400


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
        query = None

        prefix = 'puppetlabs.puppetdb.population'
        num_nodes = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix, ':name=num-nodes'))
        num_resources = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix, ':name=num-resources'))
        avg_resources_node = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix, ':name=avg-resources-per-node'))
        metrics['num_nodes'] = num_nodes['Value']
        metrics['num_resources'] = num_resources['Value']
        metrics['avg_resources_node'] = "{0:10.0f}".format(
            avg_resources_node['Value'])
    else:
        query = '["and", {0}]'.format(
                ", ".join('["=", "{0}", "{1}"]'.format(field, env)
                    for field in ['catalog_environment', 'facts_environment']))
        num_nodes = get_or_abort(
            puppetdb._query,
            'nodes',
            query='["extract", [["function", "count"]],["and", {0}]]'.format(
                    ",".join('["=", "{0}", "{1}"]'.format(field, env)
                        for field in ['catalog_environment', 'facts_environment'])))
        num_resources = get_or_abort(
            puppetdb._query,
            'resources',
            query='["extract", [["function", "count"]],' \
                '["=", "environment", "{0}"]]'.format(
                    env))
        metrics['num_nodes'] = num_nodes[0]['count']
        metrics['num_resources'] = num_resources[0]['count']
        metrics['avg_resources_node'] = "{0:10.0f}".format(
            (num_resources[0]['count'] / num_nodes[0]['count']))

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
    check_env(env, envs)

    if env == '*':
        query = None
    else:
        query = '["and", {0}]'.format(
            ", ".join('["=", "{0}", "{1}"]'.format(field, env)
                for field in ['catalog_environment', 'facts_environment'])),

    status_arg = request.args.get('status', '')
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

    fact_desc  = []     # a list of fact descriptions to go
                        # in the table header
    fact_names = []     # a list of inventory fact names
    factvalues = {}     # values of the facts for all the nodes
                        # indexed by node name and fact name
    nodedata   = {}     # a dictionary containing list of inventoried
                        # facts indexed by node name
    nodelist   = set()  # a set of node names

    # load the list of items/facts we want in our inventory
    try:
        inv_facts = app.config['INVENTORY_FACTS']
    except KeyError:
        inv_facts = [ ('Hostname'      ,'fqdn'              ),
                      ('IP Address'    ,'ipaddress'         ),
                      ('OS'            ,'lsbdistdescription'),
                      ('Architecture'  ,'hardwaremodel'     ),
                      ('Kernel Version','kernelrelease'     ) ]

    # generate a list of descriptions and a list of fact names
    # from the list of tuples inv_facts.
    for description,name in inv_facts:
        fact_desc.append(description)
        fact_names.append(name)

    if env == '*':
        query = '["or", {0}]]'.format(
            ', '.join('["=", "name", "{0}"]'.format(name)
                for name in fact_names))
    else:
        query = '["and", ["=", "environment", "{0}"], ["or", {1}]]'.format(
            env,
            ', '.join('["=", "name", "{0}"]'.format(name)
                for name in fact_names))

    # get all the facts from PuppetDB
    facts = puppetdb.facts(query=query)

    # convert the json in easy to access data structure
    for fact in facts:
        factvalues[fact.node,fact.name] = fact.value
        nodelist.add(fact.node)

    # generate the per-host data
    for node in nodelist:
        nodedata[node] = []
        for fact_name in fact_names:
            try:
                nodedata[node].append(factvalues[node,fact_name])
            except KeyError:
                nodedata[node].append("undef")

    return Response(stream_with_context(
        stream_template('inventory.html',
            nodedata=nodedata,
            fact_desc=fact_desc,
            envs=envs,
            current_env=env)))


@app.route('/node/<node_name>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
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

    if env == '*':
        query = '["=", "certname", "{0}"]]'.format(node_name)
    else:
        query='["and", ["=", "environment", "{0}"],' \
            '["=", "certname", "{1}"]]'.format(env, node_name),

    node = get_or_abort(puppetdb.node, node_name)
    facts = node.facts()
    reports = get_or_abort(puppetdb.reports,
        query=query,
        limit=app.config['REPORTS_COUNT'],
        order_by='[{"field": "start_time", "order": "desc"}]')
    reports, reports_events = tee(reports)
    report_event_counts = {}

    for report in reports_events:
        counts = get_or_abort(puppetdb.event_counts,
            query='["and", ["=", "environment", "{0}"],' \
                '["=", "certname", "{1}"], ["=", "report", "{2}"]]'.format(
                    env,
                    node_name,
                    report.hash_),
            summarize_by="certname")
        try:
            report_event_counts[report.hash_] = counts[0]
        except IndexError:
            report_event_counts[report.hash_] = {}
    return render_template(
        'node.html',
        node=node,
        facts=yield_or_stop(facts),
        reports=yield_or_stop(reports),
        reports_count=app.config['REPORTS_COUNT'],
        report_event_counts=report_event_counts,
        envs=envs,
        current_env=env)


@app.route('/reports/', defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'page': 1})
@app.route('/<env>/reports/', defaults={'page': 1})
@app.route('/<env>/reports/page/<int:page>')
def reports(env, page):
    """Displays a list of reports and status from all nodes, retreived using the
    reports endpoint, sorted by start_time.

    :param env: Search for all reports in this environment
    :type env: :obj:`string`
    :param page: Calculates the offset of the query based on the report count
        and this value
    :type page: :obj:`int`
    """
    envs = environments()
    check_env(env, envs)

    if env == '*':
        reports_query = None
        total_query = '["extract", [["function", "count"]], ["~", "certname", ""]]'
    else:
        reports_query = '["=", "environment", "{0}"]'.format(env)
        total_query = '["extract", [["function", "count"]],'\
            '["and", ["=", "environment", "{0}"]]]'.format(env)

    reports = get_or_abort(puppetdb.reports,
        query=reports_query,
        limit=app.config['REPORTS_COUNT'],
        offset=(page-1) * app.config['REPORTS_COUNT'],
        order_by='[{"field": "start_time", "order": "desc"}]')
    total = get_or_abort(puppetdb._query,
        'reports',
        query=total_query)
    total = total[0]['count']
    reports, reports_events = tee(reports)
    report_event_counts = {}

    if total == 0 and page != 1:
        abort(404)

    for report in reports_events:
        if env == '*':
            event_count_query = '["and",' \
                '["=", "certname", "{0}"],' \
                '["=", "report", "{1}"]]'.format(
                    report.node,
                    report.hash_)
        else:
            event_count_query = '["and",' \
                '["=", "environment", "{0}"],' \
                '["=", "certname", "{1}"],' \
                '["=", "report", "{2}"]]'.format(
                    env,
                    report.node,
                    report.hash_)
        counts = get_or_abort(puppetdb.event_counts,
            query=event_count_query,
            summarize_by="certname")
        try:
            report_event_counts[report.hash_] = counts[0]
        except IndexError:
            report_event_counts[report.hash_] = {}
    return Response(stream_with_context(stream_template(
        'reports.html',
        reports=yield_or_stop(reports),
        reports_count=app.config['REPORTS_COUNT'],
        report_event_counts=report_event_counts,
        pagination=Pagination(page, app.config['REPORTS_COUNT'], total),
        envs=envs,
        current_env=env)))


@app.route('/reports/<node_name>/', defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'page': 1})
@app.route('/<env>/reports/<node_name>', defaults={'page': 1})
@app.route('/<env>/reports/<node_name>/page/<int:page>')
def reports_node(env, node_name, page):
    """Fetches all reports for a node and processes them eventually rendering
    a table displaying those reports.

    :param env: Search for reports in this environment
    :type env: :obj:`string`
    :param node_name: Find the reports whose certname match this value
    :type node_name: :obj:`string`
    :param page: Calculates the offset of the query based on the report count
        and this value
    :type page: :obj:`int`
    """
    envs = environments()
    check_env(env, envs)

    if env == '*':
        query = '["=", "certname", "{0}"]]'.format(node_name)
    else:
        query='["and",' \
            '["=", "environment", "{0}"],' \
            '["=", "certname", "{1}"]]'.format(env, node_name),

    reports = get_or_abort(puppetdb.reports,
        query=query,
        limit=app.config['REPORTS_COUNT'],
        offset=(page-1) * app.config['REPORTS_COUNT'],
        order_by='[{"field": "start_time", "order": "desc"}]')
    total = get_or_abort(puppetdb._query,
        'reports',
        query='["extract", [["function", "count"]],' \
            '["and", ["=", "environment", "{0}"], ["=", "certname", "{1}"]]]'.format(
            env,
            node_name))
    total = total[0]['count']
    reports, reports_events = tee(reports)
    report_event_counts = {}

    if total == 0 and page != 1:
        abort(404)

    for report in reports_events:
        if env == '*':
            event_count_query = '["and",' \
                '["=", "certname", "{0}"],' \
                '["=", "report", "{1}"]]'.format(
                    report.node,
                    report.hash_)
        else:
            event_count_query = '["and",' \
                '["=", "environment", "{0}"],' \
                '["=", "certname", "{1}"],' \
                '["=", "report", "{2}"]]'.format(
                    env,
                    report.node,
                    report.hash_)
        counts = get_or_abort(puppetdb.event_counts,
            query=event_count_query,
            summarize_by="certname")
        try:
            report_event_counts[report.hash_] = counts[0]
        except IndexError:
            report_event_counts[report.hash_] = {}
    return render_template(
        'reports.html',
        reports=reports,
        reports_count=app.config['REPORTS_COUNT'],
        report_event_counts=report_event_counts,
        pagination=Pagination(page, app.config['REPORTS_COUNT'], total),
        envs=envs,
        current_env=env)


@app.route('/report/latest/<node_name>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/report/latest/<node_name>')
def report_latest(env, node_name):
    """Redirect to the latest report of a given node.

    :param env: Search for reports in this environment
    :type env: :obj:`string`
    :param node_name: Find the reports whose certname match this value
    :type node_name: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if env == '*':
        node_query = '["=", "certname", "{0}"]'.format(node_name)
    else:
        node_query = '["and",' \
            '["=", "report_environment", "{0}"],' \
            '["=", "certname", "{1}"]]'.format(env, node_name)

    try:
        node = next(get_or_abort(puppetdb.nodes,
            query=node_query,
            with_status=True))
    except StopIteration:
        abort(404)

    if node.latest_report_hash is not None:
        hash_ = node.latest_report_hash
    else:
        if env == '*':
            query='["and",' \
                '["=", "certname", "{0}"],' \
                '["=", "latest_report?", true]]'.format(node.name)
        else:
            query='["and",' \
                '["=", "environment", "{0}"],' \
                '["=", "certname", "{1}"],' \
                '["=", "latest_report?", true]]'.format(
                    env,
                    node.name)

        reports = get_or_abort(puppetdb.reports, query=query)
        try:
            report = next(reports)
            hash_ = report.hash_
        except StopIteration:
            abort(404)

    return redirect(
        url_for('report', env=env, node_name=node_name, report_id=hash_))


@app.route('/report/<node_name>/<report_id>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
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

    if env == '*':
        query = '["and", ["=", "certname", "{0}"],' \
            '["or", ["=", "hash", "{1}"], ["=", "configuration_version", "{1}"]]]'.format(
                node_name, report_id)
    else:
        query = '["and", ["=", "environment", "{0}"], ["=", "certname", "{1}"],' \
            '["or", ["=", "hash", "{2}"], ["=", "configuration_version", "{2}"]]]'.format(
                env, node_name, report_id)
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

    facts_dict = collections.defaultdict(list)
    facts = get_or_abort(puppetdb.fact_names)
    for fact in facts:
        letter = fact[0].upper()
        letter_list = facts_dict[letter]
        letter_list.append(fact)
        facts_dict[letter] = letter_list

    sorted_facts_dict = sorted(facts_dict.items())
    return render_template('facts.html',
        facts_dict=sorted_facts_dict,
        facts_len=sum(map(len,facts_dict.values())) + len(facts_dict)*5,
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
        query = '["=", "environment", "{0}"]'.format(env)
    localfacts = [f for f in yield_or_stop(puppetdb.facts(
        name=fact, query=query))]
    return Response(stream_with_context(stream_template(
        'fact.html',
        name=fact,
        render_graph=render_graph,
        facts=localfacts,
        envs=envs,
        current_env=env)))


@app.route('/fact/<fact>/<value>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
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
        query = '["=", "environment", "{0}"]'.format(env)
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


@app.route('/query', methods=('GET', 'POST'), defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
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

        form = QueryForm(csrf_enabled=False)
        if form.validate_on_submit():
            if form.query.data[0] == '[':
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
    for key, value in metrics.items():
        metrics[key] = value.split('/')[2]
    return render_template('metrics.html',
        metrics=sorted(metrics.items()),
        envs=envs,
        current_env=env)


@app.route('/metric/<metric>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/metric/<metric>')
def metric(env, metric):
    """Lists all information about the metric of the given name.

    :param env: While this parameter serves no function purpose it is required
        for the environments template block
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    name = unquote(metric)
    metric = puppetdb.metric(metric)
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
        if env == '*':
            query = '["null?", "catalog_timestamp", false]]'
        else:
            query = '["and",' \
                '["=", "catalog_environment", "{0}"],' \
                '["null?", "catalog_timestamp", false]]'.format(env),
        nodes = get_or_abort(puppetdb.nodes,
            query=query,
            with_status=False,
            order_by='[{"field": "certname", "order": "asc"}]')
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

@app.route('/catalog/<node_name>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
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

@app.route('/catalog/submit', methods=['POST'], defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
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

@app.route('/catalogs/compare/<compare>...<against>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
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
