from distutils.util import strtobool
from urllib.parse import unquote_plus, quote_plus

from flask import render_template, request, url_for, jsonify
from pypuppetdb.QueryBuilder import AndOperator, EqualsOperator

from puppetboard.app import app, check_env, puppetdb
from puppetboard.core import environments
from puppetboard.utils import get_or_abort, is_bool

graph_facts = app.config['GRAPH_FACTS']


@app.route('/facts', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/facts')
def facts(env):
    """Displays an alphabetical list of all facts currently known to
    PuppetDB.

    :param env: Serves no purpose for this function, only for consistency's
        sake
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    facts = get_or_abort(puppetdb.fact_names)

    facts_columns = [[]]
    letter = None
    letter_list = None
    break_size = (len(facts) / 4) + 1
    next_break = break_size
    count = 0
    for fact in facts:
        count += 1

        if letter != fact[0].upper() or not letter:
            if count > next_break:
                # Create a new column
                facts_columns.append([])
                next_break += break_size
            if letter_list:
                facts_columns[-1].append(letter_list)
            # Reset
            letter = fact[0].upper()
            letter_list = []

        letter_list.append(fact)
    facts_columns[-1].append(letter_list)

    return render_template('facts.html',
                           facts_columns=facts_columns,
                           envs=envs,
                           current_env=env)


@app.route('/fact/<fact>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'value': None})
@app.route('/<env>/fact/<fact>', defaults={'value': None})
@app.route('/fact/<fact>/<value>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/fact/<fact>/<value>')
def fact(env, fact, value):
    """Fetches the specific fact(/value) from PuppetDB and displays per
    node for which this fact is known.

    :param env: Searches for facts in this environment
    :type env: :obj:`string`
    :param fact: Find all facts with this name
    :type fact: :obj:`string`
    :param value: Find all facts with this value
    :type value: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    render_graph = False
    if fact in graph_facts and not value:
        render_graph = True

    value_safe = value
    if value is not None:
        value_safe = unquote_plus(value)

    return render_template(
        'fact.html',
        fact=fact,
        value=value,
        value_safe=value_safe,
        render_graph=render_graph,
        envs=envs,
        current_env=env)


@app.route('/fact/<fact>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'node': None, 'value': None})
@app.route('/<env>/fact/<fact>/json', defaults={'node': None, 'value': None})
@app.route('/fact/<fact>/<value>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'node': None})
@app.route('/fact/<fact>/<path:value>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'node': None})
@app.route('/<env>/fact/<fact>/<value>/json', defaults={'node': None})
@app.route('/node/<node>/facts/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'fact': None, 'value': None})
@app.route('/<env>/node/<node>/facts/json',
           defaults={'fact': None, 'value': None})
def fact_ajax(env, node, fact, value):
    """Fetches the specific facts matching (node/fact/value) from PuppetDB and
    return a JSON table

    :param env: Searches for facts in this environment
    :type env: :obj:`string`
    :param node: Find all facts for this node
    :type node: :obj:`string`
    :param fact: Find all facts with this name
    :type fact: :obj:`string`
    :param value: Filter facts whose value is equal to this
    :type value: :obj:`string`
    """
    draw = int(request.args.get('draw', 0))

    envs = environments()
    check_env(env, envs)

    render_graph = False
    if fact in graph_facts and not value and not node:
        render_graph = True

    query = AndOperator()
    if node:
        query.add(EqualsOperator("certname", node))

    if env != '*':
        query.add(EqualsOperator("environment", env))

    if len(query.operations) == 0:
        query = None

    # Generator needs to be converted (graph / total)
    try:
        value = int(value)
    except ValueError:
        if value is not None and query is not None:
            if is_bool(value):
                query.add(EqualsOperator('value', bool(strtobool(value))))
            else:
                query.add(EqualsOperator('value', unquote_plus(value)))
    except TypeError:
        pass

    facts = [f for f in get_or_abort(
        puppetdb.facts,
        name=fact,
        query=query)]

    total = len(facts)

    counts = {}
    json = {
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': []}

    for fact_h in facts:
        line = []
        if not fact:
            line.append(fact_h.name)
        if not node:
            line.append('<a href="{0}">{1}</a>'.format(
                url_for('node', env=env, node_name=fact_h.node),
                fact_h.node))
        if not value:
            fact_value = fact_h.value
            if isinstance(fact_value, str):
                fact_value = quote_plus(fact_h.value)

            line.append('<a href="{0}">{1}</a>'.format(
                url_for(
                    'fact', env=env, fact=fact_h.name, value=fact_value),
                fact_h.value))

        json['data'].append(line)

        if render_graph:
            if fact_h.value not in counts:
                counts[fact_h.value] = 0
            counts[fact_h.value] += 1

    if render_graph:
        json['chart'] = [
            {"label": "{0}".format(k).replace('\n', ' '),
             "value": counts[k]}
            for k in sorted(counts, key=lambda k: counts[k], reverse=True)]

    return jsonify(json)