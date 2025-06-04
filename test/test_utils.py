import json
import logging
from types import GeneratorType

import pytest
from pypuppetdb.errors import EmptyResponseError
from requests import Response
from requests.exceptions import ConnectionError, HTTPError
from werkzeug.exceptions import InternalServerError, NotFound

from puppetboard import app
from puppetboard import utils


def test_json_format():
    demo = [{'foo': 'bar'}, {'bar': 'foo'}]
    sample = json.dumps(demo, indent=2, separators=(',', ': '))
    assert sample == utils.jsonprint(demo), "Json formatting has changed"


def test_parse_python_array():
    python_array = [{'foo': 'bar'}, {'bar': 'foo'}]
    python_array_as_string = str(python_array)
    assert python_array == utils.parse_python(python_array_as_string)


def test_parse_python_not_really_array():
    # the downside of simplifying showing plain strings without quotes is that it's hard
    # to distinguish things that LOOK LIKE non-string but in fact are strings.
    python_not_really_array = '"["foo", "bar"]"'
    python_not_really_array_as_string = '"["foo", "bar"]"'
    assert python_not_really_array == utils.parse_python(python_not_really_array_as_string)


def test_parse_python_dict():
    python_dict = {'foo': 'bar'}
    python_dict_as_string = str(python_dict)
    assert python_dict == utils.parse_python(python_dict_as_string)


def test_parse_python_string():
    a_string = "foobar"
    assert a_string == utils.parse_python(a_string)


def test_format_val_str():
    x = "some string"
    assert x == utils.formatvalue(x), "Should return same value"


def test_format_val_array():
    x = ['a', 'b', 'c']
    assert "a, b, c" == utils.formatvalue(x)


def test_format_val_dict_one_layer():
    x = {'a': 'b'}
    assert "a => b,<br/>" == utils.formatvalue(x)


def test_format_val_tuple():
    x = ('a', 'b')
    assert str(x) == utils.formatvalue(x)


def test_get():
    x = "hello world"

    def test_get_or_abort():
        return x

    assert x == utils.get_or_abort(test_get_or_abort)


@pytest.fixture
def mock_log(mocker):
    return mocker.patch('logging.log')


@pytest.fixture
def mock_info_log(mocker):
    logger = logging.getLogger('puppetboard.utils')
    return mocker.patch.object(logger, 'info')


@pytest.fixture
def mock_err_log(mocker):
    logger = logging.getLogger('puppetboard.utils')
    return mocker.patch.object(logger, 'error')


def test_http_error(mock_log):
    err = "NotFound"

    def raise_http_error():
        x = Response()
        x.status_code = 404
        x.reason = err
        raise HTTPError(err, response=x)

    with pytest.raises(NotFound):
        utils.get_or_abort(raise_http_error)
        mock_log.error.assert_called_once_with(err)


def test_http_error_reraised_as_client_side(mock_log):
    err = "The request is invalid because ..."

    def raise_http_400_error():
        x = Response()
        x.status_code = 400
        x.reason = err
        raise HTTPError(err, response=x)

    with pytest.raises(HTTPError):
        utils.get_or_abort_except_client_errors(raise_http_400_error)
        mock_log.warning.assert_called_once_with(err)


def test_http_connection_error(mock_log):
    err = "ConnectionError"

    def connection_error():
        x = Response()
        x.status_code = 500
        x.reason = err
        raise ConnectionError(err, response=x)

    with pytest.raises(InternalServerError):
        utils.get_or_abort(connection_error)
        mock_log.error.assert_called_with(err)


def test_basic_exception(mock_log):
    err = "Exception"

    def exception_error():
        x = Response()
        x.reason = err
        raise Exception(err)

    with pytest.raises(Exception) as exception:
        utils.get_or_abort(exception_error())
        mock_log.error.assert_called_with(err)
        assert exception.status_code == 500


@pytest.mark.parametrize(
    "version,is_ok",
    [
        ("4.2.0", False),
        ("5.1.0", False),
        ("5.2.0", True),
        ("5.2.19", True),
        ("6.4.0", True),
        ("6.9.1", True),
        ("7.0.0", True),
        ("7.11.1-20220809_222149-g0b0b67c", True),
        ("8.0.0", True),
    ],
)
def test_db_version(mocker, version, is_ok):
    mocker.patch.object(app.puppetdb, "current_version", return_value=version)
    if is_ok:
        utils.check_db_version(app.puppetdb)
    else:
        with pytest.raises(SystemExit) as e:
            utils.check_db_version(app.puppetdb)
            assert e.code == 1


def test_db_invalid_version(mocker, mock_err_log):
    mocker.patch.object(app.puppetdb, 'current_version', return_value='4')
    with pytest.raises(SystemExit) as e:
        utils.check_db_version(app.puppetdb)
        assert e.code == 2


def test_db_http_error(mocker, mock_err_log):
    err = "NotFound"

    def raise_http_error():
        x = Response()
        x.status_code = 404
        x.reason = err
        raise HTTPError(err, response=x)

    mocker.patch.object(app.puppetdb, 'current_version',
                        side_effect=raise_http_error)
    with pytest.raises(SystemExit) as e:
        utils.check_db_version(app.puppetdb)
        assert e.code == 2


def test_db_connection_error(mocker, mock_err_log):
    err = "ConnectionError"

    def connection_error():
        x = Response()
        x.status_code = 500
        x.reason = err
        raise ConnectionError(err, response=x)

    mocker.patch.object(app.puppetdb, 'current_version',
                        side_effect=connection_error)
    with pytest.raises(SystemExit) as e:
        utils.check_db_version(app.puppetdb)
        assert e.code == 2


def test_db_empty_response(mocker, mock_err_log):
    err = "Empty Response"

    def connection_error():
        raise EmptyResponseError(err)

    mocker.patch.object(app.puppetdb, 'current_version',
                        side_effect=connection_error)
    with pytest.raises(SystemExit) as e:
        utils.check_db_version(app.puppetdb)
        assert e.code == 2


def test_iter():
    test_list = (0, 1, 2, 3)

    def my_generator():
        for element in test_list:
            yield element

    gen = utils.yield_or_stop(my_generator())
    assert isinstance(gen, GeneratorType)

    i = 0
    for val in gen:
        assert i == val
        i = i + 1


def test_stop_empty():
    def my_generator():
        yield 1
        raise EmptyResponseError

    gen = utils.yield_or_stop(my_generator())
    for val in gen:
        assert 1 == val


def test_stop_conn_error():
    def my_generator():
        yield 1
        raise ConnectionError

    gen = utils.yield_or_stop(my_generator())
    for val in gen:
        assert 1 == val


def test_stop_http_error():
    def my_generator():
        yield 1
        raise HTTPError

    gen = utils.yield_or_stop(my_generator())
    for val in gen:
        assert 1 == val


def test_quote_columns_data():
    quoted_with_dot = utils.quote_columns_data('foo.bar')
    assert quoted_with_dot == 'foo\\.bar'


@pytest.mark.parametrize(
    "lookup,expected",
    [
        ("os", {"distro": {"codename": "bullseye"}}),
        ("os.distro", {"codename": "bullseye"}),
        ("os.distro.codename", "bullseye"),
        ("oz", ""),
        ("oz.snooze", ""),
    ],
)
def test_dot_lookup(lookup, expected):
    os_fact = {
        "os": {
            "distro": {
                "codename": "bullseye",
            },
        }
    }
    assert utils.dot_lookup(os_fact, lookup) == expected
