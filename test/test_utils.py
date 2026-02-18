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


def test_flatten_fact_simple():
    """Test flattening a simple non-dict fact"""
    result = utils.flatten_fact('hostname', 'server01')
    assert result == {'hostname': 'server01'}


def test_flatten_fact_dict():
    """Test flattening a structured fact"""
    os_fact = {
        'name': 'Ubuntu',
        'release': {
            'full': '20.04',
            'major': '20'
        }
    }
    result = utils.flatten_fact('os', os_fact)
    # flatten_fact now includes intermediate dict nodes for nested collapsible support
    expected = {
        'os': os_fact,  # Root dict node
        'os.name': 'Ubuntu',
        'os.release': {'full': '20.04', 'major': '20'},  # Intermediate dict node
        'os.release.full': '20.04',
        'os.release.major': '20'
    }
    assert result == expected


def test_flatten_fact_nested_deep():
    """Test flattening deeply nested fact"""
    fact_value = {
        'a': {
            'b': {
                'c': 'value'
            }
        }
    }
    result = utils.flatten_fact('root', fact_value)
    # flatten_fact now includes intermediate dict nodes for nested collapsible support
    expected = {
        'root': fact_value,
        'root.a': {'b': {'c': 'value'}},
        'root.a.b': {'c': 'value'},
        'root.a.b.c': 'value'
    }
    assert result == expected


def test_flatten_fact_with_list():
    """Test flattening a fact containing a list"""
    fact_value = {
        'interfaces': ['eth0', 'eth1'],
        'primary': 'eth0'
    }
    result = utils.flatten_fact('network', fact_value)
    # flatten_fact now includes intermediate dict nodes for nested collapsible support
    expected = {
        'network': fact_value,  # Root dict node
        'network.interfaces': ['eth0', 'eth1'],
        'network.primary': 'eth0'
    }
    assert result == expected


def test_flatten_fact_skips_keys_with_slashes():
    """Test that keys containing slashes are skipped to avoid URL routing issues"""
    mountpoints_fact = {
        '/': {'size': '100G', 'filesystem': 'ext4'},
        '/opt/nomad/alloc/abc-123/private': {'size': '10G', 'filesystem': 'tmpfs'},
        '/home': {'size': '500G', 'filesystem': 'ext4'},
        'valid_key': {'size': '50G'}
    }
    result = utils.flatten_fact('mountpoints', mountpoints_fact)
    # Only the valid_key should be included (no slashes)
    # Keys with slashes (/, /opt/..., /home) should be skipped
    # Root dict node is also included
    expected = {
        'mountpoints': mountpoints_fact,  # Root dict node
        'mountpoints.valid_key': {'size': '50G'},  # Intermediate dict node
        'mountpoints.valid_key.size': '50G'
    }
    assert result == expected


def test_flatten_fact_skips_keys_with_dots():
    """Test that keys containing dots are skipped to avoid path ambiguity"""
    myco_services_fact = {
        'MYCO.FictionalService': {
            'state': 'Running',
            'pathname': 'C:\\Program Files\\Myco\\MYCO.FictionalService\\FictionalService.exe',
            'startmode': 'Auto'
        },
        'ValidServiceName': {
            'state': 'Stopped'
        }
    }
    result = utils.flatten_fact('myco_services', myco_services_fact)
    # Only ValidServiceName should be included (no dots in key)
    # MYCO_FictionalService should be skipped (dot in key causes ambiguity)
    # Root dict node is also included
    expected = {
        'myco_services': myco_services_fact,  # Root dict node
        'myco_services.ValidServiceName': {'state': 'Stopped'},  # Intermediate dict node
        'myco_services.ValidServiceName.state': 'Stopped'
    }
    assert result == expected


def test_get_all_fact_paths_simple():
    """Test getting paths from simple facts"""
    facts = {
        'hostname': 'server01',
        'kernel': 'Linux'
    }
    result = utils.get_all_fact_paths(facts)
    assert result == ['hostname', 'kernel']


def test_get_all_fact_paths_structured():
    """Test getting paths from structured facts"""
    facts = {
        'hostname': 'server01',
        'os': {
            'name': 'Ubuntu',
            'release': {
                'full': '20.04',
                'major': '20'
            }
        }
    }
    result = utils.get_all_fact_paths(facts)
    # Now includes intermediate dict nodes for nested collapsible support
    expected = ['hostname', 'os', 'os.name', 'os.release', 'os.release.full', 'os.release.major']
    assert result == expected


def test_get_all_fact_paths_mixed():
    """Test getting paths from mixed simple and structured facts"""
    facts = {
        'kernel': 'Linux',
        'os': {
            'name': 'Ubuntu'
        },
        'uptime': '30 days'
    }
    result = utils.get_all_fact_paths(facts)
    assert 'kernel' in result
    assert 'os' in result  # Intermediate dict node
    assert 'os.name' in result
    assert 'uptime' in result
    assert len(result) == 4  # Now includes 'os' intermediate node


def test_split_fact_path_simple():
    """Test splitting a simple fact path"""
    base, sub = utils.split_fact_path('hostname')
    assert base == 'hostname'
    assert sub is None


def test_split_fact_path_structured():
    """Test splitting a structured fact path"""
    base, sub = utils.split_fact_path('os.release.full')
    assert base == 'os'
    assert sub == 'release.full'


def test_split_fact_path_single_level():
    """Test splitting a single-level structured fact"""
    base, sub = utils.split_fact_path('os.name')
    assert base == 'os'
    assert sub == 'name'
