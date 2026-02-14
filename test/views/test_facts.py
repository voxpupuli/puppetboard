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


def test_structured_fact_view(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    """Test viewing a structured fact with dot notation"""
    rv = client.get('/fact/os.release.full')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    # Should show it's a structured fact
    h1 = soup.find('h1')
    assert 'os.release.full' in h1.get_text()


def test_structured_fact_json(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    """Test querying structured fact via JSON endpoint"""
    os_fact_value = {
        'name': 'Ubuntu',
        'release': {
            'full': '20.04',
            'major': '20'
        },
        'architecture': 'x86_64'
    }

    query_data = {'facts': []}
    query_data['facts'].append([])
    for i in range(3):
        query_data['facts'][0].append({
            'certname': 'node-%s' % i,
            'name': 'os',
            'value': os_fact_value,
            'environment': 'production'
        })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/os.release.full/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'data' in result_json
    assert len(result_json['data']) == 3
    for line in result_json['data']:
        assert len(line) == 2  # Node and Value columns


def test_structured_fact_with_value_filter(client, mocker,
                                            mock_puppetdb_environments,
                                            mock_puppetdb_default_nodes):
    """Test filtering structured facts by specific value"""
    os_fact_ubuntu = {
        'name': 'Ubuntu',
        'release': {
            'full': '20.04',
            'major': '20'
        }
    }
    os_fact_debian = {
        'name': 'Debian',
        'release': {
            'full': '11.0',
            'major': '11'
        }
    }

    query_data = {'facts': []}
    query_data['facts'].append([])
    query_data['facts'][0].append({
        'certname': 'node-ubuntu',
        'name': 'os',
        'value': os_fact_ubuntu,
        'environment': 'production'
    })
    query_data['facts'][0].append({
        'certname': 'node-debian',
        'name': 'os',
        'value': os_fact_debian,
        'environment': 'production'
    })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/os.release.full/20.04/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'data' in result_json
    # Should only return the Ubuntu node
    assert len(result_json['data']) == 1


def test_fact_children_ajax_top_level(client, mocker,
                                       mock_puppetdb_environments,
                                       mock_puppetdb_default_nodes):
    """Test AJAX endpoint for loading top-level children of a structured fact"""
    os_fact = {
        'name': 'Ubuntu',
        'release': {
            'full': '20.04',
            'major': '20'
        },
        'architecture': 'x86_64'
    }

    query_data = {'facts': []}
    query_data['facts'].append([])
    query_data['facts'][0].append({
        'certname': 'node-1',
        'name': 'os',
        'value': os_fact,
        'environment': 'production'
    })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/os/children/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'children' in result_json

    # Should return direct children: name, release, architecture
    children_names = [c['name'] for c in result_json['children']]
    assert 'os.name' in children_names
    assert 'os.release' in children_names
    assert 'os.architecture' in children_names

    # Check that 'release' is marked as having children
    release_child = next(c for c in result_json['children'] if c['name'] == 'os.release')
    assert release_child['has_children'] is True

    # Check that 'name' is marked as NOT having children (leaf node)
    name_child = next(c for c in result_json['children'] if c['name'] == 'os.name')
    assert name_child['has_children'] is False


def test_fact_children_ajax_nested(client, mocker,
                                   mock_puppetdb_environments,
                                   mock_puppetdb_default_nodes):
    """Test AJAX endpoint for loading nested children of a structured fact"""
    os_fact = {
        'name': 'Ubuntu',
        'release': {
            'full': '20.04',
            'major': '20'
        }
    }

    query_data = {'facts': []}
    query_data['facts'].append([])
    query_data['facts'][0].append({
        'certname': 'node-1',
        'name': 'os',
        'value': os_fact,
        'environment': 'production'
    })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/os.release/children/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'children' in result_json

    # Should return children of 'release': full, major
    children_names = [c['name'] for c in result_json['children']]
    assert 'os.release.full' in children_names
    assert 'os.release.major' in children_names
    assert len(result_json['children']) == 2

    # Both should be leaf nodes
    for child in result_json['children']:
        assert child['has_children'] is False


def test_fact_children_ajax_variable_keys(client, mocker,
                                          mock_puppetdb_environments,
                                          mock_puppetdb_default_nodes):
    """Test AJAX endpoint aggregates keys across nodes for variable-key facts"""
    # Node 1 has packages A and B
    node1_packages = {
        'package-a': {'version': '1.0'},
        'package-b': {'version': '2.0'}
    }

    # Node 2 has packages B and C (B is common, C is unique)
    node2_packages = {
        'package-b': {'version': '2.1'},
        'package-c': {'version': '3.0'}
    }

    query_data = {'facts': []}
    query_data['facts'].append([])
    query_data['facts'][0].append({
        'certname': 'node-1',
        'name': 'chocopackages',
        'value': node1_packages,
        'environment': 'production'
    })
    query_data['facts'][0].append({
        'certname': 'node-2',
        'name': 'chocopackages',
        'value': node2_packages,
        'environment': 'production'
    })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/chocopackages/children/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'children' in result_json

    # Should aggregate ALL unique keys: package-a, package-b, package-c
    children_names = [c['name'] for c in result_json['children']]
    assert 'chocopackages.package-a' in children_names
    assert 'chocopackages.package-b' in children_names
    assert 'chocopackages.package-c' in children_names
    assert len(result_json['children']) == 3


def test_fact_children_ajax_empty_for_simple_fact(client, mocker,
                                                  mock_puppetdb_environments,
                                                  mock_puppetdb_default_nodes):
    """Test AJAX endpoint returns empty for non-dict facts"""
    query_data = {'facts': []}
    query_data['facts'].append([])
    query_data['facts'][0].append({
        'certname': 'node-1',
        'name': 'hostname',
        'value': 'server01',
        'environment': 'production'
    })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/hostname/children/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'children' in result_json
    assert len(result_json['children']) == 0


def test_fact_children_ajax_empty_for_nonexistent_fact(client, mocker,
                                                       mock_puppetdb_environments,
                                                       mock_puppetdb_default_nodes):
    """Test AJAX endpoint returns empty for facts that don't exist"""
    query_data = {'facts': []}
    query_data['facts'].append([])  # Empty result

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/nonexistent/children/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'children' in result_json
    assert len(result_json['children']) == 0


def test_fact_children_ajax_skips_keys_with_dots(client, mocker,
                                                 mock_puppetdb_environments,
                                                 mock_puppetdb_default_nodes):
    """Test AJAX endpoint skips dict keys containing dots"""
    myco_services = {
        'MYCO.Fictional': {
            'state': 'Running'
        },
        'ValidServiceName': {
            'state': 'Stopped'
        }
    }

    query_data = {'facts': []}
    query_data['facts'].append([])
    query_data['facts'][0].append({
        'certname': 'node-1',
        'name': 'myco_services',
        'value': myco_services,
        'environment': 'production'
    })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/myco_services/children/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'children' in result_json

    # Should only include ValidServiceName, not G1.ActivOneApiDaemon (has dot)
    children_names = [c['name'] for c in result_json['children']]
    assert 'myco_services.ValidServiceName' in children_names
    assert 'myco_services.G1.ActivOneApiDaemon' not in children_names


def test_fact_children_ajax_skips_keys_with_slashes(client, mocker,
                                                    mock_puppetdb_environments,
                                                    mock_puppetdb_default_nodes):
    """Test AJAX endpoint skips dict keys containing slashes"""
    mountpoints = {
        '/': {'size': '100G'},
        '/home': {'size': '500G'},
        'valid_key': {'size': '50G'}
    }

    query_data = {'facts': []}
    query_data['facts'].append([])
    query_data['facts'][0].append({
        'certname': 'node-1',
        'name': 'mountpoints',
        'value': mountpoints,
        'environment': 'production'
    })

    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/fact/mountpoints/children/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'children' in result_json

    # Should only include valid_key, not / or /home (have slashes)
    children_names = [c['name'] for c in result_json['children']]
    assert 'mountpoints.valid_key' in children_names
    assert len(result_json['children']) == 1


def test_facts_page_shows_structured_facts_as_parents(client, mocker,
                                                      mock_puppetdb_environments):
    """Test facts page marks structured facts as parents with lazy-loaded children"""
    fact_names = ['hostname', 'os', 'kernel']

    # Mock fact names
    fact_names_query = {'fact-names': [fact_names]}

    # Mock fact values - os is structured, others are simple
    facts_query = {'facts': []}
    facts_query['facts'].append([])
    facts_query['facts'][0].append({
        'certname': 'node-1',
        'name': 'hostname',
        'value': 'server01',
        'environment': 'production'
    })
    facts_query['facts'][0].append({
        'certname': 'node-1',
        'name': 'os',
        'value': {'name': 'Ubuntu', 'release': {'full': '20.04'}},
        'environment': 'production'
    })
    facts_query['facts'][0].append({
        'certname': 'node-1',
        'name': 'kernel',
        'value': 'Linux',
        'environment': 'production'
    })

    query_data = {**fact_names_query, **facts_query}
    dbquery = MockDbQuery(query_data)
    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)

    rv = client.get('/facts')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')

    # Check that 'os' has the fact-toggle (expandable arrow)
    os_parent = soup.find('a', {'class': 'ui small blue label'}, string='os')
    assert os_parent is not None

    # Check that it has an expand arrow
    parent_li = os_parent.parent
    toggle_span = parent_li.find('span', {'class': 'fact-toggle'})
    assert toggle_span is not None
    assert '▶' in toggle_span.text

    # Check that it has an empty ul for lazy-loaded children
    children_ul = parent_li.find('ul', {'class': 'fact-children collapsed'})
    assert children_ul is not None

    # Check that simple facts (hostname, kernel) don't have toggles
    hostname_link = soup.find('a', href=lambda x: x and '/fact/hostname' in x and 'blue label' not in str(x))
    assert hostname_link is not None
    hostname_parent = hostname_link.parent
    hostname_toggle = hostname_parent.find('span', {'class': 'fact-toggle'})
    assert hostname_toggle is None
