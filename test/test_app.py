import pytest
import json
import os
from datetime import datetime
from puppetboard import app
from pypuppetdb.types import Node, Report
from puppetboard import default_settings

from bs4 import BeautifulSoup


class MockDbQuery(object):
    def __init__(self, responses):
        self.responses = responses

    def get(self, method, **kws):
        resp = None
        if method in self.responses:
            resp = self.responses[method].pop(0)

            if 'validate' in resp:
                checks = resp['validate']['checks']
                resp = resp['validate']['data']
                for check in checks:
                    assert check in kws
                    expected_value = checks[check]
                    assert expected_value == kws[check]
        return resp


@pytest.fixture
def mock_puppetdb_environments(mocker):
    environemnts = [
        {'name': 'production'},
        {'name': 'staging'}
    ]
    return mocker.patch.object(app.puppetdb, 'environments',
                               return_value=environemnts)


@pytest.fixture
def mock_puppetdb_default_nodes(mocker):
    node_list = [
        Node('_', 'node-unreported',
             report_timestamp='2013-08-01T09:57:00.000Z',
             latest_report_hash='1234567',
             catalog_timestamp='2013-08-01T09:57:00.000Z',
             facts_timestamp='2013-08-01T09:57:00.000Z',
             status_report='unreported'),
        Node('_', 'node-changed',
             report_timestamp='2013-08-01T09:57:00.000Z',
             latest_report_hash='1234567',
             catalog_timestamp='2013-08-01T09:57:00.000Z',
             facts_timestamp='2013-08-01T09:57:00.000Z',
             status_report='changed'),
        Node('_', 'node-failed',
             report_timestamp='2013-08-01T09:57:00.000Z',
             latest_report_hash='1234567',
             catalog_timestamp='2013-08-01T09:57:00.000Z',
             facts_timestamp='2013-08-01T09:57:00.000Z',
             status_report='failed'),
        Node('_', 'node-noop',
             report_timestamp='2013-08-01T09:57:00.000Z',
             latest_report_hash='1234567',
             catalog_timestamp='2013-08-01T09:57:00.000Z',
             facts_timestamp='2013-08-01T09:57:00.000Z',
             status_report='noop'),
        Node('_', 'node-unchanged',
             report_timestamp='2013-08-01T09:57:00.000Z',
             latest_report_hash='1234567',
             catalog_timestamp='2013-08-01T09:57:00.000Z',
             facts_timestamp='2013-08-01T09:57:00.000Z',
             status_report='unchanged'),
        Node('_', 'node-skipped',
             report_timestamp='2013-08-01T09:57:00.000Z',
             latest_report_hash='1234567',
             catalog_timestamp='2013-08-01T09:57:00.000Z',
             facts_timestamp='2013-08-01T09:57:00.000Z',
             status_report='skipped')

    ]
    return mocker.patch.object(app.puppetdb, 'nodes',
                               return_value=iter(node_list))


@pytest.fixture
def input_data(request):
    data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'data')
    data = None
    with open('%s/%s' % (data_path, request.function.__name__), "r") as fp:
        data = fp.read()
    return data


@pytest.fixture
def client():
    client = app.app.test_client()
    return client


def test_first_test():
    assert app is not None, ("%s" % reg.app)


def test_no_env(client, mock_puppetdb_environments):
    rv = client.get('/nonexsistenv/')

    assert rv.status_code == 404


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
    rv = client.get('/%2A/')

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    vals = soup.find_all('h1',
                         {"class": "ui header darkblue no-margin-bottom"})

    assert len(vals) == 3
    assert vals[0].string == '50'
    assert vals[1].string == '60'
    assert vals[2].string == '        60'

    assert rv.status_code == 200


def test_index_all_older_puppetdb(client, mocker,
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
    rv = client.get('/%2A/')

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    vals = soup.find_all('h1',
                         {"class": "ui header darkblue no-margin-bottom"})

    assert len(vals) == 3
    assert vals[0].string == '50'
    assert vals[1].string == '60'
    assert vals[2].string == '        60'

    assert rv.status_code == 200


def test_index_division_by_zero(client, mocker):
    mock_puppetdb_environments(mocker)
    mock_puppetdb_default_nodes(mocker)

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


def test_offline_mode(client, mocker):
    app.app.config['OFFLINE_MODE'] = True

    mock_puppetdb_environments(mocker)
    mock_puppetdb_default_nodes(mocker)

    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/')
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    for link in soup.find_all('link'):
        assert "//" not in link['href']

    for script in soup.find_all('script'):
        if "src" in script.attrs:
            assert "//" not in script['src']

    assert rv.status_code == 200


def test_default_node_view(client, mocker,
                           mock_puppetdb_environments,
                           mock_puppetdb_default_nodes):

    rv = client.get('/nodes')
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    for label in ['failed', 'changed', 'unreported', 'noop']:
        vals = soup.find_all('a',
                             {"class": "ui %s label status" % label})
        assert len(vals) == 1
        assert 'node-%s' % (label) in vals[0].attrs['href']

    assert rv.status_code == 200


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


def test_radiator_view_all_old_version(client, mocker,
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
    assert json_data['skipped'] == 1
    assert json_data['unchanged'] == 1


def test_radiator_view_bad_env(client, mocker):
    mock_puppetdb_environments(mocker)
    mock_puppetdb_default_nodes(mocker)

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


def test_radiator_view_division_by_zero(client, mocker):
    mock_puppetdb_environments(mocker)
    mock_puppetdb_default_nodes(mocker)

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


def test_json_report_ok(client, mocker, input_data):
    mock_puppetdb_environments(mocker)
    mock_puppetdb_default_nodes(mocker)

    query_response = json.loads(input_data)

    query_data = {
        'reports': [
            {
                'validate': {
                    'data': query_response[:100],
                    'checks': {
                        'limit': 100,
                        'offset': 0
                    }
                }
            }
        ]
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    app.puppetdb.last_total = 499

    rv = client.get('/reports/json')

    assert rv.status_code == 200
    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'data' in result_json
    assert len(result_json['data']) == 100


def test_json_daily_reports_chart_ok(client, mocker):
    mock_puppetdb_environments(mocker)
    mock_puppetdb_default_nodes(mocker)

    query_data = {
        'reports': [
            [{'status': 'changed', 'count': 1}]
            for i in range(app.app.config['DAILY_REPORTS_CHART_DAYS'])
        ]
    }

    import logging
    logging.error(query_data)

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/daily_reports_chart.json')
    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'result' in result_json
    assert (len(result_json['result']) ==
            app.app.config['DAILY_REPORTS_CHART_DAYS'])
    day_format = '%Y-%m-%d'
    cur_day = datetime.strptime(result_json['result'][0]['day'], day_format)
    for day in result_json['result'][1:]:
        next_day = datetime.strptime(day['day'], day_format)
        assert cur_day < next_day
        cur_day = next_day

    assert rv.status_code == 200
