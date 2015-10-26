from __future__ import absolute_import
from __future__ import unicode_literals

import json

from requests.exceptions import HTTPError, ConnectionError
from pypuppetdb.errors import EmptyResponseError

from flask import abort


def jsonprint(value):
    return json.dumps(value, indent=2, separators=(',', ': '))


def get_or_abort(func, *args, **kwargs):
    """Execute the function with its arguments and handle the possible
    errors that might occur.

    In this case, if we get an exception we simply abort the request.
    """
    try:
        return func(*args, **kwargs)
    except HTTPError as e:
        abort(e.response.status_code)
    except ConnectionError:
        abort(500)
    except EmptyResponseError:
        abort(204)


def limit_reports(reports, limit, events_hash):
    """Helper to yield a number of from the reports generator.

    If events_hash has any hash, then returns only those reports that
    have associated events.

    This is an ugly solution at best...
    """
    if not events_hash:
        for count, report in enumerate(reports):
            if count == limit:
                raise StopIteration
            yield report
    else:
        count = 0
        for report in reports:
            if report.hash_ not in events_hash:
                continue
            else:
                count += 1
            if count == limit:
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
