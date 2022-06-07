from flask import Response, stream_with_context, abort
from pypuppetdb.QueryBuilder import AndOperator, EqualsOperator

from puppetboard.core import get_app, get_puppetdb, environments, stream_template, to_html, \
    get_friendly_error, get_raw_error
from puppetboard.utils import check_env, yield_or_stop

app = get_app()
puppetdb = get_puppetdb()


@app.route('/failures', defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                                  'show_error_as': app.config['SHOW_ERROR_AS']})
@app.route('/failures/<show_error_as>', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/failures', defaults={'show_error_as': app.config['SHOW_ERROR_AS']})
@app.route('/<env>/failures/<show_error_as>')
def failures(env: str, show_error_as: str):
    nodes_query = AndOperator()
    nodes_query.add(EqualsOperator('latest_report_status', 'failed'))

    envs = environments()
    check_env(env, envs)
    if env != '*':
        nodes_query.add(EqualsOperator("catalog_environment", env))

    if show_error_as not in ['friendly', 'raw']:
        abort(404)

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

        source = None
        message = None
        for log in latest_failed_report.logs:
            if log['level'] not in ['info', 'notice', 'warning']:
                if log['source'] != 'Facter':
                    source = log['source']
                    message = log['message']
                    break

        if source and message:
            if show_error_as == 'friendly':
                error = to_html(get_friendly_error(source, message, node.name))
            else:
                error = get_raw_error(source, message)
        else:
            error = to_html(f'Node {node.name} is failing but we could not find the errors')

        failure = {
            'certname': node.name,
            'timestamp': node.report_timestamp,
            'error': error,
            'report_hash': node.latest_report_hash,
        }
        failures.append(failure)

    return Response(stream_with_context(
        stream_template('failures.html',
                        failures=failures,
                        envs=envs,
                        current_env=env,
                        current_show_error_as=show_error_as)))
