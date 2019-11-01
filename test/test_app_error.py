import pytest
from bs4 import BeautifulSoup
from werkzeug.exceptions import InternalServerError

from puppetboard import app
from puppetboard.errors import (bad_request, forbidden, not_found,
                                precond_failed, server_error)


@pytest.fixture
def mock_puppetdb_environments(mocker):
    environemnts = [
        {'name': 'production'},
        {'name': 'staging'}
    ]

    return mocker.patch.object(app.puppetdb, 'environments',
                               return_value=environemnts)


@pytest.fixture
def mock_server_error(mocker):
    def raiseInternalServerError():
        raise InternalServerError('Hello world')

    return mocker.patch('puppetboard.core.environments',
                        side_effect=raiseInternalServerError)


def test_error_bad_request(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = bad_request(None)
        soup = BeautifulSoup(output, 'html.parser')

        assert 'The request sent to PuppetDB was invalid' in soup.p.text
        assert error_code == 400


def test_error_forbidden(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = forbidden(None)
        soup = BeautifulSoup(output, 'html.parser')

        long_string = "%s %s" % ('What you were looking for has',
                                 'been disabled by the administrator')
        assert long_string in soup.p.text
        assert error_code == 403


def test_error_not_found(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = not_found(None)
        soup = BeautifulSoup(output, 'html.parser')

        long_string = "%s %s" % ('What you were looking for could not',
                                 'be found in PuppetDB.')
        assert long_string in soup.p.text
        assert error_code == 404


def test_error_precond(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = precond_failed(None)
        soup = BeautifulSoup(output, 'html.parser')

        long_string = "%s %s" % ('You\'ve configured Puppetboard with an API',
                                 'version that does not support this feature.')
        assert long_string in soup.p.text
        assert error_code == 412


def test_error_server(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = server_error(None)
        soup = BeautifulSoup(output, 'html.parser')

        assert 'Internal Server Error' in soup.h2.text
        assert error_code == 500


def test_early_error_server(mock_server_error):
    with app.app.test_request_context():
        (output, error_code) = server_error(None)
        soup = BeautifulSoup(output, 'html.parser')
        assert 'Internal Server Error' in soup.h2.text
        assert error_code == 500
