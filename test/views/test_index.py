from bs4 import BeautifulSoup
from pypuppetdb.errors import DoesNotComputeError

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


def test_index_all_jolokia_fallback(client, mocker,
                                    mock_puppetdb_environments,
                                    mock_puppetdb_default_nodes):
    """Test that the all-environments index page falls back to PQL count
    queries when the Jolokia metrics endpoint raises DoesNotComputeError.

    This covers OpenVox-DB 8.14.0+ where the Jolokia serializer service
    was removed (java.lang.IllegalStateException: No service of type
    interface org.jolokia.server.core.service.serializer.Serializer found).
    """
    # Simulate Jolokia returning an error that pypuppetdb converts to
    # DoesNotComputeError
    mocker.patch.object(
        app.puppetdb, 'metric',
        side_effect=DoesNotComputeError(
            "java.lang.IllegalStateException : No service of type interface "
            "org.jolokia.server.core.service.serializer.Serializer found"
        )
    )

    # The PQL fallback queries: nodes count then resources count
    query_data = {
        'nodes': [[{'count': 25}]],
        'resources': [[{'count': 100}]],
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/%2A/')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('h1',
                         {"class": "ui header darkblue no-margin-bottom"})
    assert len(vals) == 3
    assert vals[0].string == '25'
    assert vals[1].string == '100'
    assert vals[2].string == '         4'


def test_index_all_jolokia_fallback_zero_nodes(client, mocker,
                                               mock_puppetdb_environments,
                                               mock_puppetdb_default_nodes):
    """Test the all-environments index page Jolokia fallback with zero nodes
    (division-by-zero edge case in the PQL fallback path).
    """
    mocker.patch.object(
        app.puppetdb, 'metric',
        side_effect=DoesNotComputeError(
            "java.lang.IllegalStateException : No service of type interface "
            "org.jolokia.server.core.service.serializer.Serializer found"
        )
    )

    query_data = {
        'nodes': [[{'count': 0}]],
        'resources': [[{'count': 0}]],
    }
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/%2A/')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    vals = soup.find_all('h1',
                         {"class": "ui header darkblue no-margin-bottom"})
    assert len(vals) == 3
    assert vals[0].string == '0'
    assert vals[1].string == '0'
    assert vals[2].string == '0'


def test_index_all_jolokia_zero_nodes(client, mocker,
                                      mock_puppetdb_environments,
                                      mock_puppetdb_default_nodes):
    """Test the all-environments index page when Jolokia returns zero nodes
    (division-by-zero edge case in the Jolokia path).
    """
    mocker.patch.object(
        app.puppetdb, 'metric',
        side_effect=[{'Value': 0}, {'Value': 0}]
    )

    rv = client.get('/%2A/')

    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    vals = soup.find_all('h1',
                         {"class": "ui header darkblue no-margin-bottom"})
    assert len(vals) == 3
    assert vals[0].string == '0'
    assert vals[1].string == '0'
    assert vals[2].string == '0'
