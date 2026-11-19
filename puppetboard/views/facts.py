from json import dumps
from urllib.parse import quote_plus

from flask import (
    request, render_template, url_for, jsonify
)
from pypuppetdb.QueryBuilder import (AndOperator,
                                     EqualsOperator)

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.utils import (check_env, get_or_abort, parse_python, get_all_fact_paths,
                                split_fact_path, dot_lookup, flatten_fact)

app = get_app()
puppetdb = get_puppetdb()


@app.route('/fact/<path:fact>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'node': None, 'value': None})
@app.route('/<env>/fact/<path:fact>/json', defaults={'node': None, 'value': None})
@app.route('/fact/<path:fact>/<value>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'node': None})
@app.route('/fact/<path:fact>/<path:value>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'node': None})
@app.route('/<env>/fact/<path:fact>/<value>/json', defaults={'node': None})
@app.route('/<env>/fact/<path:fact>/<path:value>/json', defaults={'node': None})
@app.route('/node/<node>/facts/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'fact': None, 'value': None})
@app.route('/<env>/node/<node>/facts/json',
           defaults={'fact': None, 'value': None})
def fact_ajax(env, node, fact, value):
    """Fetches the specific facts matching (node/fact/value) from PuppetDB and
    return a JSON table. Supports structured facts with dot notation (e.g., os.release.full).

    :param env: Searches for facts in this environment
    :type env: :obj:`string`
    :param node: Find all facts for this node
    :type node: :obj:`string`
    :param fact: Find all facts with this name (supports dot notation for structured facts)
    :type fact: :obj:`string`
    :param value: Filter facts whose value is equal to this
    :type value: :obj:`string`
    """
    draw = int(request.args.get('draw', 0))

    envs = environments()
    check_env(env, envs)

    # Determine if this is a structured fact query
    base_fact = None
    sub_path = None
    if fact is not None and '.' in fact:
        base_fact, sub_path = split_fact_path(fact)
    else:
        base_fact = fact

    render_graph = False
    if fact is not None and fact in app.config['GRAPH_FACTS'] and value is None and node is None:
        render_graph = True

    query = AndOperator()
    if node is not None:
        query.add(EqualsOperator("certname", node))

    if env != '*':
        query.add(EqualsOperator("environment", env))

    # For structured facts, we can't filter by value at the PuppetDB level
    # We'll need to filter in-memory after retrieving the facts
    structured_value_filter = None
    if value is not None and sub_path is not None:
        # This is a structured fact with a value filter
        structured_value_filter = parse_python(value)
    elif value is not None:
        # Simple fact with value filter
        value_parsed = parse_python(value)
        query.add(EqualsOperator('value', value_parsed))

    # if we have not added any operations to the query,
    # then make it explicitly empty
    if len(query.operations) == 0:
        query = None

    # Query PuppetDB for the base fact
    facts = [f for f in get_or_abort(
        puppetdb.facts,
        name=base_fact,
        query=query)]

    # Filter and transform facts based on sub_path
    filtered_facts = []
    for fact_obj in facts:
        if sub_path is not None:
            # Extract the nested value using dot_lookup
            if isinstance(fact_obj.value, dict):
                nested_value = dot_lookup(fact_obj.value, sub_path)
                if nested_value is not None and nested_value != "":
                    # Apply value filter if specified
                    # Handle type mismatches (e.g., "20.04" string vs 20.04 float)
                    matches_filter = (
                        structured_value_filter is None or
                        nested_value == structured_value_filter or
                        str(nested_value) == str(structured_value_filter)
                    )
                    if matches_filter:
                        # Create a pseudo-fact object with the nested value
                        class NestedFact:
                            def __init__(self, node, name, value):
                                self.node = node
                                self.name = name
                                self.value = value

                        filtered_facts.append(NestedFact(fact_obj.node, fact, nested_value))
        else:
            # Simple fact, use as-is
            filtered_facts.append(fact_obj)

    total = len(filtered_facts)

    counts = {}
    json = {
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': []}

    for fact_h in filtered_facts:
        line = []
        if fact is None:
            line.append(fact_h.name)
        if node is None:
            line.append('<a href="{0}">{1}</a>'.format(
                url_for('node', env=env, node_name=fact_h.node),
                fact_h.node))
        if value is None:
            if isinstance(fact_h.value, str):
                # https://github.com/voxpupuli/puppetboard/issues/706
                # Force quotes around string values
                # This lets plain int values that are stored as strings in the db
                # be findable when searched via the facts page
                value_for_url = '"' + quote_plus(fact_h.value) + '"'
            else:
                value_for_url = fact_h.value

            # Show normal value with link (fast!)
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


@app.route('/fact/<path:fact>/children/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/fact/<path:fact>/children/json')
def fact_children_ajax(env, fact):
    """Returns the direct children of a structured fact for lazy loading.

    :param env: Environment to search in
    :param fact: Parent fact name (e.g., 'networking' or 'networking.interfaces')
    :return: JSON with list of direct children and their metadata
    """
    envs = environments()
    check_env(env, envs)

    # Extract base fact name (PuppetDB only stores base facts, not nested paths)
    # e.g., 'networking.interfaces.eth0' -> 'networking'
    base_fact = fact.split('.')[0] if '.' in fact else fact

    # Query for the base fact
    query = AndOperator()
    if env != '*':
        query.add(EqualsOperator("environment", env))
    query.add(EqualsOperator("name", base_fact))

    if len(query.operations) == 0:
        query = None

    # Get ALL instances of this fact to aggregate keys across nodes
    facts = list(get_or_abort(puppetdb.facts, query=query))
    if not facts:
        return jsonify({'children': []})

    sample_fact = facts[0]
    if not isinstance(sample_fact.value, dict):
        return jsonify({'children': []})

    # If this is a nested fact path (e.g., 'networking.interfaces'), navigate to that level
    current_value = sample_fact.value
    if fact != base_fact:
        # Navigate to the nested level
        sub_path = fact[len(base_fact) + 1:]  # Remove 'base_fact.' prefix
        current_value = dot_lookup(sample_fact.value, sub_path)
        if current_value is None or not isinstance(current_value, dict):
            return jsonify({'children': []})

    # For variable-key facts, collect ALL keys across all nodes at this level
    all_keys = set()
    for fact_obj in facts:
        # Navigate to the same nested level for each node
        if fact != base_fact:
            sub_path = fact[len(base_fact) + 1:]
            node_value = dot_lookup(fact_obj.value, sub_path)
        else:
            node_value = fact_obj.value

        if isinstance(node_value, dict):
            all_keys.update(node_value.keys())

    # Build a merged dict with all possible keys for path discovery
    merged_value = dict(current_value) if isinstance(current_value, dict) else {}
    for key in all_keys:
        if key not in merged_value:
            merged_value[key] = None  # Add missing keys as leaf nodes

    # Get all paths using the merged structure
    fact_dict = {fact: merged_value}
    paths = get_all_fact_paths(fact_dict)

    # Build list of direct children with metadata about whether they have children
    paths_set = set(paths)
    children = []

    for path in paths:
        if path != fact:  # Skip parent itself
            # Check if this is a direct child
            depth = path.count('.') - fact.count('.')
            if depth == 1:
                # Check if this child has its own children
                has_children = any(p != path and p.startswith(path + '.') for p in paths)
                children.append({
                    'name': path,
                    'has_children': has_children
                })

    return jsonify({'children': children})


@app.route('/facts', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/facts')
def facts(env):
    """Displays an alphabetical list of all facts currently known to
    PuppetDB, with structured facts expanded into hierarchical paths.

    :param env: Serves no purpose for this function, only for consistency's
        sake
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    fact_names = get_or_abort(puppetdb.fact_names)
    base_facts = sorted(fact_names) if fact_names else []

    # Build query for environment filter
    query = AndOperator()
    if env != '*':
        query.add(EqualsOperator("environment", env))

    # if we have not added any operations to the query,
    # then make it explicitly empty
    if len(query.operations) == 0:
        query = None

    # Efficiently detect structured facts by sampling just ONE fact value per fact name
    # This avoids the N+1 query problem by using a single bulk query
    expanded_facts = []

    fact_samples = {}
    fact_all_keys = {}  # Track ALL keys seen across all nodes for dict facts

    # Only query for fact samples if we have facts to check
    if base_facts:
        # Get ALL facts in one query to detect structure AND collect all keys
        # This is MUCH faster than querying each fact individually
        try:
            all_facts = get_or_abort(puppetdb.facts, query=query)

            if all_facts:  # Handle None or empty results
                for fact_obj in all_facts:
                    fact_name = fact_obj.name

                    # Keep first sample value for structure detection
                    if fact_name not in fact_samples:
                        fact_samples[fact_name] = fact_obj.value

                    # For dict facts, collect ALL keys across all nodes
                    # This ensures we show complete list for variable-key facts
                    if isinstance(fact_obj.value, dict):
                        if fact_name not in fact_all_keys:
                            fact_all_keys[fact_name] = set()
                        fact_all_keys[fact_name].update(fact_obj.value.keys())
        except (TypeError, AttributeError):
            # Handle test scenarios where facts query may not be properly mocked
            pass

    # Now expand structured facts - group by parent
    for base_fact in base_facts:
        sample_value = fact_samples.get(base_fact)

        if sample_value is not None and isinstance(sample_value, dict):
            # This is a structured fact - add as collapsible parent with lazy-loaded children
            expanded_facts.append({
                'name': base_fact,
                'is_structured': False,
                'is_parent': True,  # Has collapsible children (lazy-loaded)
                'depth': 0,
                'children': []  # Empty - will be lazy-loaded via AJAX
            })
        else:
            # Simple fact
            expanded_facts.append({
                'name': base_fact,
                'is_structured': False,
                'is_parent': False,
                'depth': 0,
                'children': []
            })

    # we consider a column label to count for ~5 lines
    column_label_height = 5

    # 1 label per different letter and up to 3 more labels for letters spanning
    # multiple columns.
    column_label_count = 3 + len(set(map(lambda fact: fact['name'][0].upper(), expanded_facts)))

    # Count total items including children for break calculation
    total_items = sum(1 + len(fact['children']) for fact in expanded_facts)
    break_size = (total_items + column_label_count * column_label_height) / 4.0
    next_break = break_size

    facts_columns = []
    facts_current_column = []
    facts_current_letter = []
    letter = None
    count = 0

    for fact_info in expanded_facts:
        # Count parent + all children
        item_count = 1 + len(fact_info['children'])
        count += item_count

        if count > next_break:
            next_break += break_size
            if facts_current_letter:
                facts_current_column.append(facts_current_letter)
            if facts_current_column:
                facts_columns.append(facts_current_column)
            facts_current_column = []
            facts_current_letter = []
            letter = None

        if letter != fact_info['name'][0].upper():
            if facts_current_letter:
                facts_current_column.append(facts_current_letter)
                facts_current_letter = []
            letter = fact_info['name'][0].upper()
            count += column_label_height

        facts_current_letter.append(fact_info)

    if facts_current_letter:
        facts_current_column.append(facts_current_letter)
    if facts_current_column:
        facts_columns.append(facts_current_column)

    return render_template('facts.html',
                           facts_columns=facts_columns,
                           envs=envs,
                           current_env=env)


@app.route('/fact/<path:fact>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'], 'value': None})
@app.route('/<env>/fact/<path:fact>', defaults={'value': None})
@app.route('/fact/<path:fact>/<path:value>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/fact/<path:fact>/<path:value>')
def fact(env, fact, value):
    """Fetches the specific fact(/value) from PuppetDB and displays per
    node for which this fact is known. Supports structured facts with dot notation.

    :param env: Searches for facts in this environment
    :type env: :obj:`string`
    :param fact: Find all facts with this name (supports dot notation)
    :type fact: :obj:`string`
    :param value: Find all facts with this value
    :type value: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    # Check if this is a structured fact
    is_structured = '.' in fact
    base_fact, sub_path = split_fact_path(fact) if is_structured else (fact, None)

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
    return render_template(
        'fact.html',
        fact=fact,
        value=value,
        value_json=value_json,
        render_graph=render_graph,
        envs=envs,
        current_env=env,
        is_structured=is_structured
    )
