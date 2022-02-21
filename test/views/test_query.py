from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

from puppetboard import app
from test import MockHTTPResponse


def test_query_view(client, mocker,
                    mock_puppetdb_environments,
                    mock_puppetdb_default_nodes):
    rv = client.get('/query')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('h2', {"id": "results_header"})
    assert len(vals) == 0


def test_query__some_response(client, mocker,
                              mock_puppetdb_environments,
                              mock_puppetdb_default_nodes):
    app.app.config['WTF_CSRF_ENABLED'] = False

    query_data = [
        {'certname': 'foobar'},
    ]
    mocker.patch.object(app.puppetdb, '_query', return_value=query_data)

    data = {
        'query': 'nodes[certname] { certname = "foobar" }',
        'endpoints': 'pql',
    }
    rv = client.post(
        '/query',
        data=data,
        content_type='application/x-www-form-urlencoded',
    )

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('h2', {"id": "results_header"})
    assert len(vals) == 1

    vals = soup.find_all('p', {"id": "number_of_results"})
    assert len(vals) == 1
    assert str(len(query_data)) in vals[0].string


def test_query__empty_response(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    app.app.config['WTF_CSRF_ENABLED'] = False

    query_data = []
    mocker.patch.object(app.puppetdb, '_query', return_value=query_data)

    data = {
        'query': 'nodes { certname = "asdasdasdasdsad" }',
        'endpoints': 'pql',
    }
    rv = client.post(
        '/query',
        data=data,
        content_type='application/x-www-form-urlencoded',
    )

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('h2', {"id": "results_header"})
    assert len(vals) == 1

    vals = soup.find_all('p', {"id": "zero_results"})
    assert len(vals) == 1


def test_query__error_response(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    app.app.config['WTF_CSRF_ENABLED'] = False

    error_message = "Invalid query: (...)"
    puppetdb_response = HTTPError('Invalid query')
    puppetdb_response.response = MockHTTPResponse(400, error_message)
    mocker.patch.object(app.puppetdb, '_query', side_effect=puppetdb_response)

    data = {
        'query': 'foobar',
        'endpoints': 'pql',
    }
    rv = client.post(
        '/query',
        data=data,
        content_type='application/x-www-form-urlencoded',
    )

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('h2', {"id": "results_header"})
    assert len(vals) == 1

    vals = soup.find_all('pre', {"id": "invalid_query"})
    assert len(vals) == 1
    assert error_message in vals[0].string
