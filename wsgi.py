from __future__ import absolute_import

import os
import sys

me = os.path.dirname(os.path.abspath(__file__))
# Add us to the PYTHONPATH/sys.path if we're not on it
if not me in sys.path:
    sys.path.insert(0, me)

from puppetboard.app import app as application
