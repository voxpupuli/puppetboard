#########
Changelog
#########

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
