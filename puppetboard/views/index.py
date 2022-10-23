from flask import render_template
from pypuppetdb.QueryBuilder import AndOperator, EqualsOperator, FunctionOperator, ExtractOperator

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.utils import get_or_abort, check_env

app = get_app()
puppetdb = get_puppetdb()


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
        'avg_resources_node': 0,
    }

    if env != app.config['DEFAULT_ENVIRONMENT']:
        check_env(env, envs)

    if env == '*':
        query = app.config['OVERVIEW_FILTER']

        prefix = 'puppetlabs.puppetdb.population'
        num_nodes = get_or_abort(puppetdb.metric, f"{prefix}:name=num-nodes")
        num_resources = get_or_abort(puppetdb.metric, f"{prefix}:name=num-resources")

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
        'noop': 0,
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
        current_env=env,
    )
