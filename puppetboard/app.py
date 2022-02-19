from __future__ import absolute_import
from __future__ import unicode_literals

import json
import logging
from datetime import datetime, timedelta
from itertools import tee
from json import dumps
from urllib.parse import unquote, quote_plus

import commonmark
from flask import (
    render_template, abort, url_for,
    Response, stream_with_context, request, session, jsonify
)
from pypuppetdb.QueryBuilder import (ExtractOperator, AndOperator,
                                     EqualsOperator, FunctionOperator,
                                     NullOperator, OrOperator,
                                     LessEqualOperator, RegexOperator,
                                     GreaterEqualOperator)
from requests.exceptions import HTTPError

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.dailychart import get_daily_reports_chart
from puppetboard.forms import ENABLED_QUERY_ENDPOINTS, QueryForm
from puppetboard.utils import (get_or_abort, get_or_abort_except_client_errors, yield_or_stop,
                               get_db_version, parse_python)
from puppetboard.version import __version__


# these imports are required by Flask - DO NOT remove them although they look unused
# noinspection PyUnresolvedReferences
import puppetboard.views.index
# noinspection PyUnresolvedReferences
import puppetboard.views.nodes
# noinspection PyUnresolvedReferences
import puppetboard.views.inventory
# noinspection PyUnresolvedReferences
import puppetboard.views.facts
# noinspection PyUnresolvedReferences
import puppetboard.views.reports
# noinspection PyUnresolvedReferences
import puppetboard.views.catalogs
# noinspection PyUnresolvedReferences
import puppetboard.views.metrics


app = get_app()
numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)

logging.basicConfig(level=numeric_level)
log = logging.getLogger(__name__)

puppetdb = get_puppetdb()


menu_entries = [
    ('index', 'Overview'),
    ('nodes', 'Nodes'),
    ('facts', 'Facts'),
    ('reports', 'Reports'),
    ('metrics', 'Metrics'),
    ('inventory', 'Inventory'),
    ('catalogs', 'Catalogs'),
    ('radiator', 'Radiator'),
    ('query', 'Query')
]

if not app.config.get('ENABLE_QUERY'):
    menu_entries.remove(('query', 'Query'))

if not app.config.get('ENABLE_CATALOG'):
    menu_entries.remove(('catalogs', 'Catalogs'))


app.jinja_env.globals.update(menu_entries=menu_entries)


@app.template_global()
def version():
    return __version__


@app.context_processor
def utility_processor():
    def now(format='%m/%d/%Y %H:%M:%S'):
        """returns the formated datetime"""
        return datetime.now().strftime(format)

    return dict(now=now)


@app.route('/query', methods=('GET', 'POST'), defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/query', methods=('GET', 'POST'))
def query(env):
    """Allows to execute raw, user created queries against PuppetDB. This will return
    the JSON of the response or a message telling you what went wrong why nothing was returned.

    :param env: Serves no purpose for the query data but is required for the select field in
     the environment block
    :type env: :obj:`string`
    """
    if not app.config['ENABLE_QUERY']:
        log.warning('Access to query interface disabled by administrator.')
        abort(403)

    envs = environments()
    check_env(env, envs)

    form = QueryForm(meta={
        'csrf_secret': app.config['SECRET_KEY'],
        'csrf_context': session}
    )

    if form.validate_on_submit():
        if form.endpoints.data not in ENABLED_QUERY_ENDPOINTS:
            log.warning('Access to query endpoint %s disabled by administrator.',
                        form.endpoints.data)
            abort(403)

        query = form.query.data.strip()

        # automatically wrap AST queries with [], if needed
        if form.endpoints.data != 'pql' and not query.startswith('['):
            query = f"[{query}]"

        try:
            result = get_or_abort_except_client_errors(
                puppetdb._query,
                form.endpoints.data,
                query=query)

            zero_results = (len(result) == 0)
            result = result if not zero_results else None

            if not zero_results:
                columns = result[0].keys()
            else:
                columns = []

            return render_template('query.html',
                                   form=form,
                                   zero_results=zero_results,
                                   result=result,
                                   columns=columns,
                                   envs=envs,
                                   current_env=env)

        except HTTPError as e:
            error_text = e.response.text
            return render_template('query.html',
                                   form=form,
                                   error_text=error_text,
                                   envs=envs,
                                   current_env=env)

    return render_template('query.html',
                           form=form,
                           envs=envs,
                           current_env=env)


@app.route('/daily_reports_chart.json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/daily_reports_chart.json')
def daily_reports_chart(env):
    """Return JSON data to generate a bar chart of daily runs.

    If certname is passed as GET argument, the data will target that
    node only.
    """
    certname = request.args.get('certname')
    result = get_or_abort(
        get_daily_reports_chart,
        db=puppetdb,
        env=env,
        days_number=app.config['DAILY_REPORTS_CHART_DAYS'],
        certname=certname,
    )
    return jsonify(result=result)


@app.route('/offline/<path:filename>')
def offline_static(filename):
    mimetype = 'text/html'
    if filename.endswith('.css'):
        mimetype = 'text/css'
    elif filename.endswith('.js'):
        mimetype = 'text/javascript'

    return Response(response=render_template('static/%s' % filename),
                    status=200, mimetype=mimetype)


@app.route('/status')
def health_status():
    return 'OK'
