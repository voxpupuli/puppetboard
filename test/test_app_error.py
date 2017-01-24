import pytest
from flask import Flask, current_app
from puppetboard import app

from bs4 import BeautifulSoup


@pytest.fixture
def mock_puppetdb_environments(mocker):
    environemnts = [
        {'name': 'production'},
        {'name': 'staging'}
    ]

    return mocker.patch.object(app.puppetdb, 'environments',
                               return_value=environemnts)


def test_error_no_content():
    result = app.no_content(None)
    assert result[0] == ''
    assert result[1] == 204


def test_error_bad_request(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = app.bad_request(None)
        soup = BeautifulSoup(output, 'html.parser')

        assert 'The request sent to PuppetDB was invalid' in soup.p.text
        assert error_code == 400


def test_error_forbidden(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = app.forbidden(None)
        soup = BeautifulSoup(output, 'html.parser')

        long_string = "%s %s" % ('What you were looking for has',
                                 'been disabled by the administrator')
        assert long_string in soup.p.text
        assert error_code == 403


def test_error_not_found(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = app.not_found(None)
        soup = BeautifulSoup(output, 'html.parser')

        long_string = "%s %s" % ('What you were looking for could not',
                                 'be found in PuppetDB.')
        assert long_string in soup.p.text
        assert error_code == 404


def test_error_precond(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = app.precond_failed(None)
        soup = BeautifulSoup(output, 'html.parser')

        long_string = "%s %s" % ('You\'ve configured Puppetboard with an API',
                                 'version that does not support this feature.')
        assert long_string in soup.p.text
        assert error_code == 412


def test_error_server(mock_puppetdb_environments):
    with app.app.test_request_context():
        (output, error_code) = app.server_error(None)
        soup = BeautifulSoup(output, 'html.parser')

        assert 'Internal Server Error' in soup.h2.text
        assert error_code == 500
