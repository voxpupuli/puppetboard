from bs4 import BeautifulSoup

from puppetboard import app
from test import MockDbQuery


def test_metrics_v2_api(client, mocker,
                        mock_puppetdb_environments,
                        mock_puppetdb_default_nodes):
    # starting with v6.9.1 they changed the metric API to v2
    # and a totally different format
    query_data = {
        'version': [{'version': '6.9.1'}],
        'metrics-list': [
            {
                'validate': {
                    'data': {
                        'value': {
                            'java.lang': {
                                'type=Memory': {}
                            },
                            'puppetlabs.puppetdb.population': {
                                'name=num-nodes': {}
                            },
                        }
                    },
                    'checks': {
                    }
                }
            }
        ]
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/metrics')

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    ul_list = soup.find_all('ul', attrs={'class': 'ui list searchable'})
    assert len(ul_list) == 1
    vals = ul_list[0].find_all('a')

    assert len(vals) == 2
    assert vals[0].string == 'java.lang:type=Memory'
    assert vals[1].string == 'puppetlabs.puppetdb.population:name=num-nodes'

    assert rv.status_code == 200


def test_metrics_v1_api(client, mocker,
                        mock_puppetdb_environments,
                        mock_puppetdb_default_nodes):
    query_data = {
        'version': [{'version': '4.2.0'}],
        'mbean': [
            {
                'validate': {
                    'data': {
                        'java.lang:type=Memory': {},
                        'puppetlabs.puppetdb.population:name=num-nodes': {},
                    },
                    'checks': {
                    }
                }
            }
        ]
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/metrics')

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    ul_list = soup.find_all('ul', attrs={'class': 'ui list searchable'})
    assert len(ul_list) == 1
    vals = ul_list[0].find_all('a')

    assert len(vals) == 2
    assert vals[0].string == 'java.lang:type=Memory'
    assert vals[1].string == 'puppetlabs.puppetdb.population:name=num-nodes'

    assert rv.status_code == 200


def test_metric_v2_api(client, mocker,
                       mock_puppetdb_environments,
                       mock_puppetdb_default_nodes):
    # starting with v6.9.1 they changed the metric API to v2
    # and a totally different format
    metric_name = 'puppetlabs.puppetdb.population:name=num-nodes'
    query_data = {
        'version': [{'version': '6.9.1'}],
        'metrics': [
            {
                'validate': {
                    'data': {
                        'value': {'Value': 50},
                    },
                    'checks': {
                        'path': metric_name,
                    }
                }
            }
        ]
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/metric/' + metric_name)

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    small_list = soup.find_all('small')
    assert len(small_list) == 1
    assert small_list[0].string == metric_name

    tbody_list = soup.find_all('tbody')
    assert len(tbody_list) == 1
    rows = tbody_list[0].find_all('tr')

    assert len(rows) == 1
    cols = rows[0].find_all('td')
    assert len(cols) == 2
    assert cols[0].string == 'Value'
    assert cols[1].string == '50'

    assert rv.status_code == 200


def test_metric_v1_api(client, mocker,
                       mock_puppetdb_environments,
                       mock_puppetdb_default_nodes):
    metric_name = 'puppetlabs.puppetdb.population:name=num-nodes'
    query_data = {
        'version': [{'version': '4.2.0'}],
        'mbean': [
            {
                'validate': {
                    'data': {'Value': 50},
                    'checks': {
                        'path': metric_name,
                    }
                }
            }
        ]
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/metric/' + metric_name)

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    small_list = soup.find_all('small')
    assert len(small_list) == 1
    assert small_list[0].string == metric_name

    tbody_list = soup.find_all('tbody')
    assert len(tbody_list) == 1
    rows = tbody_list[0].find_all('tr')

    assert len(rows) == 1
    cols = rows[0].find_all('td')
    assert len(cols) == 2
    assert cols[0].string == 'Value'
    assert cols[1].string == '50'

    assert rv.status_code == 200
