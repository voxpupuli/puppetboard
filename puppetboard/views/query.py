import logging
import os
import yaml

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


def load_query_presets():
    """Load query presets from YAML file specified in config.

    Returns a list of preset dicts with keys: name, description, query, endpoint, raw_json
    Returns empty list if file doesn't exist, is disabled, or has parsing errors.
    """
    presets_file = app.config.get('QUERY_PRESETS_FILE')

    if not presets_file:
        return []

    if not os.path.exists(presets_file):
        log.warning('Query presets file not found: %s', presets_file)
        return []

    try:
        with open(presets_file, 'r') as f:
            presets = yaml.safe_load(f)

        if not isinstance(presets, list):
            log.error('Query presets file must contain a list of presets')
            return []

        # Validate each preset has required fields
        validated_presets = []
        for idx, preset in enumerate(presets):
            if not isinstance(preset, dict):
                log.warning('Preset at index %d is not a dict, skipping', idx)
                continue

            if 'name' not in preset or 'query' not in preset:
                log.warning('Preset at index %d missing required fields (name, query), skipping', idx)
                continue

            # Provide defaults for optional fields
            validated_preset = {
                'name': preset['name'],
                'description': preset.get('description', ''),
                'query': preset['query'],
                'endpoint': preset.get('endpoint', 'pql'),
                'raw_json': preset.get('raw_json', False)
            }

            validated_presets.append(validated_preset)

        log.info('Loaded %d query presets from %s', len(validated_presets), presets_file)
        return validated_presets

    except yaml.YAMLError as e:
        log.error('Error parsing query presets YAML file: %s', e)
        return []
    except Exception as e:
        log.error('Error loading query presets file: %s', e)
        return []


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
    if env != app.config['DEFAULT_ENVIRONMENT']:
        check_env(env, envs)

    # Load query presets from YAML file
    query_presets = load_query_presets()

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

            if form.rawjson.data:
                # for JSON view pass the response from PuppetDB as-is
                return render_template('query.html',
                                       form=form,
                                       zero_results=zero_results,
                                       result=result,
                                       columns=None,
                                       envs=envs,
                                       current_env=env,
                                       query_presets=query_presets)
            else:
                # for table view separate the columns and the rows
                rows = []
                if not zero_results:
                    columns = result[0].keys()
                    for items in result:
                        rows.append(list(items.values()))
                else:
                    columns = []

                return render_template('query.html',
                                       form=form,
                                       zero_results=zero_results,
                                       result=rows,
                                       columns=columns,
                                       envs=envs,
                                       current_env=env,
                                       query_presets=query_presets)

        except HTTPError as e:
            error_text = e.response.text
            return render_template('query.html',
                                   form=form,
                                   error_text=error_text,
                                   envs=envs,
                                   current_env=env,
                                   query_presets=query_presets)

    return render_template('query.html',
                           form=form,
                           envs=envs,
                           current_env=env,
                           query_presets=query_presets)
