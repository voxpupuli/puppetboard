import ast
import json
import logging
import sys
from typing import Any

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
    return json.dumps(value, indent=2, separators=(",", ": "))


def check_db_version(puppetdb):
    """
    Gets the version of puppetdb and exits if it is not an accepted one.
    """
    try:
        current_version = puppetdb.current_version()
        log.info(f"PuppetDB version: {current_version}")

        current_semver = current_version.split("-")[0]
        minimum_semver = "5.2.0"

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
    if not secret_key_value:
        log.critical('Please set SECRET_KEY to a long, random string,'
                     ' **the same for each application replica**,'
                     ' and do not share it.')
        sys.exit(1)


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
    """Perform a backend request and handle all the errors,"""
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
    return data.replace(".", "\\.")


def check_env(env: str, envs: dict):
    if env != "*" and env not in envs:
        abort(404)


def is_a_test():
    running_in_shell = any(
        pytest_binary in sys.argv[0] for pytest_binary in ["pytest", "py.test"]
    )
    running_in_intellij = any("_jb_pytest_runner.py" in arg for arg in sys.argv)
    return running_in_shell or running_in_intellij


def dot_lookup(_dict: dict[str, Any], lookup: str) -> str | dict | None:
    """Recursively look up a value in a dictionary using dot notation string"""
    lookup_parts = lookup.split(".")
    if not lookup_parts:
        return None

    key = lookup_parts[0]
    if len(lookup_parts) == 1:
        return _dict.get(key, "")

    return dot_lookup(_dict.get(key, {}), ".".join(lookup_parts[1:]))


def flatten_fact(fact_name: str, fact_value: Any, prefix: str = "") -> dict[str, Any]:
    """
    Recursively flatten a structured fact into dot-notation paths.

    Skips dict keys containing dots or forward slashes to avoid ambiguity and
    URL routing conflicts. Keys with these characters cannot be reliably used in
    dot-notation paths since dots are the structural separator and slashes cause
    URL routing issues.

    Facts with problematic keys (like mountpoints with '/' or myco_services with '.')
    will only show the parent fact in the facts list. Users can click the parent
    to view the full JSON.

    :param fact_name: The name of the fact
    :param fact_value: The value of the fact (can be dict, list, or scalar)
    :param prefix: Internal prefix for recursion
    :return: Dictionary mapping dot-notation paths to their values
    """
    result = {}
    current_path = f"{prefix}.{fact_name}" if prefix else fact_name

    if isinstance(fact_value, dict):
        # For dictionaries, add the path itself (for nested collapsible support)
        # AND recursively flatten each key
        result[current_path] = fact_value

        for key, value in fact_value.items():
            key_str = str(key)
            # Skip keys with dots (ambiguous with path separator) or slashes (URL routing issues)
            # Dots: 'MYCO.FictionalServic' would be ambiguous in 'myco_services.MYCO.FictionalService.state'
            # Slashes: '/opt/nomad' causes Flask routing conflicts (see https://github.com/pallets/flask/issues/900)
            if '.' not in key_str and '/' not in key_str:
                result.update(flatten_fact(key, value, current_path))
    else:
        # For non-dict values (including lists), store as-is
        result[current_path] = fact_value

    return result


def get_all_fact_paths(facts_dict: dict[str, Any]) -> list[str]:
    """
    Get all possible dot-notation paths from a dictionary of facts.

    :param facts_dict: Dictionary of fact names to fact values
    :return: Sorted list of all fact paths (both top-level and nested)
    """
    all_paths: list[str] = []

    for fact_name, fact_value in facts_dict.items():
        if isinstance(fact_value, dict):
            # Add structured paths
            flattened = flatten_fact(fact_name, fact_value)
            all_paths.extend(flattened.keys())
        else:
            # Add simple fact name
            all_paths.append(fact_name)

    return sorted(all_paths)


def split_fact_path(fact_path: str) -> tuple[str, str | None]:
    """
    Split a dot-notation fact path into base fact name and sub-path.

    :param fact_path: Fact path like 'os.release.full' or 'hostname'
    :return: Tuple of (base_fact_name, sub_path) e.g. ('os', 'release.full') or ('hostname', None)
    """
    parts = fact_path.split(".", 1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]
