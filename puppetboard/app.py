from __future__ import unicode_literals
from __future__ import absolute_import

import os
import logging
import collections
import urllib
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, abort, url_for,
    Response, stream_with_context, redirect,
    request
    )

from pypuppetdb import connect

from puppetboard.forms import QueryForm
from puppetboard.utils import (
    get_or_abort, yield_or_stop,
    ten_reports,
    )


app = Flask(__name__)
app.config.from_object('puppetboard.default_settings')
app.config.from_envvar('PUPPETBOARD_SETTINGS', silent=True)
app.secret_key = os.urandom(24)

puppetdb = connect(
    api_version=3,
    host=app.config['PUPPETDB_HOST'],
    port=app.config['PUPPETDB_PORT'],
    ssl=app.config['PUPPETDB_SSL'],
    ssl_key=app.config['PUPPETDB_KEY'],
    ssl_cert=app.config['PUPPETDB_CERT'],
    timeout=app.config['PUPPETDB_TIMEOUT'],)

numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)
if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
logging.basicConfig(level=numeric_level)
log = logging.getLogger(__name__)


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


@app.errorhandler(400)
def bad_request(e):
    return render_template('400.html'), 400


@app.errorhandler(403)
def bad_request(e):
    return render_template('403.html'), 400


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(412)
def precond_failed(e):
    """We're slightly abusing 412 to handle missing features
    depending on the API version."""
    return render_template('412.html'), 412


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


@app.route('/')
def index():
    """This view generates the index page and displays a set of metrics and
    latest reports on nodes fetched from PuppetDB.
    """
    # TODO: Would be great if we could parallelize this somehow, doing these
    # requests in sequence is rather pointless.
    prefix = 'com.puppetlabs.puppetdb.query.population'
    num_nodes = get_or_abort(
        puppetdb.metric,
        "{0}{1}".format(prefix, ':type=default,name=num-nodes'))
    num_resources = get_or_abort(
        puppetdb.metric,
        "{0}{1}".format(prefix, ':type=default,name=num-resources'))
    avg_resources_node = get_or_abort(
        puppetdb.metric,
        "{0}{1}".format(prefix, ':type=default,name=avg-resources-per-node'))
    metrics = {
        'num_nodes': num_nodes['Value'],
        'num_resources': num_resources['Value'],
        'avg_resources_node': "{0:10.6f}".format(avg_resources_node['Value']),
        }

    latest_event_count = puppetdb._query(
        'aggregate-event-counts',
        query='["=", "latest-report?", true]',
        summarize_by='certname')

    latest_event_count['noopskip'] = (
        latest_event_count['noops'] + latest_event_count['skips'])

    latest_events = puppetdb._query(
        'event-counts',
        query='["=", "latest-report?", true]',
        summarize_by='certname')

    unreported = []
    unresponsive_window = datetime.utcnow() - (
        timedelta(hours=app.config['UNRESPONSIVE_HOURS']))
    for node in puppetdb.nodes():
        try:
            node_last_seen = node.report_timestamp.replace(tzinfo=None)
            if node_last_seen < unresponsive_window:
                delta = (datetime.utcnow() - node_last_seen)
                node.noresponse = str(delta.days) + "d "
                node.noresponse += str(int(delta.seconds / 3600)) + "h "
                node.noresponse += str(int((delta.seconds % 3600) / 60)) + "m"
                unreported.append(node)
        except AttributeError:
            unreported.append(node)

    return render_template(
        'index.html',
        metrics=metrics,
        latest_event_count=latest_event_count,
        latest_events=latest_events,
        unreported=unreported)


@app.route('/nodes')
def nodes():
    """Fetch all (active) nodes from PuppetDB and stream a table displaying
    those nodes.

    Downside of the streaming aproach is that since we've already sent our
    headers we can't abort the request if we detect an error. Because of this
    we'll end up with an empty table instead because of how yield_or_stop
    works. Once pagination is in place we can change this but we'll need to
    provide a search feature instead.
    """
    status_arg = request.args.get('status', '')
    latest_events = puppetdb._query(
        'event-counts',
        query='["=", "latest-report?", true]',
        summarize_by='certname')
    nodes = []
    for node in yield_or_stop(puppetdb.nodes()):
        # check if node name is contained in any of the
        # event-counts (grouped by certname)
        status = [
            s for s in latest_events if
            s['subject']['title'] == node.name]
        if status:
            node.status = status[0]
        else:
            node.status = {}
        if status_arg:
            if node.status.has_key(status_arg) and node.status[status_arg]:
                nodes.append(node)
        else:
            nodes.append(node)

    return Response(stream_with_context(
        stream_template('nodes.html', nodes=nodes)))


