import hashlib
import json
import logging
import re
from collections import Counter

from flask import abort, jsonify, render_template, request
from pypuppetdb.errors import EmptyResponseError
from requests.exceptions import HTTPError, RequestException

from puppetboard.core import environments, get_app, get_cache, get_puppetdb
from puppetboard.package_versions import (STATUSES, family, parse_threshold,
                                          status)
from puppetboard.utils import check_env, url_for_field

app = get_app()
cache = get_cache()
puppetdb = get_puppetdb()

logging.basicConfig(level=app.config['LOGLEVEL'].upper())
log = logging.getLogger(__name__)

MAX_NAMES = 10
MAX_NAME_LENGTH = 255
MAX_FRAGMENT_LENGTH = 100
MAX_SUGGESTIONS = 50
MAX_THRESHOLDS = 50
MAX_OS_LABEL_LENGTH = 100
# ponytail: fixed cap protecting the page, tune it after measuring on a real fleet
MAX_ROWS = 50000
SUGGESTIONS_CACHE_TIMEOUT = 600
THRESHOLD_PREFIX = 't_'
UNKNOWN_OS = 'Unknown OS'


def check_enabled():
    if not app.config['ENABLE_PACKAGES']:
        log.warning('Access to packages interface disabled by administrator')
        abort(403)


def query(ast):
    """Runs an AST query built from Python lists: user input never ends up
    concatenated into a query string."""
    return puppetdb._query('pql', query=json.dumps(ast))


def suggest_names(pattern):
    rows = query([
        'from', 'packages',
        ['extract', ['package_name'], ['~', 'package_name', pattern],
         ['group_by', 'package_name']],
        ['order_by', ['package_name']],
        ['limit', MAX_SUGGESTIONS],
    ])
    return [row['package_name'] for row in rows]


@app.route('/packages/names/json')
def packages_names():
    """Package names of the whole fleet matching a fragment, for the
    autocomplete dropdown."""
    check_enabled()
    fragment = request.args.get('q', '').strip()
    if not 2 <= len(fragment) <= MAX_FRAGMENT_LENGTH:
        return jsonify(success=True, results=[])

    key = 'packages_names_' + hashlib.sha256(fragment.lower().encode()).hexdigest()
    names = cache.get(key)
    if names is None:
        escaped = re.escape(fragment)
        try:
            # names starting with the fragment first, so that a short exact
            # name is not pushed out of the list by longer ones containing it
            names = suggest_names('(?i)^' + escaped)
            if len(names) < MAX_SUGGESTIONS:
                names += suggest_names('(?i)' + escaped)
        except (RequestException, EmptyResponseError) as e:
            log.error('Package names search failed: %s', e)
            return jsonify(success=False, results=[]), 502
        # commas separate the names in the page URL
        names = [name for name in dict.fromkeys(names) if ',' not in name][:MAX_SUGGESTIONS]
        cache.set(key, names, timeout=SUGGESTIONS_CACHE_TIMEOUT)

    return jsonify(success=True,
                   results=[{'name': name, 'value': name} for name in names])


@app.route('/node/<node_name>/packages/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/node/<node_name>/packages/json')
def node_packages(env, node_name):
    """Packages installed on a node, for the table of the node page."""
    check_enabled()
    try:
        rows = query([
            'from', 'package_inventory',
            ['extract', ['package_name', 'version', 'provider'], ['=', 'certname', node_name]],
            ['order_by', ['package_name', 'version']],
        ])
    except (RequestException, EmptyResponseError) as e:
        log.error('Packages of %s failed: %s', node_name, e)
        return jsonify(data=[], error='PuppetDB returned an error, try again in a moment.')
    return jsonify(data=[[row['package_name'], row['version'], row['provider']]
                         for row in rows])


def parse_names(raw):
    """Returns (names, too_many) from the comma-separated `pkg` parameter."""
    names = []
    for name in (raw or '').split(','):
        name = name.strip()
        if name and len(name) <= MAX_NAME_LENGTH and name not in names:
            names.append(name)
    return names[:MAX_NAMES], len(names) > MAX_NAMES


def parse_thresholds(args):
    """Returns {os label: raw threshold} from the `t_<os label>` parameters."""
    thresholds = {}
    for key, value in args.items():
        label = key[len(THRESHOLD_PREFIX):]
        if (key.startswith(THRESHOLD_PREFIX) and label and label != UNKNOWN_OS
                and value.strip() and len(label) <= MAX_OS_LABEL_LENGTH
                and len(thresholds) < MAX_THRESHOLDS):
            thresholds[label] = value
    return thresholds


def os_label(node):
    name = node.get('facts.os.name')
    if not name:
        return UNKNOWN_OS
    major = node.get('facts.os.release.major')
    return f'{name} {major}' if major else str(name)


