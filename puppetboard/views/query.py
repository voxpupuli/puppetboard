import logging

from flask import (
    render_template, abort, session
)
from requests.exceptions import HTTPError

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.forms import ENABLED_QUERY_ENDPOINTS, QueryForm
from puppetboard.utils import (check_env)
from puppetboard.utils import (get_or_abort_except_client_errors)

app = get_app()
puppetdb = get_puppetdb()

logging.basicConfig(level=app.config['LOGLEVEL'].upper())
log = logging.getLogger(__name__)


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

            output = []
            if not zero_results:
                columns = result[0].keys()
                for items in result:
                    output.append(list(items.values()))
            else:
                columns = []

            return render_template('query.html',
                                   form=form,
                                   zero_results=zero_results,
                                   result=output,
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
