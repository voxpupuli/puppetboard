from __future__ import absolute_import
from __future__ import unicode_literals

import json

from requests.exceptions import HTTPError, ConnectionError
from pypuppetdb.errors import EmptyResponseError

from flask import abort

def jsonprint(value):
  return json.dumps(value, indent=2, separators=(',', ': ') )


def get_or_abort(func, *args, **kwargs):
    """Execute the function with its arguments and handle the possible
    errors that might occur.

    In this case, if we get an exception we simply abort the request.
    """
    try:
        return func(*args, **kwargs)
    except HTTPError, e:
        abort(e.response.status_code)
    except ConnectionError:
        abort(500)
    except EmptyResponseError:
        abort(204)


def ten_reports(reports):
    """Helper to yield the first then reports from the reports generator.

    This is an ugly solution at best...
    """
    for count, report in enumerate(reports):
        if count == 10:
            raise StopIteration
        yield report


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
