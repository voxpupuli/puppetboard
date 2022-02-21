from json import dumps
from urllib.parse import quote_plus

from flask import (
    request, render_template, url_for, jsonify
)
from pypuppetdb.QueryBuilder import (AndOperator,
                                     EqualsOperator)

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.utils import (check_env, get_or_abort, parse_python)

app = get_app()
puppetdb = get_puppetdb()


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
    if fact in app.config['GRAPH_FACTS'] and value is None and node is None:
        render_graph = True

    query = AndOperator()
    if node is not None:
        query.add(EqualsOperator("certname", node))

    if env != '*':
        query.add(EqualsOperator("environment", env))

    if value is not None:
        # interpret the value as a proper type...
        value = parse_python(value)
        # ...to know if it should be quoted or not in the query to PuppetDB
        # (f.e. a string should, while a number should not)
        query.add(EqualsOperator('value', value))

    # if we have not added any operations to the query,
    # then make it explicitly empty
    if len(query.operations) == 0:
        query = None

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
        if fact is None:
            line.append(fact_h.name)
        if node is None:
            line.append('<a href="{0}">{1}</a>'.format(
                url_for('node', env=env, node_name=fact_h.node),
                fact_h.node))
        if value is None:
            if isinstance(fact_h.value, str):
                value_for_url = quote_plus(fact_h.value)
            else:
                value_for_url = fact_h.value

            line.append('["{0}", {1}]'.format(
                url_for(
                    'fact', env=env, fact=fact_h.name, value=value_for_url),
                dumps(fact_h.value)))

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

    # we consider a column label to count for ~5 lines
    column_label_height = 5

    # 1 label per different letter and up to 3 more labels for letters spanning
    # multiple columns.
    column_label_count = 3 + len(set(map(lambda fact: fact[0].upper(), facts)))

    break_size = (len(facts) + column_label_count * column_label_height) / 4.0
    next_break = break_size

    facts_columns = []
    facts_current_column = []
    facts_current_letter = []
    letter = None
    count = 0

    for fact in facts:
        count += 1

        if count > next_break:
            next_break += break_size
            if facts_current_letter:
                facts_current_column.append(facts_current_letter)
            if facts_current_column:
                facts_columns.append(facts_current_column)
            facts_current_column = []
            facts_current_letter = []
            letter = None

        if letter != fact[0].upper():
            if facts_current_letter:
                facts_current_column.append(facts_current_letter)
                facts_current_letter = []
            letter = fact[0].upper()
            count += column_label_height

        facts_current_letter.append(fact)

    if facts_current_letter:
        facts_current_column.append(facts_current_letter)
    if facts_current_column:
        facts_columns.append(facts_current_column)

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
    if fact in app.config['GRAPH_FACTS'] and not value:
        render_graph = True

    value_json = value
    if value is not None:
        value_object = parse_python(value)
        if type(value_object) is str:
            value_json = value_object
        else:
            value_json = dumps(value_object)
    natural_time_delta_sort = False
    if fact in ["uptime"]:
        natural_time_delta_sort = True
    return render_template(
        'fact.html',
        fact=fact,
        value=value,
        value_json=value_json,
        render_graph=render_graph,
        envs=envs,
        current_env=env,
        natural_time_delta_sort=natural_time_delta_sort
    )
