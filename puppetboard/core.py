import logging
import re

from flask import Flask
from pypuppetdb import connect

from puppetboard.utils import (get_or_abort, jsonprint,
                               url_for_field, url_static_offline, quote_columns_data)


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

APP = None
PUPPETDB = None


def get_app():
    global APP

    if APP is None:
        app = Flask(__name__)
        app.config.from_object('puppetboard.default_settings')
        app.config.from_envvar('PUPPETBOARD_SETTINGS', silent=True)
        app.secret_key = app.config['SECRET_KEY']

        logging.basicConfig(level=app.config['LOGLEVEL'].upper())

        app.jinja_env.filters['jsonprint'] = jsonprint
        app.jinja_env.globals['url_for_field'] = url_for_field
        app.jinja_env.globals['url_static_offline'] = url_static_offline
        app.jinja_env.globals['quote_columns_data'] = quote_columns_data
        APP = app

    return APP


def get_puppetdb():
    global PUPPETDB

    if PUPPETDB is None:
        app = get_app()
        puppetdb = connect(host=app.config['PUPPETDB_HOST'],
                           port=app.config['PUPPETDB_PORT'],
                           ssl_verify=app.config['PUPPETDB_SSL_VERIFY'],
                           ssl_key=app.config['PUPPETDB_KEY'],
                           ssl_cert=app.config['PUPPETDB_CERT'],
                           timeout=app.config['PUPPETDB_TIMEOUT'],
                           protocol=app.config['PUPPETDB_PROTO'], )
        PUPPETDB = puppetdb

    return PUPPETDB


def environments():
    puppetdb = get_puppetdb()
    envs = get_or_abort(puppetdb.environments)
    x = []

    for env in envs:
        x.append(env['name'])

    return x


# as documented in
# https://flask.palletsprojects.com/en/2.0.x/patterns/streaming/#streaming-from-templates
def stream_template(template_name, **context):
    app = get_app()
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


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
    code_prefix_to_remove = get_app().config['CODE_PREFIX_TO_REMOVE']
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