@app.route('/node/<node_name>')
def node(node_name):
    """Display a dashboard for a node showing as much data as we have on that
    node. This includes facts and reports but not Resources as that is too
    heavy to do within a single request.
    """
    node = get_or_abort(puppetdb.node, node_name)
    facts = node.facts()
    reports = ten_reports(node.reports())
    return render_template(
        'node.html',
        node=node,
        facts=yield_or_stop(facts),
        reports=yield_or_stop(reports))


@app.route('/reports')
def reports():
    """Doesn't do much yet but is meant to show something like the reports of
    the last half our, something like that."""
    return render_template('reports.html')


@app.route('/reports/<node>')
def reports_node(node):
    """Fetches all reports for a node and processes them eventually rendering
    a table displaying those reports."""
    reports = ten_reports(yield_or_stop(
        puppetdb.reports('["=", "certname", "{0}"]'.format(node))))
    return render_template(
        'reports_node.html',
        reports=reports,
        nodename=node)


@app.route('/report/latest/<node_name>')
def report_latest(node_name):
    """Redirect to the latest report of a given node. This is a workaround
    as long as PuppetDB can't filter reports for latest-report? field. This
    feature has been requested: http://projects.puppetlabs.com/issues/21554
    """
    # TODO: use limit parameter in _query to get just one report
    node = get_or_abort(puppetdb.node, node_name)
    reports = ten_reports(node.reports())
    report = list(yield_or_stop(reports))[0]
    return redirect(url_for('report', node=node_name, report_id=report))


@app.route('/report/<node>/<report_id>')
def report(node, report_id):
    """Displays a single report including all the events associated with that
    report and their status.
    """
    reports = puppetdb.reports('["=", "certname", "{0}"]'.format(node))

    for report in reports:
        if report.hash_ == report_id:
            events = puppetdb.events('["=", "report", "{0}"]'.format(
                report.hash_))
            return render_template(
                'report.html',
                report=report,
                events=yield_or_stop(events))
    else:
        abort(404)


@app.route('/facts')
def facts():
    """Displays an alphabetical list of all facts currently known to
    PuppetDB."""
    facts_dict = collections.defaultdict(list)
    facts = get_or_abort(puppetdb.fact_names)
    for fact in facts:
        letter = fact[0].upper()
        letter_list = facts_dict[letter]
        letter_list.append(fact)
        facts_dict[letter] = letter_list

    sorted_facts_dict = sorted(facts_dict.items())
    return render_template('facts.html', facts_dict=sorted_facts_dict)


@app.route('/fact/<fact>')
def fact(fact):
    """Fetches the specific fact from PuppetDB and displays its value per
    node for which this fact is known."""
    # we can only consume the generator once, lists can be doubly consumed
    # om nom nom
    localfacts = [f for f in yield_or_stop(puppetdb.facts(name=fact))]
    return Response(stream_with_context(stream_template(
        'fact.html',
        name=fact,
        facts=localfacts)))


@app.route('/query', methods=('GET', 'POST'))
def query():
    """Allows to execute raw, user created querries against PuppetDB. This is
    currently highly experimental and explodes in interesting ways since none
    of the possible exceptions are being handled just yet. This will return
    the JSON of the response or a message telling you what whent wrong /
    why nothing was returned."""
    if app.config['ENABLE_QUERY']:
        form = QueryForm()
        if form.validate_on_submit():
            result = get_or_abort(
                puppetdb._query,
                form.endpoints.data,
                query='[{0}]'.format(form.query.data))
            return render_template('query.html', form=form, result=result)
        return render_template('query.html', form=form)
    else:
        log.warn('Access to query interface disabled by administrator..')
        abort(403)


@app.route('/metrics')
def metrics():
    metrics = puppetdb._query('metrics', path='mbeans')
    for key, value in metrics.iteritems():
        metrics[key] = value.split('/')[3]
    return render_template('metrics.html', metrics=sorted(metrics.items()))


@app.route('/metric/<metric>')
def metric(metric):
    name = urllib.unquote(metric)
    metric = puppetdb.metric(metric)
    return render_template(
        'metric.html',
        name=name,
        metric=sorted(metric.items()))
