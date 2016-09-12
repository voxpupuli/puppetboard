try:
    import unittest2 as unittest
except ImportError:
    import unittest

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


import logging


class UtilsTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def teadDown(self):
        pass

    def test_json_format(self):
        demo = [{'foo': 'bar'}, {'bar': 'foo'}]
        sample = json.dumps(demo, indent=2, separators=(',', ': '))

        self.assertEqual(sample, utils.jsonprint(demo),
                         "Json formatting has changed")

    def test_format_val_str(self):
        x = "some string"
        self.assertEqual(x, utils.formatvalue(x),
                         "Should return same value")

    def test_format_val_array(self):
        x = ['a', 'b', 'c']
        self.assertEqual("a, b, c", utils.formatvalue(x),
                         "Should return comma seperated string")

    def test_format_val_dict_one_layer(self):
        x = {'a': 'b'}
        self.assertEqual("a => b,<br/>", utils.formatvalue(x),
                         "Should return stringified value")

    def test_format_val_tuple(self):
        x = ('a', 'b')
        self.assertEqual(str(x), utils.formatvalue(x))


@mock.patch('logging.log')
class GetOrAbortTesting(unittest.TestCase):

    def test_get(self, mock_log):
        x = "hello world"

        def test_get_or_abort():
            return x

        self.assertEqual(x, utils.get_or_abort(test_get_or_abort))

    def test_http_error(self, mock_log):
        err = "NotFound"

        def raise_http_error():
            x = Response()
            x.status_code = 404
            x.reason = err
            raise HTTPError(err, response=x)

        with self.assertRaises(NotFound) as error:
            utils.get_or_abort(raise_http_error)
            mock_log.error.assert_called_with(err)

    def test_http_connection_error(self, mock_log):
        err = "ConnectionError"

        def connection_error():
            x = Response()
            x.status_code = 500
            x.reason = err
            raise ConnectionError(err, response=x)

        with self.assertRaises(InternalServerError) as error:
            utils.get_or_abort(connection_error)
            mock_log.error.assert_called_with(err)

    @mock.patch('flask.abort')
    def test_http_empty(self, mock_log, flask_abort):
        err = "Empty Response"

        def connection_error():
            raise EmptyResponseError(err)

        with self.assertRaises(NoContent) as error:
            utils.get_or_abort(connection_error)
            mock_log.error.assert_called_with(err)
            flask_abort.assert_called_with('204')


class yieldOrStop(unittest.TestCase):

    def test_iter(self):
        test_list = (0, 1, 2, 3)

        def my_generator():
            for i in test_list:
                yield i

        gen = utils.yield_or_stop(my_generator())
        self.assertIsInstance(gen, GeneratorType)

        i = 0
        for val in gen:
            self.assertEqual(i, val)
            i = i + 1

    def test_stop_empty(self):
        def my_generator():
            yield 1
            raise EmptyResponseError
            yield 2

        gen = utils.yield_or_stop(my_generator())
        for val in gen:
            self.assertEqual(1, val)

    def test_stop_conn_error(self):
        def my_generator():
            yield 1
            raise ConnectionError
            yield 2

        gen = utils.yield_or_stop(my_generator())
        for val in gen:
            self.assertEqual(1, val)

    def test_stop_http_error(self):
        def my_generator():
            yield 1
            raise HTTPError
            yield 2

        gen = utils.yield_or_stop(my_generator())
        for val in gen:
            self.assertEqual(1, val)


if __name__ == '__main__':
    unittest.main()
