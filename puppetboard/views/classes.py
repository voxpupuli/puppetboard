import logging

from flask import (
    render_template, abort, request
)
from pypuppetdb.QueryBuilder import (AndOperator, InOperator, FromOperator,
                                     EqualsOperator, NullOperator, ExtractOperator)

from puppetboard.core import get_app, get_cache, get_puppetdb, environments
from puppetboard.utils import yield_or_stop, check_env

# list of events status
events_status_columns = ('skipped', 'failure', 'success', 'noop')

app = get_app()
cache = get_cache()
puppetdb = get_puppetdb()

logging.basicConfig(level=app.config['LOGLEVEL'].upper())
log = logging.getLogger(__name__)


@app.route('/classes', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/classes')
def classes(env):
    """Fetch all resource events from PuppetDB of the last report of each active node
    and and groups resource events by class. Only classes with one resource event
    are taken into account.
    It streams a table displaying those classes along with the number of nodes
    and the number of events grouped by status ('Failure', 'Success' and 'Noop').

    :param env: Search for resource events in this environment
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if not app.config['ENABLE_CLASS']:
        log.warning('Access to class interface disabled by administrator')
        abort(403)

    columns = [col for col in app.config['CLASS_EVENTS_STATUS_COLUMNS'] if col[0] in events_status_columns]

    return render_template(
        'classes.html',
        columns=columns,
        envs=envs,
        current_env=env)


@app.route('/classes/json', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/classes/json')
def classes_ajax(env):
    """Backend endpoint for classes table"""

    env_cache_key = env
    draw = int(request.args.get('draw', 0))
    envs = environments()
    check_env(env, envs)

    columns = [col for col in app.config['CLASS_EVENTS_STATUS_COLUMNS'] if col[0] in events_status_columns]

    query = AndOperator()
    if env == '*':
        env_cache_key = 'all'
    else:
        query.add(EqualsOperator("report_environment", env))
    query.add(NullOperator('deactivated', True))
    nodelist = puppetdb.nodes(query=query, with_status=True)

    new_cache = {}
    cached_classes = cache.get(f'classes_resource_{env_cache_key}')
    if cached_classes is None:
        cached_classes = {}

    classes = {}
    for node in yield_or_stop(nodelist):
        last_report = node.latest_report_hash
        if last_report is None:
            continue
        is_new_report = True
        for class_name, cached_last_reports in cached_classes.items():
            if class_name in new_cache and last_report in new_cache[class_name]:
                is_new_report = False
                continue
            if last_report in cached_last_reports:
                is_new_report = False
                new_cache[class_name] = new_cache.get(class_name, {})
                new_cache[class_name][last_report] = cached_last_reports[last_report]

                classes[class_name] = classes.get(class_name, {})
                classes[class_name]['nb_events_per_status'] = classes[class_name].get('nb_events_per_status', {col[0]: 0 for col in columns})

                nb_events_per_status = cached_last_reports[last_report]['nb_events_per_status']
                for status in nb_events_per_status:
                    if status in classes[class_name]['nb_events_per_status']:
                        classes[class_name]['nb_events_per_status'][status] += nb_events_per_status[status]
        if is_new_report:
            for event in yield_or_stop(get_events(last_report, env)):
                containing_class = event.item['class']
                if containing_class is None:
                    continue

                classes[containing_class] = classes.get(containing_class, {})
                classes[containing_class]['nb_events_per_status'] = classes[containing_class].get('nb_events_per_status', {col[0]: 0 for col in columns})
                if event.status in classes[containing_class]['nb_events_per_status']:
                    classes[containing_class]['nb_events_per_status'][event.status] += 1

                new_cache[containing_class] = new_cache.get(containing_class, {})
                new_cache[containing_class][last_report] = new_cache[containing_class].get(last_report, {
                    'node_name': node.name,
                    'node_status': node.status,
                    'class_status': 'skipped',
                    'report_hash': last_report,
                    'nb_events_per_status': {col[0]: 0 for col in columns},
                })
                if event.status in new_cache[containing_class][last_report]['nb_events_per_status']:
                    new_cache[containing_class][last_report]['nb_events_per_status'][event.status] += 1

    class_to_remove = []
    for class_name in classes:
        classes[class_name]['nb_nodes'] = len(new_cache[class_name])
        classes[class_name]['nb_nodes_per_class_status'] = classes[class_name].get('nb_nodes_per_class_status', {col[0]: 0 for col in columns})
        disable_class = True
        for report_hash, report in new_cache[class_name].items():
            class_status = get_status_from_events(report['nb_events_per_status'])
            new_cache[class_name][report_hash]['class_status'] = class_status
            if class_status in classes[class_name]['nb_nodes_per_class_status']:
                disable_class = False
                classes[class_name]['nb_nodes_per_class_status'][class_status] += 1
        if disable_class:
            class_to_remove.append(class_name)

    for class_name in class_to_remove:
        del classes[class_name]

    cache.set(f'classes_resource_{env_cache_key}', new_cache)

    total = len(classes)

    return render_template(
        'classes.json.tpl',
        draw=draw,
        total=total,
        total_filtered=total,
        classes_data=classes,
        columns=[col[0] for col in columns],
        current_env=env)


def get_events(report_hash, env):
    """Fetches all resource events from PuppetDB of a given report"""
    query = AndOperator()
    if env != '*':
        query.add(EqualsOperator("environment", env))
    query = EqualsOperator("hash", report_hash)

    reports = puppetdb.reports(query=query)
    for report in yield_or_stop(reports):
        for event in yield_or_stop(report.events()):
            yield event


@app.route('/class_resource/<class_name>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/class_resource/<class_name>')
def class_resource(env, class_name):
    """Fetches the nodes from PuppetDB for which there was
    at least one event on a resource declared in a given Class.
    It streams a table displaying those nodes along with the status
    of the node and the status of the class (aka resource(s)).

    :param env: Searches for resource events in this environment
    :type env: :obj:`string`
    :param class_name: Find all nodes executing the resources declared in the
    class
    :type class_name: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    if not app.config['ENABLE_CLASS']:
        log.warning('Access to class interface disabled by administrator')
        abort(403)

    return render_template(
        'class.html',
        class_name=class_name,
        envs=envs,
        current_env=env)


@app.route('/class_resource/<class_name>/json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/class_resource/<class_name>/json')
def class_resource_ajax(env, class_name):
    """Backend endpoint for class table"""

    env_cache_key = env
    draw = int(request.args.get('draw', 0))
    envs = environments()
    check_env(env, envs)

    columns = [col for col in app.config['CLASS_EVENTS_STATUS_COLUMNS'] if col[0] in events_status_columns]

    query = InOperator('certname')
    query_from = FromOperator('resources')
    query_extract = ExtractOperator()
    query_extract.add_field('certname')
    resources_in_query = InOperator('certname')
    query_and = AndOperator()
    query_and.add(EqualsOperator('type', 'Class'))
    query_and.add(EqualsOperator('title', class_name))
    if env == '*':
        env_cache_key = 'all'
    else:
        query_and.add(EqualsOperator("environment", env))

    query_extract.add_query(query_and)
    query_from.add_query(query_extract)
    query.add_query(query_from)
    nodelist = puppetdb.nodes(query=query, with_status=True)

    cached_classes = cache.get(f'classes_resource_{env_cache_key}')
    if cached_classes is None:
        cached_classes = {}

    cached_class = cached_classes.get(class_name, {})
    reports = {}
    for node in yield_or_stop(nodelist):
        node_name = node.name
        last_report = node.latest_report_hash

        if last_report is None or node.deactivated:
            continue
        if last_report in reports:
            continue
        if last_report in cached_class:
            reports[last_report] = cached_class[last_report]
            continue

        for event in yield_or_stop(get_events(last_report, env)):
            if class_name != event.item['class']:
                continue
            reports[last_report] = reports.get(last_report, {
                'node_name': node_name,
                'node_status': node.status,
                'class_status': 'skipped',
                'report_hash': last_report,
                'nb_events_per_status': {col[0]: 0 for col in columns},
            })
            if event.status in reports[last_report]['nb_events_per_status']:
                reports[last_report]['nb_events_per_status'][event.status] += 1
        if last_report in reports:
            reports[last_report]['class_status'] = get_status_from_events(reports[last_report]['nb_events_per_status'])

    cached_classes[class_name] = reports
    cache.set(f'classes_resource_{env_cache_key}', cached_classes)

    total = len(reports)

    return render_template(
        'class_resource.json.tpl',
        draw=draw,
        total=total,
        total_filtered=total,
        nodes_data=reports)


def get_status_from_events(events_status={}):
    """Get the status of a class from the events contained in it"""

    if 'failure' in events_status and events_status['failure']:
        # if there is at least one failed event, the status of the class is 'failure'
        return 'failure'
    elif 'success' in events_status and events_status['success']:
        return 'success'
    elif 'noop' in events_status and events_status['noop']:
        return 'noop'
    else:
        # 'skipped' is the default status
        return 'skipped'
