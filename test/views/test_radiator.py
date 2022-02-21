import json

from bs4 import BeautifulSoup

from puppetboard import app
from test import MockDbQuery


def test_radiator_view(client, mocker,
                       mock_puppetdb_environments,
                       mock_puppetdb_default_nodes):
    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/radiator')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    assert soup.h1 != 'Not Found'
    total = soup.find(class_='total')

    assert '10' in total.text


def test_radiator_view_all(client, mocker,
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
                        'value': {'Value': '50'}
                    },
                    'checks': {
                        'path': '%sname=num-nodes' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {
                        'value': {'Value': '60'}
                    },
                    'checks': {
                        'path': '%sname=num-resources' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {
                        'value': {'Value': 60.3}
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

    rv = client.get('/%2A/radiator')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    assert soup.h1 != 'Not Found'
    total = soup.find(class_='total')

    assert '50' in total.text


def test_radiator_view_all_v4(client, mocker,
                              mock_puppetdb_environments,
                              mock_puppetdb_default_nodes):
    base_str = 'puppetlabs.puppetdb.population:'
    query_data = {
        'version': [{'version': '4.2.0'}],
        'mbean': [
            {
                'validate': {
                    'data': {'Value': '50'},
                    'checks': {
                        'path': '%sname=num-nodes' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {'Value': '60'},
                    'checks': {
                        'path': '%sname=num-resources' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {'Value': 60.3},
                    'checks': {
                        'path': '%sname=avg-resources-per-node' % base_str
                    }
                }
            }
        ]
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/%2A/radiator')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    assert soup.h1 != 'Not Found'
    total = soup.find(class_='total')

    assert '50' in total.text


def test_radiator_view_all_v3(client, mocker,
                              mock_puppetdb_environments,
                              mock_puppetdb_default_nodes):
    base_str = 'puppetlabs.puppetdb.population:type=default,'
    query_data = {
        'version': [{'version': '3.2.0'}],
        'mbean': [
            {
                'validate': {
                    'data': {'Value': '50'},
                    'checks': {
                        'path': '%sname=num-nodes' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {'Value': '60'},
                    'checks': {
                        'path': '%sname=num-resources' % base_str
                    }
                }
            },
            {
                'validate': {
                    'data': {'Value': 60.3},
                    'checks': {
                        'path': '%sname=avg-resources-per-node' % base_str
                    }
                }
            }
        ]
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/%2A/radiator')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    assert soup.h1 != 'Not Found'
    total = soup.find(class_='total')

    assert '50' in total.text


def test_radiator_view_json(client, mocker,
                            mock_puppetdb_environments,
                            mock_puppetdb_default_nodes):
    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/radiator', headers={'Accept': 'application/json'})

    assert rv.status_code == 200
    json_data = json.loads(rv.data.decode('utf-8'))

    assert json_data['unreported'] == 1
    assert json_data['noop'] == 1
    assert json_data['failed'] == 1
    assert json_data['changed'] == 1
    assert json_data['unchanged'] == 1


def test_radiator_view_bad_env(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/nothere/radiator')

    assert rv.status_code == 404
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    assert soup.h1.text == 'Not Found'


def test_radiator_view_division_by_zero(client, mocker,
                                        mock_puppetdb_environments,
                                        mock_puppetdb_default_nodes):
    query_data = {
        'nodes': [[{'count': 0}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/radiator')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    total = soup.find(class_='total')
    assert '0' in total.text
