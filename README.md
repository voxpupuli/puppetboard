# Puppetboard

[![PyPI Version](https://img.shields.io/pypi/v/puppetboard)](https://pypi.org/project/puppetboard/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/puppetboard)](https://pypi.org/project/puppetboard/)
![Tests Status](https://github.com/voxpupuli/puppetboard/workflows/tests%20(unit)/badge.svg)
[![codecov](https://codecov.io/gh/voxpupuli/puppetboard/branch/master/graph/badge.svg?token=uez5RoiU6I)](https://codecov.io/gh/voxpupuli/puppetboard)
[![By Voxpupuli](https://img.shields.io/badge/by-Vox%20Pupuli%20%F0%9F%A6%8A-ef902f.svg)](http://voxpupuli.org)


Puppetboard is a web interface to [PuppetDB](https://puppet.com/docs/puppetdb/latest/index.html) aiming to replace
the reporting functionality of [Puppet Enterprise console (previously: Puppet Dashboard)](https://puppet.com/docs/pe/latest/console_accessing.html)
for the open source Puppet.

![Overview](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/overview.png)

See [more screenshots here](#more-screenshots).

## Table of Contents

* [Requirements](#requirements)
* [Installation](#installation)
* [Configuration](#configuration)
* [Getting Help](#getting-help)
* [Contributing](#contributing)
* [Legal](#legal)

## Requirements<a id="requirements"></a>

* PuppetDB v. 5.2-8.*
  * (**Note**: PuppetDB 8.1.0 is not supported because of [this bug](https://github.com/puppetlabs/puppetdb/issues/3866). Please update to 8.1.1+.)
* Python 3.9-3.13 or Docker

## Installation<a id="installation"></a>

Puppetboard is packaged and available on PyPI.

### With Puppet module

There is a [Puppet module](https://forge.puppetlabs.com/puppet/puppetboard) originally written by
 [Spencer Krum](https://github.com/nibalizer) and currently maintained by [Voxpupuli](https://voxpupuli.org/)
that takes care of installing the Puppetboard for you.

To see how to get it working with RedHat/Centos 7 check out these [docs](https://github.com/voxpupuli/puppetboard/blob/master/docs/EL7.md).

### Using Docker

We provide an official Docker image in:
* [GitHub Container Registry](https://github.com/orgs/voxpupuli/packages/container/package/puppetboard),
* [Dockerhub](https://hub.docker.com/r/voxpupuli/puppetboard).

You can run the app on your PuppetDB host with this command:

```bash
docker run -it \
  -e PUPPETDB_HOST=localhost \
  -e PUPPETDB_PORT=8080 \
  -e SECRET_KEY=XXXXXXXX \
  --net=host \
  ghcr.io/voxpupuli/puppetboard
```
Note: you must provide a secret key! Generate one for example by running `ruby -e "require 'securerandom'; puts SecureRandom.hex(32)"`.

Optionally you can set `PUPPETBOARD_URL_PREFIX` env variable to a value like `/puppetboard` to run the app under a URL prefix.

You can use the following Puppet Code to have Puppetboard managed by Puppet:

```puppet
include docker

docker::image { 'ghcr.io/voxpupuli/puppetboard': }

docker::run { 'puppetboard':
  image => 'ghcr.io/voxpupuli/puppetboard',
  env   => [
    'PUPPETDB_HOST=127.0.0.1',
    'PUPPETDB_PORT=8080',
    'PUPPETBOARD_PORT=8088',
    'SECRET_KEY=XXXXXXXX',
  ],
  net   => 'host',
}
```

If you want to have all features enabled, you must use SSL talking to PuppetDB:

```puppet
file { '/etc/puppetboard':
  ensure => directory,
}
file { '/etc/puppetboard/key.pem':
  ensure => file,
  mode   => '0644',
  source => "/etc/puppetlabs/puppet/ssl/private_keys/${facts['networking']['fqdn']}.pem",
}
file { '/etc/puppetboard/cert.pem':
  ensure => file,
  mode   => '0644',
  source => "/etc/puppetlabs/puppet/ssl/certs/${facts['networking']['fqdn']}.pem",
}

include docker

docker::image { 'ghcr.io/voxpupuli/puppetboard': }

docker::run { 'puppetboard':
  image   => 'ghcr.io/voxpupuli/puppetboard',
  volumes => ['/etc/puppetboard:/etc/puppetboard:ro'],
  env     => [
    'PUPPETDB_HOST=puppet', # this must be the certname or DNS_ALT_NAME of the PuppetDB host
    'PUPPETDB_PORT=8081',
    'PUPPETBOARD_PORT=8080',
    'ENABLE_CATALOG=true',
    'PUPPETDB_SSL_VERIFY=false',
    'PUPPETDB_KEY=/etc/puppetboard/key.pem',
    'PUPPETDB_CERT=/etc/puppetboard/cert.pem',
    'SECRET_KEY=XXXXXXXX',
    'DEFAULT_ENVIRONMENT=*',
  ],
  net     => 'host',
}
```

Within an air gapped environment you want to load all content from your local puppetboard web service.
Add: `'OFFLINE_MODE=true',` to the `env` parameter list of the `docker::run` Puppet type.

We also provide the Dockerfile, so you can build the image yourself:
```bash
docker build -t puppetboard .
```

### Using Red Hat OpenShift

The included OpenShift template file helps in the creation of the Puppetboard web interface by adopting a source-to-image methodology.

You can run the app on your OpenShift environment with these commands:

```bash
# Import the template into OpenShift
oc create -f puppetboard-s2i-template.yaml 

# Create the Puppetboard application and supporting Pods.
oc new-app -p PUPPETDB_HOST=puppetdb.fqdn.com \
           --template=puppetboard-template
```

This will build a puppetboard application that queries a PuppetDB database at puppetdb.fqdn.com.

Optionally you can set other environment variables to fit your needs:

```bash
oc new-app -p PUPPETDB_HOST=puppetdb.fqdn.com \
           -p PUPPETDB_PORT=3456 \
           -p PUPPETBOARD_SOURCE_REPOSITORY_REF="v5.4.0" \
           -p PUPPETBOARD_SERVICE_NAME=prod_puppetboard \
           --template=puppetboard-template
```

This will build Puppetboard version v5.4.0 that queries the PuppetDB server on TCP/3456.

The following is a list of OpenShift parameters that you can pass to the ``oc`` command to customize the application:

- `PUPPETBOARD_SERVICE_NAME`: This is the name that will be used for application.  Deployment Configs, Build Configs 
    Services, Routes and Pods will use this value for their names as well.  You can instantiate multiple applications
    by using different names in ``oc new-app``.  Defaults to 'puppetboard'.
- `PUPPETDB_HOST`: This is the name of the PuppetDB host that Puppetboard will query for its reports.  Defaults to 'puppetdb'.
- `PUPPETDB_PORT`: This is tcp port on the `PUPPETDB_HOST` for queries.  Defaults to '8080'.
- `PUPPETBOARD_SECRET_KEY`: Identical to `SECRET_KEY` (below).  Defaults to 'Secr3t_K3y'.
- `PUPPETBOARD_PORT`: The TCP port on which the Puppetboard docker image presents the web interface.  This is not the
    user-facing web interface.  Rather, it's the port that the OpenShift route forwards **to**.  
- `SERVICE_PORT`: The TCP port on which the Puppetboard service offers its user-facing web interface on OpenShift.  Defaults to '80'.
- `PUPPETBOARD_SOURCE_REPOSITORY_URL`: The URL to the Puppetboard repository.  Defaults to 'https://github.com/voxpupuli/puppetboard.git'.
- `PUPPETBOARD_SOURCE_REPOSITORY_REF`: The branch/tag/ref for Puppetboard.  Defaults to 'master'.

### From a package

Actively maintained packages:

* [FreeBSD](https://www.freshports.org/www/py-puppetboard/)
  maintained by [Romain Tartière](https://github.com/smortex)
* [OpenBSD](https://cvsweb.openbsd.org/cgi-bin/cvsweb/ports/www/puppetboard/)
  maintained by [Sebastian Reitenbach](https://github.com/buzzdeee)

### Manually

You can also install the package from PyPI and configure a WSGI-capable application server to serve it.

We recommend using virtualenv to provide a separate environment for the app.

```bash
virtualenv -p python3 venv
. venv/bin/activate
pip install puppetboard
```

Please see [an article about more deployment setups here](https://github.com/voxpupuli/puppetboard/blob/master/docs/Deployment-setups.md).

## Configuration<a id="configuration"></a>

### Puppet agents

The default value of `usecacheonfailure = true` configuration setting for Puppet agents causes Puppet runs to always succeed,
event if there are catalog compilation failures f.e. because of a syntax error in your code. This is because in such
cases with this setting Puppet will just use a cached working catalog and report the run to PuppetDB as successful.
(Although with an error visible in the Puppet run log.)

Therefore, to show the nodes with a catalog compilation as failed in Puppetboard you need to set
`usecacheonfailure = false` in your nodes' `puppet.conf`.

### PuppetDB

Of course you need to configure your Puppet Server to store the Puppet run reports in PuppetDB.
If you haven't done that already please follow the [PuppetDB documentation](https://puppet.com/docs/puppetdb/latest/connect_puppet_server.html)
about this.

If you run Puppetboard on a different host than PuppetDB then you may want to configure the certificate
allow-list for which certificates are allowed to access data from PuppetDB.
Please read more about this feature in the [PuppetDB documentation here](https://puppet.com/docs/puppetdb/latest/configure.html#certificate-allowlist).

### App settings

Puppetboard will look for a file pointed at by the `PUPPETBOARD_SETTINGS` environment variable.
The file has to be identical to
[default_settings.py](https://github.com/voxpupuli/puppetboard/blob/master/puppetboard/default_settings.py)
but should only override the settings you need changed.

If you run PuppetDB and Puppetboard on the same machine the default settings provided will be enough to get you started
and you won't need a custom settings file.

Assuming your webserver and PuppetDB machine are not identical you will at least have to change the following settings:

-   `PUPPETDB_HOST`
-   `PUPPETDB_PORT`

By default PuppetDB requires SSL to be used when a non-local client wants to connect. Therefore you'll also have to
supply the following settings:

-   `PUPPETDB_SSL_VERIFY = True`
-   `PUPPETDB_KEY = /path/to/private/keyfile.pem`
-   `PUPPETDB_CERT = /path/to/public/keyfile.crt`

When using the Puppetboard Docker image, you may also pass Puppetboard it's certificate contents via these environment
variables, either as a multiline string or pre-base64 encoded. This can be useful where the certificate is stored in a
secrets store i.e. AWS SSM Parameter Store.

```
PUPPETDB_CERT="-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----"
```

```
PUPPETDB_CERT=LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQouLi4KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQ==
```

For information about how to generate the correct keys please refer to the
[pypuppetdb documentation](https://pypuppetdb.readthedocs.io/en/latest/connecting.html#ssl). Alternatively it is possible
to explicitly specify the protocol to be used setting the `PUPPETDB_PROTO` variable.

Other settings that might be interesting, in no particular order:

- `SECRET_KEY`: set this to a long string, **the same for each application replica**, and keep it secret. Refer to
    [Flask documentation](https://flask.palletsprojects.com/en/2.1.x/quickstart/#sessions), section
    "How to generate good secret keys" for more info. Cannot be an empty string, which is the default.
- `FAVORITE_ENVS`: an ordered list of Puppet environment names that will be shown immediately after "All Environments"
    and before other environments (which are sorted by name) in the dropdown for choosing the environment shown
    in the top-right of the UI. Environments listed here that do not really exist in your deployment are silently ignored.
- `SHOW_ERROR_AS`: `friendly` or `raw`. The former makes Puppet run errors in Report and Failures views shown
    in a modified, (arguably) more user-friendly form. The latter shows them as they are.
    Defaults to `friendly`.
- `CODE_PREFIX_TO_REMOVE`: what code path that should be shortened in "Friendly errors" to "…" for readability.
    A regexp. Defaults to `/etc/puppetlabs/code/environments(/.*?/modules)?`.
- `PUPPETDB_TIMEOUT`: Defaults to 20 seconds, but you might need to increase this value. It depends on how big the
    results are when querying PuppetDB. This behaviour will change in a future release when pagination will be introduced.
- `UNRESPONSIVE_HOURS`: The amount of hours since the last check-in after which a node is considered unresponsive.
- `LOGLEVEL`: A string representing the loglevel. It defaults to `'info'` but can be changed to `'warning'` or
    `'critical'` for less verbose logging or `'debug'` for more information.
- `ENABLE_QUERY`: Defaults to `True` causing a Query tab to show up in the web interface allowing users to write
    and execute arbitrary queries against a set of endpoints in PuppetDB. Change this to `False` to disable this.
    See `ENABLED_QUERY_ENDPOINTS` to fine-tune which endpoints are allowed.
- `ENABLED_QUERY_ENDPOINTS`: If `ENABLE_QUERY` is `True`, allow to fine tune the endpoints of PuppetDB APIs that
    can be queried. It must be a list of strings of PuppetDB endpoints for which the query is enabled.
    See the `QUERY_ENDPOINTS` constant in the `puppetboard.app` module for a list of the available endpoints.
- `GRAPH_TYPE`: Specify the type of graph to display.   Default is
    pie, other good option is donut.   Other choices can be found here:
    [C3.js documentation](https://c3js.org/examples.html#chart)
- `GRAPH_FACTS`: A list of fact names to tell PuppetBoard to generate a pie-chart on the fact page. With some fact
    values being unique per node, like ipaddress, uuid, and serial number, as well as structured facts it was no longer
    feasible to generate a graph for everything.
- `INVENTORY_FACTS`: A list of tuples that serve as the column header and the fact name to search for to create
    the inventory page. If a fact is not found for a node then `undef` is printed.
- `INVENTORY_FACT_TEMPLATES`: A mapping between fact name and jinja template to customize display
- `ENABLE_CATALOG`: If set to `True` allows the user to view a node's latest catalog. This includes all managed
    resources, their file-system locations and their relationships, if available. Defaults to `False`.
- `REFRESH_RATE`: Defaults to `30` the number of seconds to wait until the index page is automatically refreshed.
- `DEFAULT_ENVIRONMENT`: Defaults to `'production'`, as the name suggests, load all information filtered by this
    environment value, for All Environments use `'*'`.
- `REPORTS_COUNT`: Defaults to `10` the limit of the number of reports to load on the node or any reports page.
- `OFFLINE_MODE`: If set to `True` load static assets (jquery, semantic-ui, etc) from the local web server instead
    of a CDN. Defaults to `False`.
- `DAILY_REPORTS_CHART_ENABLED`: Enable the use of daily chart graphs when looking at dashboard and node view.
- `DAILY_REPORTS_CHART_DAYS`: Number of days to show history for on the daily report graphs.
- `DISPLAYED_METRICS`: Metrics to show when displaying node summary. Example: `'resources.total'`, `'events.noop'`.
- `TABLE_COUNT_SELECTOR`: Configure the dropdown to limit number of hosts to show per page.
- `LITTLE_TABLE_COUNT`: Default number of reports to show when when looking at a node.
- `NORMAL_TABLE_COUNT`: Default number of nodes to show when displaying reports and catalog nodes.
- `LOCALISE_TIMESTAMP`: If set to `True` then timestamps are shown using your browser's timezone. Otherwise UTC is used. Defaults to `True`.
- `WITH_EVENT_NUMBERS`: If set to `True` then Overview and Nodes list shows exact number of changed resources
    in the last report. Otherwise shows only 'some' string if there are resources with given status. Setting this
    to `False` gives performance benefits, especially in big Puppet environments (more than few hundreds of nodes).
    Defaults to `True`.
- `ENABLE_CLASS`: If set to `True` allows the user to view the number of resource events (number of changed resources in the last report) grouped by class.
    The resource events are grouped by their status ('failure', 'success', 'noop').
- `CLASS_EVENTS_STATUS_COLUMNS`: A mapping between the status of the resource events and the name of the columns of the table to display.
- `CACHE_TYPE`: Specifies which type of caching object to use when `SCHEDULER_ENABLED` is set to `True`.
    The cache is used for the classes view (`ENABLE_CLASS` is set to `True`) which requires parsing the events of all the latest reports to group them by Puppet class.
    If the last report is present in the cache, we do not parse the events, which avoids unnecessary processing.
    If you configure more than one worker, you must use a shared backend (e.g. `MemcachedCache`) to allow the sharing of the cache between the processes.
    Indeed, the `SimpleCache` type does not allow sharing the cache between processes, it uses the process memory to store the cache.
    Defaults to `SimpleCache`.
- `CACHE_DEFAULT_TIMEOUT`: Cache lifetime in second. Defaults to `3600`.
- `SCHEDULER_ENABLED`: If set to `True` then a scheduler instance is created in order to execute scheduled jobs. Defaults to `False`.
- `SCHEDULER_JOBS`: List of the scheduled jobs to trigger within a worker.
    A job can for example be used to compute a result to be cached. This is the case for the classes view which uses a job to pre-compute at regular intervals the results to be displayed.
    Each scheduled job must contain the following fields: `id`, `func`, `trigger`, `seconds`.
- `SCHEDULER_LOCK_BIND_PORT`: Specifies an available port that allows a single worker to listen on it.
    This allows to configure scheduled jobs in a single worker. Defaults to `49100`.

## Getting Help<a id="getting-help"></a>

For questions or bug reports you can file an [issue](https://github.com/voxpupuli/puppetboard/issues).

## Contributing<a id="contributing"></a>

### Development

Puppetboard relies on the [pypuppetdb](https://pypi.org/project/pypuppetdb/) library to fetch data from PuppetDB
and is built with the help of the [Flask](https://flask.palletsprojects.com) microframework.

If you wish to hack on Puppetboard you should fork/clone the Github repository and then install the requirements through:

```bash
pip install --upgrade wheel setuptools
python setup.py develop
pip install --upgrade -r requirements-test.txt
mypy --install-types --non-interactive puppetboard/ test/
```

You're advised to do this inside a virtualenv specifically created to work on Puppetboard as to not pollute your global Python installation.

You can run the tests with:
```bash
pytest --cov=. --cov-report=xml --strict-markers --mypy puppetboard test
pylint --errors-only puppetboard test
```

You can run the app it in development mode by simply executing:

```bash
flask run
```

You can specify listening host and port with environment variables or command line otions:

```bash
export FLASK_RUN_HOST=0.0.0.0
export FLASK_RUN_PORT=8000

flask run
```

or

```bash
flask run --host '0.0.0.0' --port '8000'
```


Use `PUPPETBOARD_SETTINGS` to change the different settings or patch `default_settings.py` directly.
Take care not to include your local changes on that file when submitting patches for Puppetboard.
Place a `settings.py` file inside the base directory of the git repository that will be used, if the environment
variable is not set.

We welcome contributions to this project. However, there are a few ground rules contributors should be aware of.

### License

This project is licensed under the Apache v2.0 License. As such, your contributions, once accepted, are automatically
covered by this license.

### Commit messages

Write decent commit messages. Don't use swear words and refrain from uninformative commit messages as 'fixed typo'.

The preferred format of a commit message:

    docs/quickstart: Fixed a typo in the Nodes section.

    If needed, elaborate further on this commit. Feel free to write a
    complete blog post here if that helps us understand what this is
    all about.

    Fixes #4 and resolves #2.

If you'd like a more elaborate guide on how to write and format your commit messages have a look at [this post
by Tim Pope](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html).

### Build a release

please see: [RELEASE.md](RELEASE.md)

## More Screenshots<a id="more-screenshots"></a>

* Overview / Index / Homepage

![Overview / Index / Homepage](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/overview.png)

* Nodes view, all active nodes

![Nodes view, all active nodes](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/nodes.png)

* Single node page / overview

![Single node page / overview](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/node.png)

* Report view

![Report view](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/report.png)

* Facts view

![Facts view](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/facts.png)

* Single fact, with graphs

![Single fact, with graphs](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/fact.png)

* All nodes that have this fact with that value

![All nodes that have this fact with that value](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/fact_value.png)

* Query view - results as table

![Query view](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/query_result_table.png)

* Query view - results as JSON

![Query view](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/query_result_json.png)

* Metrics view

![Metrics view](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/metrics.png)

* Single metric

![Single metric](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/metric.png)

* Inventory view

![Inventory view](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/inventory.png)

* Classes view, group the resource events of the last reports by Puppet class

![Classes view](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/classes.png)

* Class view, list the nodes with almost one resource event for a given class

![Class view](https://raw.githubusercontent.com/voxpupuli/puppetboard/master/screenshots/class.png)

# Legal<a id="legal"></a>

The app code is licensed under the [Apache License, Version 2.0](./LICENSE).

The favicon has been created based on the icon created by [Jonathan Coutiño](https://thenounproject.com/ralts01/)
under the [Attribution 3.0 Unported (CC BY 3.0) license](https://creativecommons.org/licenses/by/3.0/),
downloaded from the [Noun Project](https://thenounproject.com).
