from __future__ import unicode_literals
from __future__ import absolute_import
import os
import subprocess

if 'PUPPETBOARD_SETTINGS' not in os.environ:
    os.environ['PUPPETBOARD_SETTINGS'] = os.path.join(
        os.getcwd(), 'settings.py'
    )

from puppetboard.app import app

if __name__ == '__main__':
    # Start CoffeeScript to automatically compile our coffee source.
    # We must be careful to only start this in the parent process as
    # Werkzeug will create a secondary process when using the reloader.
    if os.environ.get('WERKZEUG_RUN_MAIN') is None:
        try:
            subprocess.Popen([
                app.config['DEV_COFFEE_LOCATION'], '-w', '-c',
                '-o', 'puppetboard/static/js',
                'puppetboard/static/coffeescript'
            ])
        except OSError:
            app.logger.error(
                'The coffee executable was not found, disabling automatic '
                'CoffeeScript compilation'
            )

    # Start the Flask development server
    app.debug = True
    app.run(app.config['DEV_LISTEN_HOST'], app.config['DEV_LISTEN_PORT'])
