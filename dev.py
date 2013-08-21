from __future__ import unicode_literals
from __future__ import absolute_import

from puppetboard.app import app
from puppetboard.default_settings import DEV_LISTEN, DEV_LISTEN_PORT

if __name__ == '__main__':
    app.debug=True
    app.run(DEV_LISTEN_HOST, DEV_LISTEN_PORT)
