from __future__ import unicode_literals
from __future__ import absolute_import

from puppetboard.app import app

if __name__ == '__main__':
    app.debug=True
    app.run('127.0.0.1')
