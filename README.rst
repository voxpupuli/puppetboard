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

.. image:: https://www.dropbox.com/s/5dzocpvsl7uoub7/node-experimental.png

Word of caution
===============

Puppetboard is very, very young, it's less than a week's worth of
efforts but it works fairly well.

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

.. image:: https://www.dropbox.com/s/lnueotxs6m4c3xk/broken.png
.. image:: https://www.dropbox.com/s/z4tyme9yw9dqy48/facts.png
.. image:: https://www.dropbox.com/s/r3l8uum74h91j1e/no-experimental.png
.. image:: https://www.dropbox.com/s/jy1rrcm3rf3vazg/node.png
.. image:: https://www.dropbox.com/s/bh0h95rgegavung/nodes.png
.. image:: https://www.dropbox.com/s/yeqs0j1rgpvxcvo/overview.png
.. image:: https://www.dropbox.com/s/61tfrvkkst2im2v/query.png

With experimental endpoints
---------------------------

.. image:: https://www.dropbox.com/s/4d67108n8fenobb/nodes-experimental.png
.. image:: https://www.dropbox.com/s/5dzocpvsl7uoub7/node-experimental.png
