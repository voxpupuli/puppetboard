from pypuppetdb.QueryBuilder import (AndOperator, InOperator, FromOperator,
                                     EqualsOperator, NullOperator, OrOperator,
                                     ExtractOperator, LessEqualOperator, SubqueryOperator)

from puppetboard.core import get_app, get_cache, get_puppetdb, environments, stream_template, REPORTS_COLUMNS
from puppetboard.utils import (yield_or_stop, check_env, get_or_abort)
from puppetboard.views.classes import (get_status_from_events)

app = get_app()
cache = get_cache()
puppetdb = get_puppetdb()

events_status_columns = ['skipped','failure','success','noop']


def build_async_cache():
    """Scheduled job triggered at regular interval in order to pre-compute the
    results to display in the classes view.
    The result contains the events associated with the last reports and is
    stored in the cache.
    """
    columns = [col for col in app.config['CLASS_EVENTS_STATUS_COLUMNS'] if col[0] in events_status_columns]

    envs = puppetdb.environments()
    for env in puppetdb.environments():
        env = env['name']
        query = AndOperator()
        query.add(EqualsOperator("environment", env))
        # get events from last report for each active node
        query_in = InOperator('hash')
        query_ex = ExtractOperator()
        query_ex.add_field('latest_report_hash')
        query_from = FromOperator('nodes')
        query_null = NullOperator('deactivated', True)
        query_ex.add_query(query_null)
        query_from.add_query(query_ex)
        query_in.add_query(query_from)
        reportlist = puppetdb.reports(query=query_in)
 
        new_cache = {}
        for report in yield_or_stop(reportlist):
            report_hash = report.hash_
            for event in yield_or_stop(report.events()):
                containing_class = event.item['class']
                status = event.status
                new_cache[containing_class] = new_cache.get(containing_class, {})
                new_cache[containing_class][report_hash] = new_cache[containing_class].get(report_hash, {
                    'node_name': report.node,
                    'node_status': report.status,
                    'class_status': 'skipped',
                    'report_hash': report_hash,
                    'nb_events_per_status': {col[0]: 0 for col in columns},
                })
                if status in new_cache[containing_class][report_hash]['nb_events_per_status']:
                    new_cache[containing_class][report_hash]['nb_events_per_status'][status] += 1
        for class_name in new_cache:
            for report_hash, report in new_cache[class_name].items():
                status = get_status_from_events(report['nb_events_per_status'])
                new_cache[class_name][report_hash]['class_status'] = get_status_from_events(report['nb_events_per_status'])

        cache.set(f'classes_resource_{env}', new_cache)
