import pytest
import sys
import json
import mock

from types import GeneratorType

from requests.exceptions import HTTPError, ConnectionError
from pypuppetdb.errors import EmptyResponseError
from requests import Response
from werkzeug.exceptions import NotFound, InternalServerError

from puppetboard import utils
from puppetboard import app
from puppetboard.app import NoContent

from bs4 import BeautifulSoup
import logging


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


def test_http_empty(mock_log, mocker):
    err = "Empty Response"

    def connection_error():
        raise EmptyResponseError(err)

    flask_abort = mocker.patch('flask.abort')
    with pytest.raises(NoContent):
        utils.get_or_abort(connection_error)
        mock_log.error.assert_called_with(err)
        flask_abort.assert_called_with('204')


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
