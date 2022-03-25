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

* PuppetDB v. 3.0-7.5 (will most probably work with newer, but this has not been tested yet)
* Python 3.6-3.10 or Docker

## Installation<a id="installation"></a>

Puppetboard is packaged and available on PyPI.

### With Puppet module

There is a [Puppet module](https://forge.puppetlabs.com/puppet/puppetboard) originally written by
 [Spencer Krum](https://github.com/nibalizer) and currently maintained by [Voxpupuli](https://voxpupuli.org/)
that takes care of installing the Puppetboard for you.

To see how to get it working with RedHat/Centos 7 check out these [docs](https://github.com/voxpupuli/puppetboard/blob/master/docs/EL7.md).

### Using Docker

We provide [an official Docker image in the GitHub Container Registry](https://github.com/orgs/voxpupuli/packages/container/package/puppetboard).

You can run the app on your PuppetDB host with this command:

```bash
docker run -it \
  -e PUPPETDB_HOST=localhost \
  -e PUPPETDB_PORT=8080 \
  --net=host \
  ghcr.io/voxpupuli/puppetboard
```

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
  ],
  net   => 'host',
}
```

We also provide the Dockerfile so you can build the image yourself:
```bash
docker build -t puppetboard .
```

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

-   `PUPPETDB_SSL_VERIFY = /path/to/ca/keyfile.pem`
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

Other settings that might be interesting in no particular order:

-   `SECRET_KEY`: Refer to [Flask documentation](https://flask.palletsprojects.com/en/1.1.x/quickstart/#sessions),
    section "How to generate good secret keys" for more info. Defaults to a random 24-char string generated by
    `os.random(24)`.
-   `PUPPETDB_TIMEOUT`: Defaults to 20 seconds, but you might need to increase this value. It depends on how big the
    results are when querying PuppetDB. This behaviour will change in a future release when pagination will be introduced.
-   `UNRESPONSIVE_HOURS`: The amount of hours since the last check-in after which a node is considered unresponsive.
-   `LOGLEVEL`: A string representing the loglevel. It defaults to `'info'` but can be changed to `'warning'` or
    `'critical'` for less verbose logging or `'debug'` for more information.
-   `ENABLE_QUERY`: Defaults to `True` causing a Query tab to show up in the web interface allowing users to write
    and execute arbitrary queries against a set of endpoints in PuppetDB. Change this to `False` to disable this.
    See `ENABLED_QUERY_ENDPOINTS` to fine-tune which endpoints are allowed.
-   `ENABLED_QUERY_ENDPOINTS`: If `ENABLE_QUERY` is `True`, allow to fine tune the endpoints of PuppetDB APIs that
    can be queried. It must be a list of strings of PuppetDB endpoints for which the query is enabled.
    See the `QUERY_ENDPOINTS` constant in the `puppetboard.app` module for a list of the available endpoints.
-   `GRAPH_TYPE`: Specify the type of graph to display.   Default is
    pie, other good option is donut.   Other choices can be found here:
    \_C3JS\_documentation\`
-   `GRAPH_FACTS`: A list of fact names to tell PuppetBoard to generate a pie-chart on the fact page. With some fact
    values being unique per node, like ipaddress, uuid, and serial number, as well as structured facts it was no longer
    feasible to generate a graph for everything.
-   `INVENTORY_FACTS`: A list of tuples that serve as the column header and the fact name to search for to create
    the inventory page. If a fact is not found for a node then `undef` is printed.
-   `ENABLE_CATALOG`: If set to `True` allows the user to view a node's latest catalog. This includes all managed
    resources, their file-system locations and their relationships, if available. Defaults to `False`.
-   `REFRESH_RATE`: Defaults to `30` the number of seconds to wait until the index page is automatically refreshed.
-   `DEFAULT_ENVIRONMENT`: Defaults to `'production'`, as the name suggests, load all information filtered by this
    environment value.
-   `REPORTS_COUNT`: Defaults to `10` the limit of the number of reports to load on the node or any reports page.
-   `OFFLINE_MODE`: If set to `True` load static assets (jquery, semantic-ui, etc) from the local web server instead
    of a CDN. Defaults to `False`.
-   `DAILY_REPORTS_CHART_ENABLED`: Enable the use of daily chart graphs when looking at dashboard and node view.
-   `DAILY_REPORTS_CHART_DAYS`: Number of days to show history for on the daily report graphs.
-   `DISPLAYED_METRICS`: Metrics to show when displaying node summary. Example: `'resources.total'`, `'events.noop'`.
-   `TABLE_COUNT_SELECTOR`: Configure the dropdown to limit number of hosts to show per page.
-   `LITTLE_TABLE_COUNT`: Default number of reports to show when when looking at a node.
-   `NORMAL_TABLE_COUNT`: Default number of nodes to show when displaying reports and catalog nodes.
-   `LOCALISE_TIMESTAMP`: Normalize time based on localserver time.
-   `WITH_EVENT_NUMBERS`: If set to `True` then Overview and Nodes list shows exact number of changed resources
    in the last report. Otherwise shows only 'some' string if there are resources with given status. Setting this
    to `False` gives performance benefits, especially in big Puppet environments (more than few hundreds of nodes).
    Defaults to `True`.
-   `DEV_LISTEN_HOST`: For use with dev.py for development. Default is localhost
-   `DEV_LISTEN_PORT`: For use with dev.py for development. Default is 5555

## Getting Help<a id="getting-help"></a>

For questions or bug reports you can file an [issue](https://github.com/voxpupuli/puppetboard/issues).

## Contributing<a id="contributing"></a>

### Development

Puppetboard relies on the [pypuppetdb](https://pypi.org/project/pypuppetdb/) library to fetch data from PuppetDB
and is built with the help of the [Flask](https://flask.palletsprojects.com) microframework.

If you wish to hack on Puppetboard you should fork/clone the Github repository and then install the requirements through:

```bash
pip install --upgrade wheel setuptools
pip install --upgrade -r requirements-test.txt
mypy --install-types --non-interactive puppetboard/ test/
```

You're advised to do this inside a virtualenv specifically created to work on Puppetboard as to not pollute your global Python installation.

You can run the tests with:
```bash
pytest --cov=. --cov-report=xml --flake8 --strict-markers --mypy puppetboard test
```

You can run the app it in development mode by simply executing:

```bash
./dev.py
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

# Legal<a id="legal"></a>

The app code is licensed under the [Apache License, Version 2.0](./LICENSE).

The favicon has been created based on the icon created by [Jonathan Coutiño](https://thenounproject.com/ralts01/)
under the [Attribution 3.0 Unported (CC BY 3.0) license](https://creativecommons.org/licenses/by/3.0/),
downloaded from the [Noun Project](https://thenounproject.com).
