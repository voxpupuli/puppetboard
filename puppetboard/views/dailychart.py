from datetime import datetime, timedelta

from flask import (
    request, jsonify
)
from pypuppetdb.QueryBuilder import (ExtractOperator, AndOperator,
                                     EqualsOperator, FunctionOperator,
                                     GreaterEqualOperator)
from pypuppetdb.QueryBuilder import (LessOperator)
from pypuppetdb.utils import UTC

from puppetboard.core import get_app, get_puppetdb
from puppetboard.utils import (get_or_abort)

app = get_app()
puppetdb = get_puppetdb()


DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


@app.route('/daily_reports_chart.json',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/daily_reports_chart.json')
def daily_reports_chart(env):
    """Return JSON data to generate a bar chart of daily runs.

    If certname is passed as GET argument, the data will target that
    node only.
    """
    certname = request.args.get('certname')
    result = get_or_abort(
        get_daily_reports_chart,
        db=puppetdb,
        env=env,
        days_number=app.config['DAILY_REPORTS_CHART_DAYS'],
        certname=certname,
    )
    return jsonify(result=result)


def _iter_dates(days_number, reverse=False):
    """Return a list of datetime pairs AB, BC, CD, ... that represent the
       24hs time ranges of today (until this midnight) and the
       previous days.
    """
    one_day = timedelta(days=1)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0,
                                      microsecond=0, tzinfo=UTC())
    days_list = list(today + one_day * (1 - i) for i in range(days_number + 1))
    if reverse:
        days_list.reverse()
        return zip(days_list, days_list[1:])
    return zip(days_list[1:], days_list)


def _build_query(env, start, end, certname=None):
    """Build a extract query with optional certname and environment."""
    query = ExtractOperator()
    query.add_field(FunctionOperator('count'))
    query.add_field('status')
    subquery = AndOperator()
    subquery.add(GreaterEqualOperator('producer_timestamp', start))
    subquery.add(LessOperator('producer_timestamp', end))
    if certname is not None:
        subquery.add(EqualsOperator('certname', certname))
    if env != '*':
        subquery.add(EqualsOperator('environment', env))
    query.add_query(subquery)
    query.add_group_by("status")
    return query


def _format_report_data(day, query_output):
    """Format the output of the query to a simpler dict."""
    result = {'day': day, 'changed': 0, 'unchanged': 0, 'failed': 0}
    for out in query_output:
        if out['status'] == 'changed':
            result['changed'] = out['count']
        elif out['status'] == 'unchanged':
            result['unchanged'] = out['count']
        elif out['status'] == 'failed':
            result['failed'] = out['count']
    return result


def get_daily_reports_chart(db, env, days_number, certname=None):
    """Return the sum of each report status (changed, unchanged, failed)
       per day, for today and the previous N days.

    This information is used to present a chart.

    :param db: The puppetdb.
    :param env: Sum up the reports in this environment.
    :param days_number: How many days to sum, including today.
    :param certname: If certname is passed, only the reports of that
    certname will be added.  If certname is not passed, all reports in
    the database will be considered.
    """
    result = []
    for start, end in _iter_dates(days_number, reverse=True):
        query = _build_query(
            env=env,
            start=start.strftime(DATETIME_FORMAT),
            end=end.strftime(DATETIME_FORMAT),
            certname=certname,
        )
        day = start.strftime(DATE_FORMAT)
        output = db._query('reports', query=query)
        result.append(_format_report_data(day, output))
    return result
