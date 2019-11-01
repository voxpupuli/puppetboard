import json
import logging
from types import GeneratorType

import pytest
from bs4 import BeautifulSoup
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


def test_pretty_print():
    test_data = [{'hello': 'world'}]

    html = utils.prettyprint(test_data)
    soup = BeautifulSoup(html, 'html.parser')

    assert soup.th.text == 'hello'


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


def test_db_version_good(mocker, mock_info_log):
    mocker.patch.object(app.puppetdb, 'current_version', return_value='4.2.0')
    err = 'PuppetDB Version %d.%d.%d' % (4, 2, 0)
    result = utils.get_db_version(app.puppetdb)
    mock_info_log.assert_called_with(err)
    assert (4, 0, 0) < result
    assert (4, 2, 0) == result
    assert (3, 2, 0) < result
    assert (4, 3, 0) > result
    assert (5, 0, 0) > result
    assert (4, 2, 1) > result


def test_db_invalid_version(mocker, mock_err_log):
    mocker.patch.object(app.puppetdb, 'current_version', return_value='4')
    err = u"Unable to determine version from string: '%s'" % (4)
    result = utils.get_db_version(app.puppetdb)
    mock_err_log.assert_called_with(err)
    assert (4, 0, 0) < result
    assert (4, 2, 0) == result


def test_db_http_error(mocker, mock_err_log):
    err = "NotFound"

    def raise_http_error():
        x = Response()
        x.status_code = 404
        x.reason = err
        raise HTTPError(err, response=x)

    mocker.patch.object(app.puppetdb, 'current_version',
                        side_effect=raise_http_error)
    result = utils.get_db_version(app.puppetdb)
    mock_err_log.assert_called_with(err)
    assert result == ()


def test_db_connection_error(mocker, mock_err_log):
    err = "ConnectionError"

    def connection_error():
        x = Response()
        x.status_code = 500
        x.reason = err
        raise ConnectionError(err, response=x)

    mocker.patch.object(app.puppetdb, 'current_version',
                        side_effect=connection_error)
    result = utils.get_db_version(app.puppetdb)
    mock_err_log.assert_called_with(err)
    assert result == ()


def test_db_empty_response(mocker, mock_err_log):
    err = "Empty Response"

    def connection_error():
        raise EmptyResponseError(err)

    mocker.patch.object(app.puppetdb, 'current_version',
                        side_effect=connection_error)
    result = utils.get_db_version(app.puppetdb)
    mock_err_log.assert_called_with(err)
    assert result == ()


def test_iter():
    test_list = (0, 1, 2, 3)

    def my_generator():
        for i in test_list:
            yield i

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
        yield 2

    gen = utils.yield_or_stop(my_generator())
    for val in gen:
        assert 1 == val


def test_stop_conn_error():
    def my_generator():
        yield 1
        raise ConnectionError
        yield 2

    gen = utils.yield_or_stop(my_generator())
    for val in gen:
        assert 1 == val


def test_stop_http_error():
    def my_generator():
        yield 1
        raise HTTPError
        yield 2

    gen = utils.yield_or_stop(my_generator())
    for val in gen:
        assert 1 == val
