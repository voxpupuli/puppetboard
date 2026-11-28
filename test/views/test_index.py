from bs4 import BeautifulSoup
from pypuppetdb.QueryBuilder import EqualsOperator

from puppetboard import app
from test import MockDbQuery

COUNT = '["extract", [["function", "count"]]'


def count_queries(query_mock):
    return {c.args[0]: str(c.kwargs['query'])
            for c in query_mock.call_args_list}


def test_get_index(client, mocker,
                   mock_puppetdb_environments,
                   mock_puppetdb_default_nodes):
    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    query_mock = mocker.patch.object(app.puppetdb, '_query',
                                     side_effect=dbquery.get)
    rv = client.get('/')
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    assert rv.status_code == 200

    assert count_queries(query_mock) == {
        'nodes': COUNT + ', ["and", ["=", "catalog_environment", "production"]]]',
        'resources': COUNT + ', ["=", "environment", "production"]]',
    }


def test_index_all(client, mocker,
                   mock_puppetdb_environments,
                   mock_puppetdb_default_nodes):
    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 63}]],
    }
    dbquery = MockDbQuery(query_data)
    query_mock = mocker.patch.object(app.puppetdb, '_query',
                                     side_effect=dbquery.get)
    rv = client.get('/%2A/')

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    vals = soup.find_all('h1',
                         {"class": "ui header darkblue no-margin-bottom"})

    assert len(vals) == 3
    assert vals[0].string == '10'
    assert vals[1].string == '63'
    assert vals[2].string == '         6'

    assert rv.status_code == 200

    assert count_queries(query_mock) == {
        'nodes': COUNT + ']',
        'resources': COUNT + ']',
    }


def test_index_all_overview_filter(client, mocker,
                                   mock_puppetdb_environments,
                                   mock_puppetdb_default_nodes):
    overview_filter = EqualsOperator('certname', 'node-failed')
    mocker.patch.dict(app.app.config, {'OVERVIEW_FILTER': overview_filter})
    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 63}]],
    }
    dbquery = MockDbQuery(query_data)
    query_mock = mocker.patch.object(app.puppetdb, '_query',
                                     side_effect=dbquery.get)
    rv = client.get('/%2A/')

    assert rv.status_code == 200
    # the filter limits the node list but not the totals
    assert mock_puppetdb_default_nodes.call_args.kwargs['query'] is overview_filter
    assert count_queries(query_mock) == {
        'nodes': COUNT + ']',
        'resources': COUNT + ']',
    }


def test_index_division_by_zero(client, mocker,
                                mock_puppetdb_environments,
                                mock_puppetdb_default_nodes):
    query_data = {
        'nodes': [[{'count': 0}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('h1',
                         {"class": "ui header darkblue no-margin-bottom"})
    assert len(vals) == 3
    assert vals[2].string == '0'


def test_index_environment_column_hidden(client, mocker,
                                         mock_puppetdb_environments,
                                         mock_puppetdb_default_nodes):
    mocker.patch.object(app.puppetdb, '_query', return_value=[{'count': 10}])

    rv = client.get('/')

    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    table = soup.find(id='main-table')
    headers = [th.text for th in table.find_all('th')]
    assert 'Environment' not in headers
    assert table['data-order'] == '[[ 2, "desc" ]]'


def test_index_all_environment_column(client, mocker,
                                      mock_puppetdb_environments,
                                      mock_puppetdb_default_nodes):
    # totals are not under test, so mock both ways they can be fetched
    mocker.patch.object(app.puppetdb, 'metric', return_value={'Value': 10})
    mocker.patch.object(app.puppetdb, '_query', return_value=[{'count': 10}])

    rv = client.get('/%2A/')

    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    table = soup.find(id='main-table')
    headers = [th.text for th in table.find_all('th')]
    assert headers.index('Environment') == 2
    assert table['data-order'] == '[[ 3, "desc" ]]'
    cells = table.tbody.find('tr').find_all('td')
    assert cells[2].text == 'production'
