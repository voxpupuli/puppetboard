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


def test_query__some_response__table(client, mocker,
                                     mock_puppetdb_environments,
                                     mock_puppetdb_default_nodes):
    app.app.config['WTF_CSRF_ENABLED'] = False

    result = [
        {'certname': 'foobar', 'catalog_environment': 'qa'},
    ]
    mocker.patch.object(app.puppetdb, '_query', return_value=result)

    query_data = {
        'query': 'nodes[certname] { certname = "foobar" }',
        'endpoints': 'pql',
    }
    rv = client.post(
        '/query',
        data=query_data,
        content_type='application/x-www-form-urlencoded',
    )

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('h2', {"id": "results_header"})
    assert len(vals) == 1

    vals = soup.find_all('p', {"id": "number_of_results"})
    assert len(vals) == 1
    assert 'Number of results: 1' in vals[0].string

    vals = soup.find_all('table', {"id": "query_table"})
    assert len(vals) == 1
    # we can't test more here as the content of this table is generated with JavaScript...


def test_query__some_response__json(client, mocker,
                                    mock_puppetdb_environments,
                                    mock_puppetdb_default_nodes):
    app.app.config['WTF_CSRF_ENABLED'] = False

    result = [
        {'certname': 'foobar', 'catalog_environment': 'qa'},
    ]
    mocker.patch.object(app.puppetdb, '_query', return_value=result)

    query_data = {
        'query': 'nodes[certname] { certname = "foobar" }',
        'endpoints': 'pql',
        'rawjson': 'y',
    }
    rv = client.post(
        '/query',
        data=query_data,
        content_type='application/x-www-form-urlencoded',
    )

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('h2', {"id": "results_header"})
    assert len(vals) == 1

    vals = soup.find_all('p', {"id": "number_of_results"})
    assert len(vals) == 1
    assert 'Number of results: 1' in vals[0].string

    vals = soup.find_all('pre', {"id": "result"})
    assert len(vals) == 1
    # we can't test more here as the content of this tag is generated with JavaScript...


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
