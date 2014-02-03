from __future__ import unicode_literals
from __future__ import absolute_import
import os

if 'PUPPETBOARD_SETTINGS' not in os.environ:
    os.environ['PUPPETBOARD_SETTINGS'] = os.path.join(
        os.getcwd(), 'settings.py'
    )

from puppetboard.app import app
from puppetboard.default_settings import DEV_LISTEN_HOST, DEV_LISTEN_PORT

if __name__ == '__main__':
    app.debug = True
    app.run(DEV_LISTEN_HOST, DEV_LISTEN_PORT)
