from flask import request, jsonify, render_template
from pypuppetdb.QueryBuilder import AndOperator, ExtractOperator, EqualsOperator, FunctionOperator

import puppetboard.metrics
import puppetboard.nodes
from puppetboard.app import app, check_env, puppetdb, metric_params
from puppetboard.core import environments
from puppetboard.utils import get_db_version, get_or_abort


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
            puppetboard.metrics.metric,
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

    nodes = puppetboard.nodes.nodes(
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