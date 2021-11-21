import ast
import json
import logging

from flask import abort
from pypuppetdb.errors import EmptyResponseError
from requests.exceptions import ConnectionError, HTTPError

from puppetboard.app import app
from puppetboard.core import get_puppetdb

numeric_level = getattr(logging, app.config['LOGLEVEL'].upper(), None)
logging.basicConfig(level=numeric_level)
log = logging.getLogger(__name__)


def jsonprint(value):
    return json.dumps(value, indent=2, separators=(',', ': '))


def get_db_version(puppetdb):
    """
    Get the version of puppetdb.  Version form 3.2 query
    interface is slightly different on mbeans
    """
    ver = ()
    try:
        version = puppetdb.current_version()
        (major, minor, build) = [int(x) for x in version.split('.')]
        ver = (major, minor, build)
        log.info("PuppetDB Version %d.%d.%d" % (major, minor, build))
    except ValueError:
        log.error("Unable to determine version from string: '%s'" % puppetdb.current_version())
        ver = (4, 2, 0)
    except HTTPError as e:
        log.error(str(e))
    except ConnectionError as e:
        log.error(str(e))
    except EmptyResponseError as e:
        log.error(str(e))
    return ver


def parse_python(value: str):
    """
    :param value: any string, number, bool, list or a dict
                  casted to a string (f.e. "{'up': ['eth0'], (...)}")
    :return: the same value but with a proper type
    """
    try:
        return ast.literal_eval(value)
    except ValueError:
        return str(value)
    except SyntaxError:
        return str(value)


def formatvalue(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, list):
        return ", ".join(map(formatvalue, value))
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
    return html


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
    except Exception as e:
        log.error(str(e))
        abort(500)


def yield_or_stop(generator):
    """Similar in intent to get_or_abort this helper will iterate over our
    generators and handle certain errors.

    Since this is also used in streaming responses where we can't just abort
    a request we raise StopIteration.
    """
    while True:
        try:
            yield next(generator)
        except (EmptyResponseError, ConnectionError, HTTPError, StopIteration):
            return


def environments():
    puppetdb = get_puppetdb()
    envs = get_or_abort(puppetdb.environments)
    x = []

    for env in envs:
        x.append(env['name'])

    return x
