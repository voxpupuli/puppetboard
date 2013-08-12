###########
Puppetboard
###########

Puppetboard is a web interface to `PuppetDB`_ aiming to replace the reporting
functionality of `Puppet Dashboard`_.

Puppetboard relies on the `pypuppetdb`_ library to fetch data from PuppetDB
and is built with the help of the `Flask`_ microframework.

.. _pypuppetdb: https://pypi.python.org/pypi/pypuppetdb
.. _PuppetDB: http://docs.puppetlabs.com/puppetdb/latest/index.html
.. _Puppet Dashboard: http://docs.puppetlabs.com/dashboard/
.. _Flask: http://flask.pocoo.org

Because this project is powered by Flask we are restricted to:
    * Python 2.6
    * Python 2.7

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/node-experimental.png
   :alt: View of a node
   :width: 1024
   :height: 700
   :align: center

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

You can run in it in development mode by simple executing:

.. code-block:: bash

   $ python dev.py

Production
----------
For WSGI capable webservers a ``wsgi.py`` is provided which ``mod_wsgi``
and ``uwsgi`` can deal with.

  * Apache mod_wsgi configuration: http://flask.pocoo.org/docs/deploying/mod_wsgi/
  * uwsgi configuration: ``uwsgi --http :9090 --wsgi-file /path/to/puppetboard/wsgi.py``

In the case of uwsgi you'll of course need something like nginx in front of it to
proxy the requests to it.

Don't forget that you also need to serve the ``static/`` folder on the
``/static`` URL of your vhost. (I'm considering embedding the little additional
Javascript and CSS this application has so no one has to bother with that).

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

Third party
===========
Some people have already started building things with and around Puppetboard.

`Hunter Haugen`_ has provided a Vagrant setup:

* https://github.com/hunner/puppetboard-vagrant

`Krum Spencer`_ created a Puppet module to install Puppetboard with:

* https://github.com/nibalizer/puppet-module-puppetboard

.. _Hunter Haugen: https://github.com/hunner
.. _Krum Spencer: https://github.com/nibalizer

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

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/node.png
   :alt: Node without experimental endpoints endabled
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/facts.png
   :alt: Facts view
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/nodes.png
   :alt: Nodes table without experimental endpoints enabled
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/overview.png
   :alt: Overview / Index / Homepage
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/query.png
   :alt: Query view
   :width: 1024
   :height: 700
   :align: center

With experimental endpoints
---------------------------

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/nodes-experimental.png
   :alt: Nodes table with experimental endpoints enabled
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/node-experimental.png
   :alt: Node view with experimental endpoints enabled
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/report.png
   :alt: Nodes table with experimental endpoints enabled
   :width: 1024
   :height: 700
   :align: center

Error page
----------

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/no-experimental.png
   :alt: Accessing disabled experimental feature
   :width: 1024
   :height: 700
   :align: center

.. image:: https://raw.github.com/nedap/puppetboard/master/screenshots/broken.png
   :alt: Error message
   :width: 1024
   :height: 700
   :align: center
