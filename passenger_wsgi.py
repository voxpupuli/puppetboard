from __future__ import absolute_import

import os
import sys
import logging

me = os.path.dirname(os.path.abspath(__file__))
# Add us to the PYTHONPATH/sys.path if we're not on it
if not me in sys.path:
    sys.path.insert(0, me)

logfilename = os.path.join('/tmp/', 'puppetboard_passenger_wsgi.log')
# configure the logging
logging.basicConfig(filename=logfilename, level=logging.INFO)

try:
    from puppetboard.app import app as application
except Exception, inst:
    logging.exception("Error: %s", str(type(inst)))
