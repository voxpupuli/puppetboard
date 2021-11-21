from flask import Flask
from pypuppetdb import connect
import json
import logging
import os.path

from flask import request, url_for
from jinja2.utils import contextfunction


@contextfunction
def url_static_offline(context, value):
    request_parts = os.path.split(os.path.dirname(context.name))
    static_path = '/'.join(request_parts[1:])

    return url_for('static', filename="%s/%s" % (static_path, value))


def url_for_field(field, value):
    args = request.view_args.copy()
    args.update(request.args.copy())
    args[field] = value
    return url_for(request.endpoint, **args)


def jsonprint(value):
    return json.dumps(value, indent=2, separators=(',', ': '))


def formatvalue(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, list):
        return ", ".join(map(formatvalue, value))
    elif isinstance(value, dict):
        ret = ""
        for k in value:
            ret += k + " => " + formatvalue(value[k]) + ",<br/>"
        return ret
    else:
        return str(value)


def prettyprint(value):
    html = '<table class="ui basic fixed sortable table"><thead><tr>'

    # Get keys
    for k in value[0]:
        html += "<th>" + k + "</th>"

    html += "</tr></thead><tbody>"

    for e in value:
        html += "<tr>"
        for k in e:
            html += "<td>" + formatvalue(e[k]) + "</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html


APP = None
PUPPETDB = None


def get_app():
    global APP

    if APP is None:
        app = Flask(__name__)
        app.config.from_object('puppetboard.default_settings')
        app.config.from_envvar('PUPPETBOARD_SETTINGS', silent=True)
        app.secret_key = app.config['SECRET_KEY']

        numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % app.config['LOGLEVEL'])

        app.jinja_env.filters['jsonprint'] = jsonprint
        app.jinja_env.filters['prettyprint'] = prettyprint
        app.jinja_env.globals['url_for_field'] = url_for_field
        app.jinja_env.globals['url_static_offline'] = url_static_offline
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
