from datetime import datetime, timedelta

from flask import render_template
from pypuppetdb.QueryBuilder import AndOperator, EqualsOperator, ExtractOperator, FunctionOperator
from pypuppetdb.types import Node
from pypuppetdb.utils import json_to_datetime

from puppetboard.app import app, check_env, puppetdb, metric_params
from puppetboard.utils import environments, get_db_version, get_or_abort


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

    metrics = {
        'num_nodes': 0,
        'num_resources': 0,
        'avg_resources_node': 0,
    }
    nodes_overview = []
    stats = {
        'changed': 0,
        'unchanged': 0,
        'failed': 0,
        'unreported': 0,
        'noop': 0
    }

    nodes = []

    node_status_detail_enabled = app.config['NODES_STATUS_DETAIL_ENABLED']
    resource_stats_enabled = app.config['RESOURCES_STATS_ENABLED']
    if env == '*':
        query = app.config['OVERVIEW_FILTER']

        prefix = 'puppetlabs.puppetdb.population'
        db_version = get_db_version(puppetdb)
        query_type, metric_version = metric_params(db_version)

        num_nodes = get_or_abort(
            puppetdb.metric,
            "{0}{1}".format(prefix, ':%sname=num-nodes' % query_type),
            version=metric_version)

        if resource_stats_enabled:
            num_resources = get_or_abort(
                puppetdb.metric,
                "{0}{1}".format(prefix, ':%sname=num-resources' % query_type),
                version=metric_version)

            metrics['num_resources'] = num_resources['Value']
            try:
                # Compute our own average because avg_resources_node['Value']
                # returns a string of the format "num_resources/num_nodes"
                # example: "1234/9" instead of doing the division itself.
                metrics['avg_resources_node'] = "{0:10.0f}".format(
                    (num_resources['Value'] / num_nodes['Value']))
            except ZeroDivisionError:
                metrics['avg_resources_node'] = 0

            if not node_status_detail_enabled:
                nodes = get_node_status_summary(query)
    else:
        query = AndOperator()
        query.add(EqualsOperator('catalog_environment', env))

        num_nodes_query = ExtractOperator()
        num_nodes_query.add_field(FunctionOperator('count'))
        num_nodes_query.add_query(query)

        if app.config['OVERVIEW_FILTER'] is not None:
            query.add(app.config['OVERVIEW_FILTER'])

        num_nodes = get_or_abort(
            puppetdb._query,
            'nodes',
            query=num_nodes_query)

        metrics['num_nodes'] = num_nodes[0]['count']

        if resource_stats_enabled:
            num_resources_query = ExtractOperator()
            num_resources_query.add_field(FunctionOperator('count'))
            num_resources_query.add_query(EqualsOperator("environment", env))

            num_resources = get_or_abort(
                puppetdb._query,
                'resources',
                query=num_resources_query)

            metrics['num_resources'] = num_resources[0]['count']
            try:
                metrics['avg_resources_node'] = "{0:10.0f}".format(
                    (num_resources[0]['count'] / num_nodes[0]['count']))
            except ZeroDivisionError:
                metrics['avg_resources_node'] = 0

            if not node_status_detail_enabled:
                nodes = get_node_status_summary(query)

    if node_status_detail_enabled:
        nodes = get_or_abort(puppetdb.nodes,
                             query=query,
                             unreported=app.config['UNRESPONSIVE_HOURS'],
                             with_status=True,
                             with_event_numbers=app.config['WITH_EVENT_NUMBERS'])

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

        if node_status_detail_enabled:
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


def get_node_status_summary(inner_query):
    node_status_query = ExtractOperator()
    node_status_query.add_field('certname')
    node_status_query.add_field('report_timestamp')
    node_status_query.add_field('latest_report_status')
    node_status_query.add_query(inner_query)

    node_status = get_or_abort(
        puppetdb._query,
        'nodes',
        query=node_status_query
    )

    now = datetime.utcnow()
    node_infos = []
    for node_state in node_status:
        last_report = json_to_datetime(node_state['report_timestamp'])
        last_report = last_report.replace(tzinfo=None)
        unreported_border = now - timedelta(hours=app.config['UNRESPONSIVE_HOURS'])
        certname = node_state['certname']

        node_infos.append(Node(puppetdb, name=certname, unreported=last_report < unreported_border,
                               status_report=node_state['latest_report_status']))

    return node_infos
