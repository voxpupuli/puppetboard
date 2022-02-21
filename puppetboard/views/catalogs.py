import logging

from flask import (
    render_template, abort, request
)
from pypuppetdb.QueryBuilder import (AndOperator,
                                     EqualsOperator, NullOperator, RegexOperator)

from puppetboard.core import get_app, get_puppetdb, environments, CATALOGS_COLUMNS
from puppetboard.utils import (get_or_abort, check_env)

app = get_app()
puppetdb = get_puppetdb()

logging.basicConfig(level=app.config['LOGLEVEL'].upper())
log = logging.getLogger(__name__)


@app.route('/catalogs',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'compare': None})
@app.route('/<env>/catalogs', defaults={'compare': None})
@app.route('/catalogs/compare/<compare>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalogs/compare/<compare>')
def catalogs(env, compare):
    """Lists all nodes with a compiled catalog.

    :param env: Find the nodes with this catalog_environment value
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if not app.config['ENABLE_CATALOG']:
        log.warning('Access to catalog interface disabled by administrator')
        abort(403)

    return render_template(
        'catalogs.html',
        compare=compare,
        columns=CATALOGS_COLUMNS,
        envs=envs,
        current_env=env)


@app.route('/catalogs/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT'],
                     'compare': None})
@app.route('/<env>/catalogs/json', defaults={'compare': None})
@app.route('/catalogs/compare/<compare>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalogs/compare/<compare>/json')
def catalogs_ajax(env, compare):
    """Server data to catalogs as JSON to Jquery datatables
    """
    draw = int(request.args.get('draw', 0))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', app.config['NORMAL_TABLE_COUNT']))
    paging_args = {'limit': length, 'offset': start}
    search_arg = request.args.get('search[value]')
    order_column = int(request.args.get('order[0][column]', 0))
    order_filter = CATALOGS_COLUMNS[order_column].get(
        'filter', CATALOGS_COLUMNS[order_column]['attr'])
    order_dir = request.args.get('order[0][dir]', 'asc')
    order_args = '[{"field": "%s", "order": "%s"}]' % (order_filter, order_dir)

    envs = environments()
    check_env(env, envs)

    query = AndOperator()
    if env != '*':
        query.add(EqualsOperator("catalog_environment", env))
    if search_arg:
        query.add(RegexOperator("certname", r"%s" % search_arg))
    query.add(NullOperator("catalog_timestamp", False))

    nodes = get_or_abort(puppetdb.nodes,
                         query=query,
                         include_total=True,
                         order_by=order_args,
                         **paging_args)

    catalog_list = []
    total = None
    for node in nodes:
        if total is None:
            total = puppetdb.total

        catalog_list.append({
            'certname': node.name,
            'catalog_timestamp': node.catalog_timestamp,
            'form': compare,
        })

    if total is None:
        total = 0

    return render_template(
        'catalogs.json.tpl',
        total=total,
        total_filtered=total,
        draw=draw,
        columns=CATALOGS_COLUMNS,
        catalogs=catalog_list,
        envs=envs,
        current_env=env)


@app.route('/catalog/<node_name>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalog/<node_name>')
def catalog_node(env, node_name):
    """Fetches from PuppetDB the compiled catalog of a given node.

    :param env: Find the catalog with this environment value
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if app.config['ENABLE_CATALOG']:
        catalog = get_or_abort(puppetdb.catalog,
                               node=node_name)
        return render_template('catalog.html',
                               catalog=catalog,
                               envs=envs,
                               current_env=env)
    else:
        log.warn('Access to catalog interface disabled by administrator')
        abort(403)


@app.route('/catalogs/compare/<compare>...<against>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/catalogs/compare/<compare>...<against>')
def catalog_compare(env, compare, against):
    """Compares the catalog of one node, parameter compare, with that of
       with that of another node, parameter against.

    :param env: Ensure that the 2 catalogs are in the same environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if app.config['ENABLE_CATALOG']:
        compare_cat = get_or_abort(puppetdb.catalog,
                                   node=compare)
        against_cat = get_or_abort(puppetdb.catalog,
                                   node=against)

        return render_template('catalog_compare.html',
                               compare=compare_cat,
                               against=against_cat,
                               envs=envs,
                               current_env=env)
    else:
        log.warn('Access to catalog interface disabled by administrator')
        abort(403)
