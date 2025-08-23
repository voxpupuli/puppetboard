from collections import defaultdict
from flask import (
    render_template, request, render_template_string
)
from pypuppetdb.QueryBuilder import (AndOperator,
                                     EqualsOperator, OrOperator)

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.utils import (check_env, dot_lookup)

app = get_app()
puppetdb = get_puppetdb()


def inventory_facts():
    # a list of facts descriptions to go in table header
    headers = []
    # a list of inventory fact names
    fact_names = []

    # load the list of items/facts we want in our inventory
    inv_facts = app.config['INVENTORY_FACTS']

    # generate a list of descriptions and a list of fact names
    # from the list of tuples inv_facts.
    for desc, name in inv_facts:
        headers.append(desc)
        fact_names.append(name)

    return headers, fact_names


@app.route('/inventory', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/inventory')
def inventory(env):
    """Fetch all (active) nodes from PuppetDB and stream a table displaying
    those nodes along with a set of facts about them.

    :param env: Search for facts in this environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)
    headers, fact_names = inventory_facts()

    return render_template(
        'inventory.html',
        envs=envs,
        current_env=env,
        fact_headers=headers)


@app.route('/inventory/json', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/inventory/json')
def inventory_ajax(env):
    """Backend endpoint for inventory table"""
    draw = int(request.args.get('draw', 0))

    envs = environments()
    check_env(env, envs)
    headers, fact_names = inventory_facts()
    fact_templates = app.config['INVENTORY_FACT_TEMPLATES']

    query = AndOperator()
    fact_query = OrOperator()
    fact_name_bases = {name.split(".")[0] for name in fact_names}
    fact_query.add([EqualsOperator("name", name) for name in fact_name_bases])
    query.add(fact_query)

    if env != '*':
        query.add(EqualsOperator("environment", env))

    facts = puppetdb.facts(query=query)

    facts_by_node = defaultdict(dict)
    for fact in facts:
        facts_by_node[fact.node][fact.name] = fact.value

    fact_data = defaultdict(dict)
    for node, facts in facts_by_node.items():
        for name in fact_names:
            # If the fact name is in dot notation, we need to resolve it
            fact_value = dot_lookup(facts, name) if "." in name else facts.get(name, "")

            if name in fact_templates:
                fact_template = fact_templates[name]
                fact_value = render_template_string(
                    fact_template,
                    current_env=env,
                    value=fact_value,
                )
            fact_data[node][name] = fact_value

    total = len(fact_data)

    return render_template(
        'inventory.json.tpl',
        draw=draw,
        total=total,
        total_filtered=total,
        fact_data=fact_data,
        columns=fact_names)
