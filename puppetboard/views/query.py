import logging
from collections import OrderedDict

from flask import session, render_template
from flask_wtf import FlaskForm
from werkzeug.exceptions import abort
from wtforms import (BooleanField, SelectField, TextAreaField, validators)

from puppetboard.app import app, check_env, puppetdb
from puppetboard.utils import environments, get_or_abort

numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)
logging.basicConfig(level=numeric_level)
log = logging.getLogger(__name__)


QUERY_ENDPOINTS = OrderedDict([
    # PuppetDB API endpoint, Form name
    ('pql', 'PQL'),
    ('nodes', 'Nodes'),
    ('resources', 'Resources'),
    ('facts', 'Facts'),
    ('factsets', 'Fact Sets'),
    ('fact-paths', 'Fact Paths'),
    ('fact-contents', 'Fact Contents'),
    ('reports', 'Reports'),
    ('events', 'Events'),
    ('catalogs', 'Catalogs'),
    ('edges', 'Edges'),
    ('environments', 'Environments'),
])
ENABLED_QUERY_ENDPOINTS = app.config.get('ENABLED_QUERY_ENDPOINTS', list(QUERY_ENDPOINTS.keys()))


class QueryForm(FlaskForm):
    """The form used to allow freeform queries to be executed against
    PuppetDB."""
    query = TextAreaField('Query', [validators.DataRequired(
        message='A query is required.')])
    endpoints = SelectField('API endpoint', choices=[
        (key, value) for key, value in QUERY_ENDPOINTS.items()
        if key in ENABLED_QUERY_ENDPOINTS], default='pql')
    rawjson = BooleanField('Raw JSON')


@app.route('/query', methods=('GET', 'POST'), defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/query', methods=('GET', 'POST'))
def query(env):
    """Allows to execute raw, user created querries against PuppetDB. This is
    currently highly experimental and explodes in interesting ways since none
    of the possible exceptions are being handled just yet. This will return
    the JSON of the response or a message telling you what whent wrong /
    why nothing was returned.
    :param env: Serves no purpose for the query data but is required for the
        select field in the environment block
    :type env: :obj:`string`
    """
    if not app.config['ENABLE_QUERY']:
        log.warn('Access to query interface disabled by administrator.')
        abort(403)

    envs = environments()
    check_env(env, envs)

    form = QueryForm(meta={
        'csrf_secret': app.config['SECRET_KEY'],
        'csrf_context': session})
    if form.validate_on_submit():
        if form.endpoints.data not in ENABLED_QUERY_ENDPOINTS:
            log.warn('Access to query endpoint %s disabled by administrator.',
                     form.endpoints.data)
            abort(403)

        if form.endpoints.data == 'pql':
            query = form.query.data
        elif form.query.data[0] == '[':
            query = form.query.data
        else:
            query = '[{0}]'.format(form.query.data)

        result = get_or_abort(
            puppetdb._query,
            form.endpoints.data,
            query=query)
        return render_template('query.html',
                               form=form,
                               result=result,
                               envs=envs,
                               current_env=env)
    return render_template('query.html',
                           form=form,
                           envs=envs,
                           current_env=env)
