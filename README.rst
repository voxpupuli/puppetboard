###########
Puppetboard
###########

Puppetboard is a web interface to `PuppetDB`_ aiming to replace the reporting
functionality of `Puppet Dashboard`_.

Puppetboard relies on the `pypuppetdb`_ library to fetch data from PuppetDB
and is built with the help of the `Flask`_ microframework.

**Note**: As of the 28th of October the master branch and the upcoming 0.0.3 release
require PuppetDB 1.5 / API v3.

.. _pypuppetdb: https://pypi.python.org/pypi/pypuppetdb
.. _PuppetDB: http://docs.puppetlabs.com/puppetdb/latest/index.html
.. _Puppet Dashboard: http://docs.puppetlabs.com/dashboard/
.. _Flask: http://flask.pocoo.org

Because this project is powered by Flask we are restricted to:
    * Python 2.6
    * Python 2.7

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/overview.png
   :alt: View of a node
   :width: 1024
   :height: 700
   :align: center

.. contents::

Word of caution
===============

Puppetboard is very, very young but it works fairly well.

That being said a lot of the code is very exeprimental, just trying
to figure out what works and what not, what we need to do different
and what features we need on the PuppetDB side of things.

As such you should be at least comfortable handling a few errors
this might throw at you.

Installation
============

Currently you can only run from source:

.. code-block:: bash

   $ git clone https://github.com/nedap/puppetboard
   $ pip install -r requirements.txt

This will install all the requirements for Puppetboard.

Run it
======

Development
-----------

You can run it in development mode by simply executing:

.. code-block:: bash

   $ python dev.py

Production
----------
For WSGI capable webservers a ``wsgi.py`` is provided which ``mod_wsgi``
and ``uwsgi`` can deal with.

  * Apache mod_wsgi configuration: http://flask.pocoo.org/docs/deploying/mod_wsgi/
  * uwsgi configuration: ``uwsgi --http :9090 --wsgi-file /path/to/puppetboard/wsgi.py``
  * Passenger

In the case of uwsgi you'll of course need something like nginx in front of it to
proxy the requests to it.

Don't forget that you also need to serve the ``static/`` folder on the
``/static`` URL of your vhost. (I'm considering embedding the little additional
Javascript and CSS this application has so no one has to bother with that).

Passenger
^^^^^^^^^
From within the Puppetboard checkout:

.. code-block:: bash

   mkdir public
   mkdir tmp
   ln -s wsgi.py passenger_wsgi.py

The apache vhost configuration:

.. code-block::

   <VirtualHost *:80>
       ServerName puppetboard.example.tld
       DocumentRoot /path/to/puppetboard/public

       RackAutoDetect On
       Alias /static /path/to/puppetboard/static
       <Directory /path/to/puppetboard/>
                Options None
                Order allow,deny
                allow from all
       </Directory>
   </VirtualHost>

Configuration
=============

Puppetboard has some configuration settings, their defaults can
be viewed in ``puppetboard/default_settings.py``.

Additionally Puppetboard will look for an environment variable
called ``PUPPETBOARD_SETTINGS`` pointing to a file with identical
markup as ``default_settings.py``. Any setting defined in
``PUPPETBOARD_SETTINGS`` will override the defaults.

Experimental
------------
Pypuppetdb and Puppetboard can query and display information from
PuppetDB's experimental API endpoints.

However, if you haven't enabled them for Puppet it isn't particularily
useful to enable them here as there will be no data to retrieve.

Getting Help
============
This project is still very new so it's not inconceivable you'll run into
issues.

For bug reports you can file an `issue`_. If you need help with something
feel free to hit up `@daenney`_ by e-mail or find him on IRC. He can usually
be found on `IRCnet`_ and `Freenode`_ and idles in #puppet.

There's now also the #puppetboard channel on `Freenode`_ where we hang out
and answer questions related to pypuppetdb and Puppetboard.

.. _issue: https://github.com/nedap/puppetboard/issues
.. _@daenney: https://github.com/daenney
.. _IRCnet: http://www.ircnet.org
.. _Freenode: http://freenode.net

Third party
===========
Some people have already started building things with and around Puppetboard.

`Hunter Haugen`_ has provided a Vagrant setup:

* https://github.com/hunner/puppetboard-vagrant

`Spencer Krum`_ created a Puppet module to install Puppetboard with:

* https://github.com/nibalizer/puppet-module-puppetboard

You can install it with:

    puppet module install nibalizer-puppetboard

.. _Hunter Haugen: https://github.com/hunner
.. _Spencer Krum: https://github.com/nibalizer

Contributing
============
We welcome contributions to this project. However, there are a few ground
rules contributors should be aware of.

License
-------
This project is licensed under the Apache v2.0 License. As such, your
contributions, once accepted, are automatically covered by this license.

Commit messages
---------------
Write decent commit messages. Don't use swear words and refrain from
uninformative commit messages as 'fixed typo'.

The preferred format of a commit message:

::

    docs/quickstart: Fixed a typo in the Nodes section.

    If needed, elaborate further on this commit. Feel free to write a
    complete blog post here if that helps us understand what this is
    all about.

    Fixes #4 and resolves #2.

If you'd like a more elaborate guide on how to write and format your commit
messages have a look at this post by `Tim Pope`_.

.. _Tim Pope: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html

Screenshots
===========

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/overview.png
   :alt: Overview / Index / Homepage
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/nodes.png
   :alt: Nodes view, all active nodes
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/node.png
   :alt: Single node page / overview
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/report.png
   :alt: Report view
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/report_message.png
   :alt: Report view with message
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/facts.png
   :alt: Facts view
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/fact.png
   :alt: Single fact, with graphs
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/fact_value.png
   :alt: All nodes that have this fact with that value
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/metrics.png
   :alt: Metrics view
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/metric.png
   :alt: Single metric
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/query.png
   :alt: Query view
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/broken.png
   :alt: Error page
   :width: 1024
   :height: 700
   :align: center
