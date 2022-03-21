from __future__ import absolute_import
from __future__ import unicode_literals

import logging
from datetime import datetime

from flask import render_template, Response

# these imports are required by Flask - DO NOT remove them although they look unused
# noinspection PyUnresolvedReferences
import puppetboard.views.catalogs  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.dailychart  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.facts  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.index  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.inventory  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.metrics  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.nodes  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.query  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.radiator  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.reports  # noqa: F401
# noinspection PyUnresolvedReferences
import puppetboard.views.failures  # noqa: F401


from puppetboard.core import get_app, get_puppetdb
from puppetboard.version import __version__

app = get_app()
puppetdb = get_puppetdb()

logging.basicConfig(level=app.config['LOGLEVEL'].upper())
log = logging.getLogger(__name__)


menu_entries = [
    ('index', 'Overview'),
    ('failures', 'Failures'),
    ('nodes', 'Nodes'),
    ('facts', 'Facts'),
    ('reports', 'Reports'),
    ('metrics', 'Metrics'),
    ('inventory', 'Inventory'),
    ('catalogs', 'Catalogs'),
    ('radiator', 'Radiator'),
    ('query', 'Query'),
]

if not app.config.get('ENABLE_QUERY'):
    menu_entries.remove(('query', 'Query'))

if not app.config.get('ENABLE_CATALOG'):
    menu_entries.remove(('catalogs', 'Catalogs'))


app.jinja_env.globals.update(menu_entries=menu_entries)


@app.context_processor
def utility_processor():
    def now(format='%m/%d/%Y %H:%M:%S'):
        """returns the formated datetime"""
        return datetime.now().strftime(format)

    def version():
        return __version__

    return dict(now=now, version=version)


@app.route('/offline/<path:filename>')
def offline_static(filename):
    mimetype = 'text/html'
    if filename.endswith('.css'):
        mimetype = 'text/css'
    elif filename.endswith('.js'):
        mimetype = 'text/javascript'

    return Response(response=render_template('static/%s' % filename),
                    status=200, mimetype=mimetype)


@app.route('/status')
def health_status():
    return 'OK'
