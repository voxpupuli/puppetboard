import logging
from urllib.parse import unquote

from flask import (
    render_template
)

from puppetboard.core import get_app, get_puppetdb, environments
from puppetboard.utils import get_or_abort, check_env

app = get_app()
puppetdb = get_puppetdb()

logging.basicConfig(level=app.config['LOGLEVEL'].upper())
log = logging.getLogger(__name__)


@app.route('/metrics', defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/metrics')
def metrics(env):
    """Lists all available metrics that PuppetDB is aware of.

    :param env: While this parameter serves no function purpose it is required
        for the environments template block
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    # the list response is a dict in the format:
    # {
    #   "domain1": {
    #     "property1": {
    #      ...
    #     }
    #   },
    #   "domain2": {
    #     "property2": {
    #      ...
    #     }
    #   }
    # }
    # The MBean names are the combination of the domain and the properties
    # with a ":" in between, example:
    #   domain1:property1
    #   domain2:property2
    # reference: https://jolokia.org/reference/html/protocol.html#list
    metrics_domains = get_or_abort(puppetdb.metric)
    metrics = []
    # get all of the domains
    for domain in list(metrics_domains.keys()):
        # iterate over all of the properties in this domain
        properties = list(metrics_domains[domain].keys())
        for prop in properties:
            # combine the current domain and each property with
            # a ":" in between
            metrics.append(domain + ':' + prop)

    return render_template('metrics.html',
                           metrics=sorted(metrics),
                           envs=envs,
                           current_env=env)


@app.route('/metric/<path:metric>',
           defaults={'env': app.config['DEFAULT_ENVIRONMENT']})
@app.route('/<env>/metric/<path:metric>')
def metric(env, metric):
    """Lists all information about the metric of the given name.

    :param env: While this parameter serves no function purpose it is required
        for the environments template block
    :type env: :obj:`string`
    """
    envs = environments()
    check_env(env, envs)

    name = unquote(metric)
    metric = get_or_abort(puppetdb.metric, metric)
    return render_template(
        'metric.html',
        name=name,
        metric=sorted(metric.items()),
        envs=envs,
        current_env=env)
