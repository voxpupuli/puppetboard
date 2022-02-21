import json

from bs4 import BeautifulSoup

from puppetboard import app
from test import MockDbQuery


def test_facts_view(client, mocker, mock_puppetdb_environments):
    query_data = {
        'fact-names': [[chr(i) for i in range(ord('a'), ord('z') + 1)]]
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/facts')
    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    searchable = soup.find('div', {'class': 'searchable'})
    vals = searchable.find_all('div', {'class': 'column'})
    assert len(vals) == 4


def test_facts_view_empty_when_no_facts(client,
                                        mocker,
                                        mock_puppetdb_environments):
    query_data = {
        'fact-names': [[]]
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/facts')
    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    searchable = soup.find('div', {'class': 'searchable'})
    vals = searchable.find_all('div', {'class': 'column'})
    assert len(vals) == 0


def test_fact_view_with_graph(client, mocker,
                              mock_puppetdb_environments,
                              mock_puppetdb_default_nodes):
    rv = client.get('/fact/architecture')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('div', {"id": "factChart"})
    assert len(vals) == 1


def test_fact_view_without_graph(client, mocker,
                                 mock_puppetdb_environments,
                                 mock_puppetdb_default_nodes):
    rv = client.get('/%2A/fact/augeas')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('div', {"id": "factChart"})
    assert len(vals) == 0


def test_fact_value_view(client, mocker,
                         mock_puppetdb_environments,
                         mock_puppetdb_default_nodes):
    rv = client.get('/fact/architecture/amd64')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('div', {"id": "factChart"})
    assert len(vals) == 0


def test_fact_value_view_complex(client, mocker,
                                 mock_puppetdb_environments,
                                 mock_puppetdb_default_nodes):
    values = {
        'trusted': {
            'domain': '',
            'certname': 'node-changed',
            'hostname': 'node-changed',
            'extensions': {},
            'authenticated': 'remote',
        }
    }
    query_data = {'facts': []}
    query_data['facts'].append({
        'certname': 'node-changed',
        'name': 'trusted',
        'value': values,
        'environment': 'production'
    })

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/trusted/'
                    + "{'domain': ''%2C 'certname': 'node-changed'%2C"
                      " 'hostname': 'node-changed'%2C "
                      "'extensions': {}%2C 'authenticated': 'remote'}")
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('table', {"id": "facts_table"})
    assert len(vals) == 1


def test_fact_json_with_graph(client, mocker,
                              mock_puppetdb_environments,
                              mock_puppetdb_default_nodes):
    values = ['a', 'b', 'b', 'd', True, 'a\nb']
    query_data = {'facts': []}
    query_data['facts'].append([])
    for i, value in enumerate(values):
        query_data['facts'][0].append({
            'certname': 'node-%s' % i,
            'name': 'architecture',
            'value': value,
            'environment': 'production'
        })

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/architecture/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'data' in result_json
    assert len(result_json['data']) == 6
    for line in result_json['data']:
        assert len(line) == 2

    assert 'chart' in result_json
    assert len(result_json['chart']) == 5
    # Test group_by
    assert result_json['chart'][0]['value'] == 2


def test_fact_json_without_graph(client, mocker,
                                 mock_puppetdb_environments,
                                 mock_puppetdb_default_nodes):
    values = ['a', 'b', 'b', 'd']
    query_data = {'facts': []}
    query_data['facts'].append([])
    for i, value in enumerate(values):
        query_data['facts'][0].append({
            'certname': 'node-%s' % i,
            'name': 'architecture',
            'value': value,
            'environment': 'production'
        })

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/%2A/fact/augeas/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'data' in result_json
    assert len(result_json['data']) == 4
    for line in result_json['data']:
        assert len(line) == 2

    assert 'chart' not in result_json


def test_fact_value_json(client, mocker,
                         mock_puppetdb_environments,
                         mock_puppetdb_default_nodes):
    values = ['a', 'b', 'b', 'd']
    query_data = {'facts': []}
    query_data['facts'].append([])
    for i, value in enumerate(values):
        query_data['facts'][0].append({
            'certname': 'node-%s' % i,
            'name': 'architecture',
            'value': value,
            'environment': 'production'
        })

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/architecture/amd64/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'data' in result_json
    assert len(result_json['data']) == 4
    for line in result_json['data']:
        assert len(line) == 1

    assert 'chart' not in result_json


def test_node_facts_json(client, mocker,
                         mock_puppetdb_environments,
                         mock_puppetdb_default_nodes):
    values = ['a', 'b', 'b', 'd']
    query_data = {'facts': []}
    query_data['facts'].append([])
    for i, value in enumerate(values):
        query_data['facts'][0].append({
            'certname': 'node-failed',
            'name': 'fact-%s' % i,
            'value': value,
            'environment': 'production'
        })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/node/node-failed/facts/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'data' in result_json
    assert len(result_json['data']) == 4
    for line in result_json['data']:
        assert len(line) == 2

    assert 'chart' not in result_json
