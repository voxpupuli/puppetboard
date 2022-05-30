import json
import re
from itertools import tee

import commonmark
from flask import (
    request, render_template, abort
)
from pypuppetdb.QueryBuilder import (AndOperator,
                                     EqualsOperator, OrOperator,
                                     LessEqualOperator, RegexOperator, GreaterEqualOperator)

from puppetboard.core import get_app, get_puppetdb, environments, REPORTS_COLUMNS, to_html, \
    get_raw_error, get_friendly_error
from puppetboard.utils import (check_env, get_or_abort)

app = get_app()
puppetdb = get_puppetdb()


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
    date_args = request.args.get('columns[0][search][value]', '')
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

    if date_args:
        dates = json.loads(date_args)

        if len(dates) > 0:
            date_query = AndOperator()

            if 'min' in dates:
                date_query.add(GreaterEqualOperator('end_time', dates['min']))

            if 'max' in dates:
                date_query.add(LessEqualOperator('end_time', dates['max']))

            reports_query.add(date_query)

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


def get_location(log) -> str:
    return f"{log['file']}:{log['line']}" if (log['file'] and log['line']) else ''


def get_short_location(location: str) -> str:
    # shorten the file paths
    code_prefix_to_remove = app.config['CODE_PREFIX_TO_REMOVE']
    location = re.sub(f'^{code_prefix_to_remove}', '…', location)
    return location


def get_message(node_name, log, show_error_as):
    if show_error_as == 'friendly':
        error = to_html(get_friendly_error(log['source'], log['message'], node_name))
    else:
        error = get_raw_error(log['source'], log['message'])
    return error


@app.route('/report/<node_name>/<report_id>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'show_error_as': app.config['SHOW_ERROR_AS']})
@app.route('/report/<node_name>/<report_id>/<show_error_as>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/report/<node_name>/<report_id>',
           defaults={'show_error_as': app.config['SHOW_ERROR_AS']})
@app.route('/<env>/report/<node_name>/<report_id>/<show_error_as>')
def report(env, node_name, report_id, show_error_as):
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
    :param show_error_as: 'friendly' or 'raw', the former means that messages
        will be show in a mode transformed for human-readability, the latter
        that the messages will be unchanged
    :param show_error_as: :obj:`string`
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

    if show_error_as not in ['friendly', 'raw']:
        abort(404)

    report.version = commonmark.commonmark(report.version)

    events = [{
        'resource': f"{event.item['type']}[{event.item['title']}]",
        'status': event.status,
        'old': event.item['old'],
        'new': event.item['new'],
        'failed': event.failed,
    } for event in report.events()]

    logs = [{
        'timestamp': log['time'],
        'level': log["level"],
        'source': log['source'],
        'tags': ', '.join(log['tags']),
        'message': get_message(node_name, log, show_error_as),
        'location': get_location(log),
        # this could be also done with a different rendered in DataTables,
        # - feel free to refactor it into that if you know how
        'short_location': get_short_location(get_location(log)),
    } for log in report.logs]

    return render_template(
        'report.html',
        report=report,
        events=events,
        logs=logs,
        metrics=report.metrics,
        envs=envs,
        current_env=env,
        current_show_error_as=show_error_as)
