from bs4 import BeautifulSoup

from puppetboard import app
from test import MockDbQuery


def test_get_index(client, mocker,
                   mock_puppetdb_environments,
                   mock_puppetdb_default_nodes):
    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/')
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    assert rv.status_code == 200


def test_index_all(client, mocker,
                   mock_puppetdb_environments,
                   mock_puppetdb_default_nodes):
    # starting with v6.9.1 they changed the metric API to v2
    # and a totally different format
    base_str = 'puppetlabs.puppetdb.population:'
    query_data = {
        'version': [{'version': '6.9.1'}],
        'metrics': [
            {
                'validate': {
                    'data': {
                        'value': {'Value': 10}
                    },
                    'checks': {
                        'path': '%sname=num-nodes' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {
                        'value': {'Value': 63}
                    },
                    'checks': {
                        'path': '%sname=num-resources' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {
                        'value': {'Value': 6.3}
                    },
                    'checks': {
                        'path': '%sname=avg-resources-per-node' % base_str
                    }
                }
            }
        ]
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
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


def test_index_all_puppetdb_v4(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    base_str = 'puppetlabs.puppetdb.population:'
    query_data = {
        'version': [{'version': '4.2.0'}],
        'mbean': [
            {
                'validate': {
                    'data': {'Value': 10},
                    'checks': {
                        'path': '%sname=num-nodes' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {'Value': 63},
                    'checks': {
                        'path': '%sname=num-resources' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {'Value': 6.3},
                    'checks': {
                        'path': '%sname=avg-resources-per-node' % base_str
                    }
                }
            }
        ]
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
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


def test_index_all_puppetdb_v3(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    base_str = 'puppetlabs.puppetdb.population:type=default,'
    query_data = {
        'version': [{'version': '3.2.0'}],
        'mbean': [
            {
                'validate': {
                    'data': {'Value': 10},
                    'checks': {
                        'path': '%sname=num-nodes' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {'Value': 60},
                    'checks': {
                        'path': '%sname=num-resources' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {'Value': 6.3},
                    'checks': {
                        'path': '%sname=avg-resources-per-node' % base_str
                    }
                }
            }
        ]
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/%2A/')

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    vals = soup.find_all('h1',
                         {"class": "ui header darkblue no-margin-bottom"})

    assert len(vals) == 3
    assert vals[0].string == '10'
    assert vals[1].string == '60'
    assert vals[2].string == '         6'

    assert rv.status_code == 200


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
