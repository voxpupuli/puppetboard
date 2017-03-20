#########
Changelog
#########

This is the changelog for Puppetboard.

0.2.2
=====
 * Ensure Werkzeug <= 0.11.5

0.2.1
=====

* Daily Charts
* Fixed missing javascript files on radiator view.
* TravisCI and Coveralls integration.
* Fixed app crash in catalog view.
* Upgrade pypuppetdb to 0.3.2
* Enhanced queries for Node and Report (#271)
* Optimize Inventory Code.
* Use certname instead of hostname to identify nodes when applicable.
* Add environment filter for facts.
* Update cs.js to 0.4.11
* Fix radiator column alignment
* Security checks with bandit
* Dockerfile now uses gunicorn and environment variables for
  configuration.
* Handle division by zero errors.
* Implement new Jquery Datatables.
* JSON output for radiator. * Move javascript to head tag.
* Optimize reports and node page queries.
* Fix all environments for PuppetDB 3.2
* Fact graph chart now configurable.
* Support for Flask 0.12 and Jinja2 2.9
* Fix misreporting noops as changes.

0.2.0
=====

* Full support for PuppetDB 4.x
* Updating Semantic UI to 2.1.8
* Updating Flask-WTF requirements to 0.12
* Updating WTForms to 2.x
* Restored CSRF protection on the Query Tab form
* Updating Pypuppetdb requirement to 0.3.x
* New configuration option OVERVIEW_FILTER allows users to add custom
  PuppetDB query clauses to include/exclude nodes displayed on the
  index page
* Adding Radiator view similar to what is available in Puppet Dashboard
* Adding a drop-down list in the Reports tab to configure the number of
  reports displayed
* Removing unneeded report_latest() endpoint. This endpoint was deprecated
  with the addition of the `latest_report_hash` field in the Nodes
  PuppetDB endpoint
* Enhancing Report pagination
* Using the OOP Query Builder available in Pypuppetdb 0.3.x
* Allowing PQL queries in the Query Tab
* Fixing double url-quoting bug on Metric endpodint calls
* Adding a Boolean field to the Query form to prettyprint responses from
  PuppetDB
* Fixing corner-case where empty environments would trigger a ZeroDivisionError
  due to the Number of Nodes divided by the Number of Resources calculation
* Adding additional logging in `utils.py`

0.1.2
====

* Add configuration option to set the default environment with new
  configuration option DEFAULT_ENVIRONMENT, defaults to 'production'.
* Loading all available environments with every page load.
* Adding an "All Environments" item to the Environments dropdown to
  remove all environment filters on PuppetDB data.
* Updating README.rst to update links and describe new configuration
  options.
* Fixing Query form submission problem by disabling CSRF protection.
  Needs to be re-implemented.
* Updating the pypuppetdb requirement to >= 0.2.1, using information
  available in PuppetDB 3.2 and higher
** latest_report_hash and latest_report_status fields from the Nodes
   endpoint, this effectively deprecates the report_latest() function
** code_id from the Catalogs endpoint (current unused)
* Adding a automatic refresh on the overview page to reload the page
  every X number of seconds, defaults to 30. This is configurable
  with the configuration option REFRESH_RATE
* Fixing the table alignment in the catalog_compare() page by switching
  to fixed tables from basic tables.
* Using colors similar to Puppet Dashboard and Foreman for the status
  counts sections

0.1.1
====

* Fix bug where the reports template was not generating the report links
  with the right environment

0.1.0
====

* Requires pypuppetdb >= 0.2.0
* Drop support for PuppetDB 2 and earlier
* Full support for PuppetDB 3.x
* The first directory location is now a Puppet environment which is filtered
  on all supported queries. Users can browse different environments with a
  select field in the top NavBar
* Using limit, order_by and offset parameters adding pagaination on the Reports
  page (available in the NavBar). Functionality is available to pages that
  accept a page attribute.
* The report page now directly queries pypuppetdb to match the report_id
  value with the report hash or configuration_version fields.
* Catching and aborting with a 404 if the report and report_latest function
  queries do not return a generator object.
* Adding a Catalogs page (similar to the Nodes page) with a form to compare
  one node's catalog information with that of another node.
* Updating the Query Endpoints for the Query page.
* Adding to ``templates/_macros.html`` status_counts that shows node/report
  status information, like what is avaiable on the index and nodes pages,
  available to the reports pages and tables also.
* Showing report logs and metrics in the report page.
* Removing ``limit_reports`` from ``utils.py`` because this helper function
  has been replaced by the limit PuppetDB paging function.

**Known Issues**

* fact_value pages rendered from JSON valued facts return no results. A more
  sophisticated API is required to make use of JSON valued facts (through the
  factsets, fact-paths and/or fact-contents endpoints for example)

0.0.5
=====

* Now requires WTForms versions less than 2.0
* Adding a Flask development server in ``dev.py``.
* Adding CSRF protection VIA the flask_wtf CsrfProtect object.
* Allowing users to configure the report limit on pages where reports are
  listed with the LIMIT_REPORTS configuration option.
* Adding an inventory page to users to be able to see all available nodes
  and a configure lists of facts to display VIA the INVENTORY_FACTS
  configuration option.
* Adding a page to view a node's catalog information if enabled, disabled
  by default. Can be changed with the ENABLE_CATALOG configuration attribute.
* New configuration option GRAPH_FACTS allows the user to choose which graphs
  will generate pie on the fact pages.
* Replacing Chart.js with c3.js and d3.js.
* Adding Semantic UI 0.16.1 and removing unused bootstrap styles.
* Adding an OFFLINE_MODE configuration option to load local assets or from a
  CDN service. This is useful in environments without internet access.

0.0.4
=====

* Fix the sorting of the different tables containing facts.
* Fix the license in our ``setup.py``. The license shouldn't be longer than
  200 characters. We were including the full license tripping up tools like
  bdist_rpm.

0.0.3
=====
This release introduces a few big changes. The most obvious one is the
revamped Overview page which has received significant love. Most of the work
was done by Julius Härtl. The Nodes tab has been given a slight face-lift
too.

Other changes:

* This release depends on the new pypuppetdb 0.1.0. Because of this the SSL
  configuration options have been changed:

  * ``PUPPETDB_SSL`` is gone and replaced by ``PUPPETDB_SSL_VERIFY`` which
    now defaults to ``True``. This only affects connections to PuppetDB that
    happen over SSL.
  * SSL is automatically enabled if both ``PUPPETDB_CERT`` and
    ``PUPPETDB_KEY`` are provided.

* Display of deeply nested metrics and query results have been fixed.
* Average resources per node metric is now displayed as a natural number.
* A link back to the node has been added to the reports.
* A few issues with reports have been fixed.
* A new setting called ``UNRESPONSIVE_HOURS`` has been added which denotes
  the amount of hours after which Puppetboard will display the node as
  unreported if it hasn't checked in. We default to ``2`` hours.
* The event message can now be viewed by clicking on the event.

Puppetboard is now neatly packaged up and available on PyPi. This should
significantly help reduce the convoluted installation instructions people had
to follow.

Updated installation instructions have been added on how to install from PyPi
and how to configure your HTTPD.

0.0.2
=====
In this release we've introduced a few new things. First of all we now require
pypuppetdb version 0.0.4 or later which includes support for the v3 API
introduced with PuppetDB 1.5.

Because of changes in PuppetDB 1.5 and therefor in pypuppetdb users of the v2
API, regardless of the PuppetDB version, will no longer be able to view reports
or events.

In light of this the following settings have been removed:

* ``PUPPETDB_EXPERIMENTAL``

Two new settings have been added:

* ``PUPPETDB_API``: an integer, defaulting to ``3``, representing the API
  version we want to use.
* ``ENABLE_QUERY``: a boolean, defaulting to ``True``, on wether or not to
  be able to use the Query tab.

We've also added a few new features:

* Thanks to some work done during PuppetConf together with Nick Lewis (from
  Puppet Labs) we now expose all of PuppetDB's metrics in the Metrics tab. The
  formatting isn't exactly pretty but it's a start.
* Spencer Krum added the graphing capabilities to the Facts tab.
* Daniel Lawrence added a feature so that facts on the node view are clickable
  and take you to the complete overview of that fact for your infrastructure
  and made the nodes in the complete facts list clickable so you can jump to a
  node.
* Klavs Klavsen contributed some documentation on how to run Puppetboard with
  Passenger.

0.0.1
=====
Initial release.
