import ast
import json
import logging
import sys

from flask import abort, request, url_for
from packaging.version import parse
from pypuppetdb.errors import EmptyResponseError
from requests.exceptions import ConnectionError, HTTPError

log = logging.getLogger(__name__)


def url_for_field(field, value):
    args = request.view_args.copy()
    args.update(request.args.copy())
    args[field] = value
    return url_for(request.endpoint, **args)


def jsonprint(value):
    return json.dumps(value, indent=2, separators=(',', ': '))


def check_db_version(puppetdb):
    """
    Gets the version of puppetdb and exits if it is not an accepted one.
    """
    try:
        current_version = puppetdb.current_version()
        log.info(f"PuppetDB version: {current_version}")

        current_semver = current_version.split('-')[0]
        minimum_semver = '5.2.0'

        if parse(current_semver) < parse(minimum_semver):
            log.error(f"The minimum supported version of PuppetDB is {minimum_semver}")
            sys.exit(1)

    except HTTPError as e:
        log.error(str(e))
        sys.exit(2)
    except ConnectionError as e:
        log.error(str(e))
        sys.exit(2)
    except EmptyResponseError as e:
        log.error(str(e))
        sys.exit(2)


def check_secret_key(secret_key_value):
    """
    Check if the secret key value is set to a default value, that will stop
    being accepted in v5.x of the app.
    """

    # Flask's SECRET_KEY can be bytes or string, but for the check below
    # we need it to be a string
    if type(secret_key_value) is bytes:
        secret_key_value = secret_key_value.decode("utf-8")

    if secret_key_value.startswith("default-"):
        log.warning(
            "Leaving SECRET_KEY set to a default value WILL cause issues"
            " when the app is restarted or has more than 1 replica"
            " (f.e. uWSGI workers, k8s replicas etc.) and some features"
            " (in particular: queries) are used.\n"
            "Please set SECRET_KEY to your own value, the same for all app"
            " replicas.\n"
            "This will be REQUIRED starting with Puppetboard 5.x which"
            " will NOT contain the default value anymore.\n"
            "Please see"
            " https://github.com/voxpupuli/puppetboard/issues/721"
            " for more info."
            )


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


def get_or_abort(func, *args, **kwargs):
    """Perform a backend request and handle all the errors,
    """
    return _do_get_or_abort(False, func, *args, **kwargs)


def get_or_abort_except_client_errors(func, *args, **kwargs):
    """Perform a backend request and handle the errors,
    but with a chance to react to client errors (HTTP 400-499).
    """
    return _do_get_or_abort(True, func, *args, **kwargs)


def _do_get_or_abort(reraise_client_error: bool, func, *args, **kwargs):
    """Execute the function with its arguments and handle the possible
    errors that might occur.

    If reraise_client_error is True then if the HTTP response status code
    indicates that it was a client side error - then re-raise it.

    In all other cases if we get an exception we simply abort the request.
    """
    try:
        return func(*args, **kwargs)
    except HTTPError as e:
        if reraise_client_error and 400 <= e.response.status_code <= 499:
            # it's a client side error, so reraise it to show the user
            log.warning(str(e))
            raise
        else:
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


def quote_columns_data(data: str) -> str:
    """When projecting Queries using dot notation (f.e. inventory [ facts.osfamily ])
    we need to quote the dot in such column name for the DataTables library or it will
    interpret the dot a way to get into a nested results object.

    See https://datatables.net/reference/option/columns.data#Types."""
    return data.replace('.', '\\.')


def check_env(env: str, envs: dict):
    if env != '*' and env not in envs:
        abort(404)


def is_a_test():
    running_in_shell = any(
        pytest_binary in sys.argv[0] for pytest_binary in ['pytest', 'py.test']
    )
    running_in_intellij = any(
        '_jb_pytest_runner.py' in arg for arg in sys.argv
    )
    return running_in_shell or running_in_intellij