def query_package_rows(names, env):
    filters = ['in', 'package_name', ['array', names]]
    if env != '*':
        filters = ['and', filters,
                   ['in', 'certname',
                    ['from', 'inventory',
                     ['extract', 'certname', ['=', 'environment', env]]]]]
    return query([
        'from', 'package_inventory',
        ['extract', ['certname', 'package_name', 'version', 'provider'], filters],
        ['order_by', ['certname', 'package_name', 'version']],
        ['limit', MAX_ROWS + 1],
    ])


def query_nodes(names, env):
    filters = ['in', 'certname',
               ['from', 'package_inventory',
                ['extract', 'certname', ['in', 'package_name', ['array', names]]]]]
    if env != '*':
        filters = ['and', ['=', 'environment', env], filters]
    # dotted projections come back as flat keys, e.g. row['facts.os.name']
    return query([
        'from', 'inventory',
        ['extract', ['certname', 'timestamp', 'facts.os.name', 'facts.os.release.major'],
         filters],
    ])


def build_results(package_rows, nodes, thresholds):
    """Joins the package rows with the nodes (which applies the environment
    and drops deactivated nodes), groups them by OS and computes the status
    of each row and of each server (its most severe row)."""
    nodes_by_name = {node['certname']: node for node in nodes}
    groups = {}

    def group(label):
        if label not in groups:
            raw = thresholds.get(label, '')
            threshold, invalid = parse_threshold(raw)
            groups[label] = {
                'label': label,
                'unknown': label == UNKNOWN_OS,
                'param': THRESHOLD_PREFIX + label,
                'raw': raw,
                'threshold': threshold,
                'invalid': invalid,
                'comparable': False,
                'example': None,
                'servers': {},
            }
        return groups[label]

    rows = []
    for row in package_rows:
        node = nodes_by_name.get(row['certname'])
        if node is None:
            continue
        g = group(os_label(node))
        if family(row['provider']) and not g['unknown']:
            g['comparable'] = True
            g['example'] = g['example'] or row['version']
        code = status(row['version'], row['provider'], g['threshold'])
        previous = g['servers'].get(row['certname'], 'ok')
        g['servers'][row['certname']] = min(previous, code, key=STATUSES.index)
        rows.append([code, row['certname'], g['label'], row['package_name'],
                     row['version'], row['provider'], node.get('timestamp')])

    # thresholds of a shared link whose OS has no server (anymore) are kept
    for label in thresholds:
        group(label)

    totals = Counter()
    for g in groups.values():
        g['counts'] = Counter(g['servers'].values())
        g['total'] = len(g['servers'])
        g['has_field'] = not g['unknown'] and (g['comparable'] or not g['total'])
        totals.update(g['counts'])

    rows.sort(key=lambda r: (STATUSES.index(r[0]), r[1], r[3], r[4]))
    return {
        'groups': sorted(groups.values(),
                         key=lambda g: (g['unknown'], not g['total'],
                                        -g['total'], g['label'])),
        'rows': rows,
        'totals': totals,
        'servers': sum(g['total'] for g in groups.values()),
        'any_threshold': any(g['threshold'] for g in groups.values()),
        'any_invalid': any(g['invalid'] for g in groups.values()),
    }


@app.route('/packages', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/packages')
def packages(env):
    """Which servers have some packages, and is their version below the
    threshold given for their OS."""
    check_enabled()
    envs = environments()
    check_env(env, envs)

    names, too_many = parse_names(request.args.get('pkg'))
    thresholds = parse_thresholds(request.args)
    results = None
    truncated = False
    error = None
    if names:
        try:
            package_rows = query_package_rows(names, env)
            nodes = query_nodes(names, env) if package_rows else []
        except (RequestException, EmptyResponseError) as e:
            log.error('Packages search failed: %s', e)
            package_rows, nodes = [], []
            error = (e.response.status_code
                     if isinstance(e, HTTPError) and e.response is not None
                     else True)
        truncated = len(package_rows) > MAX_ROWS
        if truncated:
            # rows are ordered by certname: drop the server cut in the middle
            # of its rows, its status would be computed on part of them
            kept = package_rows[:MAX_ROWS]
            last = kept[-1]['certname']
            if package_rows[MAX_ROWS]['certname'] == last and kept[0]['certname'] != last:
                kept = [row for row in kept if row['certname'] != last]
            package_rows = kept
        results = build_results(package_rows, nodes, thresholds)

    return render_template(
        'packages.html',
        envs=envs,
        current_env=env,
        names=names,
        too_many=too_many,
        results=results,
        truncated=truncated,
        error=error,
        max_names=MAX_NAMES,
        max_rows=MAX_ROWS,
        all_envs_url=url_for_field('env', '*'))
