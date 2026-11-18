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
