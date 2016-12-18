from __future__ import absolute_import
from __future__ import unicode_literals

import json
import logging

from math import ceil
from requests.exceptions import HTTPError, ConnectionError
from pypuppetdb.errors import EmptyResponseError

from flask import abort


# Python 3 compatibility
try:
    xrange
except NameError:
    xrange = range

log = logging.getLogger(__name__)


def jsonprint(value):
    return json.dumps(value, indent=2, separators=(',', ': '))


def formatvalue(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, list):
        return ", ".join(value)
    elif isinstance(value, dict):
        ret = ""
        for k in value:
            ret += k + " => " + formatvalue(value[k]) + ",<br/>"
        return ret
    else:
        return str(value)


def prettyprint(value):
    html = '<table class="ui basic fixed sortable table"><thead><tr>'

    # Get keys
    for k in value[0]:
        html += "<th>" + k + "</th>"

    html += "</tr></thead><tbody>"

    for e in value:
        html += "<tr>"
        for k in e:
            html += "<td>" + formatvalue(e[k]) + "</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return(html)


def get_or_abort(func, *args, **kwargs):
    """Execute the function with its arguments and handle the possible
    errors that might occur.

    In this case, if we get an exception we simply abort the request.
    """
    try:
        return func(*args, **kwargs)
    except HTTPError as e:
        log.error(str(e))
        abort(e.response.status_code)
    except ConnectionError as e:
        log.error(str(e))
        abort(500)
    except EmptyResponseError as e:
        log.error(str(e))
        abort(204)


def yield_or_stop(generator):
    """Similar in intent to get_or_abort this helper will iterate over our
    generators and handle certain errors.

    Since this is also used in streaming responses where we can't just abort
    a request we raise StopIteration.
    """
    while True:
        try:
            yield next(generator)
        except StopIteration:
            raise
        except (EmptyResponseError, ConnectionError, HTTPError):
            raise StopIteration
