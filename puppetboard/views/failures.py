import re

from flask import Response, stream_with_context, abort
from pypuppetdb.QueryBuilder import AndOperator, EqualsOperator

from puppetboard.core import get_app, get_puppetdb, environments, stream_template
from puppetboard.utils import check_env, yield_or_stop

app = get_app()
puppetdb = get_puppetdb()


def get_raw_error(source: str, message: str) -> str:
    # prefix with source, if it's not trivial
    if source != 'Puppet':
        message = source + "\n\n" + message

    if '\n' in message:
        message = f"<pre>{message}</pre>"

    return message


def get_friendly_error(source: str, message: str, certname: str) -> str:
    # NOTE: the order of the below operations matters in some cases!

    # prefix with source, if it's not trivial
    if source != 'Puppet':
        message = source + "\n\n" + message

    # shorten the file paths
    code_prefix_to_remove = app.config['CODE_PREFIX_TO_REMOVE']
    message = re.sub(f'file: {code_prefix_to_remove}', 'file: …', message)

    # remove some unuseful parts
    too_long_prefix = "Could not retrieve catalog from remote server: " \
                      "Error 500 on SERVER: " \
                      "Server Error: "
    message = re.sub(f'^{too_long_prefix}', '', message)

    message = re.sub(r"(Evaluation Error: Error while evaluating a )",
                     r"Error while evaluating a ", message)

    # remove redundant certnames
    redundant_certname = f" on node {certname}"
    message = re.sub(f'{redundant_certname}$', '', message)

    redundant_certname = f" for {certname}"
    message = re.sub(f'{redundant_certname} ', ' ', message)

    # add extra line breaks for readability
    message = re.sub(r"(Error while evaluating a .*?),",
                     r"\1:\n\n", message)

    message = re.sub(r"( returned \d+:) ",
                     r"\1\n\n", message)

    # reformat and rephrase ending expression that says where in the code is the error
    # NOTE: this has to be done AFTER removing " on node ..."
    # but BEFORE replacing spaces with &nbsp;
    message = re.sub(r"(\S)\s+\(file: ([0-9a-zA-Z/_\-.…]+, line: \d+, column: \d+)\)\s*$",
                     r"\1\n\n…in \2.", message)

    message = re.sub(r"(\S)\s+\(file: ([0-9a-zA-Z/_\-.…]+, line: \d+)\)\s*$",
                     r"\1\n\n…in \2.", message)

    return message


def to_html(message: str) -> str:
    # replace \n with <br/> to not have to use <pre> which breaks wrapping
    message = re.sub(r"\n", "<br/>", message)

    # prevent line breaking inside expressions that provide code location
    message = re.sub(r"\(file: (.*?), line: (.*?), column: (.*?)\)",
                     r"(file:&nbsp;\1,&nbsp;line:&nbsp;\2,&nbsp;column:&nbsp;\3)", message)
    message = re.sub(r"\(file: (.*?), line: (.*?)\)",
                     r"(file:&nbsp;\1,&nbsp;line:&nbsp;\2)", message)

    return message


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

        for log in latest_failed_report.logs:
            if log['level'] not in ['info', 'notice', 'warning']:
                if log['source'] != 'Facter':
                    source = log['source']
                    message = log['message']
                    break

        if show_error_as == 'friendly':
            error = to_html(get_friendly_error(source, message, node.name))
        else:
            error = get_raw_error(source, message)

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
