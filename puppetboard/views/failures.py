from flask import Response, stream_with_context
from pypuppetdb.QueryBuilder import AndOperator, EqualsOperator

from puppetboard.core import get_app, get_puppetdb, environments, stream_template
from puppetboard.utils import check_env, yield_or_stop

app = get_app()
puppetdb = get_puppetdb()


@app.route('/failures', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/failures')
def failures(env):

    nodes_query = AndOperator()
    nodes_query.add(EqualsOperator('latest_report_status', 'failed'))

    envs = environments()
    check_env(env, envs)
    if env != '*':
        nodes_query.add(EqualsOperator("catalog_environment", env))

    nodes = puppetdb.nodes(
        query=nodes_query,
        with_status=True,
        with_event_numbers=False,
    )

    failures = []

    for node in yield_or_stop(nodes):

        report_query = AndOperator()
        report_query.add(EqualsOperator('hash', node.latest_report_hash))

        reports = puppetdb.reports(
            query=report_query,
        )

        latest_failed_report = next(reports)

        for log in latest_failed_report.logs:
            if log['level'] not in ['info', 'notice', 'warning']:
                if log['source'] != 'Facter':
                    source = log['source']
                    message = log['message']
                    break

        failure = {
            'certname': node.name,
            'timestamp': node.report_timestamp,
            'source': source,
            'message': message,
        }
        failures.append(failure)

    return Response(stream_with_context(
        stream_template('failures.html',
                        failures=failures,
                        envs=envs,
                        current_env=env)))
