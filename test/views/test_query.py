import tempfile
import os

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


def test_query_presets_loaded(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    """Test that query presets are loaded and displayed when configured"""
    # Create a temporary YAML file with test presets
    preset_content = """
- name: "Test Query 1"
  description: "Test description 1"
  query: "nodes { certname ~ '.*' }"
  endpoint: pql
  raw_json: false

- name: "Test Query 2"
  description: "Test description 2"
  query: "facts { name = 'os' }"
  endpoint: facts
  raw_json: true
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(preset_content)
        preset_file = f.name

    try:
        # Configure app to use the preset file
        app.app.config['QUERY_PRESETS_FILE'] = preset_file

        rv = client.get('/query')
        assert rv.status_code == 200

        soup = BeautifulSoup(rv.data, 'html.parser')

        # Check that preset dropdown exists
        preset_selector = soup.find('select', {'id': 'preset-selector'})
        assert preset_selector is not None

        # Check that both presets are in the dropdown
        options = preset_selector.find_all('option')
        assert len(options) == 2  # 2 presets

        # Check preset 1
        option1 = soup.find('option', {'data-query': "nodes { certname ~ '.*' }"})
        assert option1 is not None
        assert 'Test Query 1' in option1.text
        assert option1.get('data-endpoint') == 'pql'
        assert option1.get('data-raw-json') == 'false'
        assert option1.get('data-description') == 'Test description 1'

        # Check preset 2
        option2 = soup.find('option', {'data-query': "facts { name = 'os' }"})
        assert option2 is not None
        assert 'Test Query 2' in option2.text
        assert option2.get('data-endpoint') == 'facts'
        assert option2.get('data-raw-json') == 'true'

    finally:
        # Clean up temp file
        if os.path.exists(preset_file):
            os.unlink(preset_file)
        # Reset config
        app.app.config['QUERY_PRESETS_FILE'] = None


def test_query_no_presets_when_disabled(client, mocker,
                                         mock_puppetdb_environments,
                                         mock_puppetdb_default_nodes):
    """Test that preset dropdown is not shown when QUERY_PRESETS_FILE is None"""
    app.app.config['QUERY_PRESETS_FILE'] = None

    rv = client.get('/query')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')

    # Check that preset dropdown does NOT exist
    preset_selector = soup.find('select', {'id': 'preset-selector'})
    assert preset_selector is None


def test_query_presets_invalid_yaml(client, mocker,
                                     mock_puppetdb_environments,
                                     mock_puppetdb_default_nodes):
    """Test that invalid YAML in presets file doesn't crash the app"""
    # Create a temporary YAML file with invalid content
    preset_content = """
- name: "Test Query"
  invalid yaml here
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(preset_content)
        preset_file = f.name

    try:
        app.app.config['QUERY_PRESETS_FILE'] = preset_file

        rv = client.get('/query')
        assert rv.status_code == 200

        soup = BeautifulSoup(rv.data, 'html.parser')

        # App should handle error gracefully and not show presets
        preset_selector = soup.find('select', {'id': 'preset-selector'})
        # Might be None or have no options
        if preset_selector:
            options = preset_selector.find_all('option')
            assert len(options) <= 1  # Only default option or none

    finally:
        if os.path.exists(preset_file):
            os.unlink(preset_file)
        app.app.config['QUERY_PRESETS_FILE'] = None


def test_query_presets_missing_required_fields(client, mocker,
                                                mock_puppetdb_environments,
                                                mock_puppetdb_default_nodes):
    """Test that presets missing required fields are skipped"""
    preset_content = """
- name: "Valid Query"
  query: "nodes {}"

- description: "Missing name field"
  query: "nodes {}"

- name: "Missing query field"
  endpoint: pql
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(preset_content)
        preset_file = f.name

    try:
        app.app.config['QUERY_PRESETS_FILE'] = preset_file

        rv = client.get('/query')
        assert rv.status_code == 200

        soup = BeautifulSoup(rv.data, 'html.parser')
        preset_selector = soup.find('select', {'id': 'preset-selector'})

        if preset_selector:
            options = preset_selector.find_all('option')
            # Should have 1 valid preset (the other 2 should be skipped)
            assert len(options) == 1
            assert 'Valid Query' in str(options[0])

    finally:
        if os.path.exists(preset_file):
            os.unlink(preset_file)
        app.app.config['QUERY_PRESETS_FILE'] = None


def test_query_presets_file_not_found(client, mocker,
                                       mock_puppetdb_environments,
                                       mock_puppetdb_default_nodes):
    """Test that a non-existent presets file is handled gracefully"""
    app.app.config['QUERY_PRESETS_FILE'] = '/nonexistent/path/presets.yaml'

    rv = client.get('/query')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')

    # Preset selector should not be shown when file doesn't exist
    preset_selector = soup.find('select', {'id': 'preset-selector'})
    assert preset_selector is None

    # Reset config
    app.app.config['QUERY_PRESETS_FILE'] = None


def test_query_presets_not_a_list(client, mocker,
                                   mock_puppetdb_environments,
                                   mock_puppetdb_default_nodes):
    """Test that presets file containing non-list data is handled gracefully"""
    # Create a YAML file with a dict instead of a list
    preset_content = """
name: "Single Query"
query: "nodes {}"
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(preset_content)
        preset_file = f.name

    try:
        app.app.config['QUERY_PRESETS_FILE'] = preset_file

        rv = client.get('/query')
        assert rv.status_code == 200

        soup = BeautifulSoup(rv.data, 'html.parser')

        # Preset selector should not be shown when file format is invalid
        preset_selector = soup.find('select', {'id': 'preset-selector'})
        assert preset_selector is None

    finally:
        if os.path.exists(preset_file):
            os.unlink(preset_file)
        app.app.config['QUERY_PRESETS_FILE'] = None


def test_query_presets_non_dict_entry(client, mocker,
                                       mock_puppetdb_environments,
                                       mock_puppetdb_default_nodes):
    """Test that non-dict entries in presets list are skipped"""
    preset_content = """
- name: "Valid Query"
  query: "nodes {}"

- "just a string"

- 12345
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(preset_content)
        preset_file = f.name

    try:
        app.app.config['QUERY_PRESETS_FILE'] = preset_file

        rv = client.get('/query')
        assert rv.status_code == 200

        soup = BeautifulSoup(rv.data, 'html.parser')
        preset_selector = soup.find('select', {'id': 'preset-selector'})

        if preset_selector:
            options = preset_selector.find_all('option')
            # Should only have 1 valid preset
            assert len(options) == 1
            assert 'Valid Query' in str(options[0])

    finally:
        if os.path.exists(preset_file):
            os.unlink(preset_file)
        app.app.config['QUERY_PRESETS_FILE'] = None


def test_query_presets_default_values(client, mocker,
                                       mock_puppetdb_environments,
                                       mock_puppetdb_default_nodes):
    """Test that optional fields get correct default values"""
    # Create preset with only required fields (name and query)
    preset_content = """
- name: "Minimal Query"
  query: "nodes { certname ~ '.*' }"
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(preset_content)
        preset_file = f.name

    try:
        app.app.config['QUERY_PRESETS_FILE'] = preset_file

        rv = client.get('/query')
        assert rv.status_code == 200

        soup = BeautifulSoup(rv.data, 'html.parser')
        preset_selector = soup.find('select', {'id': 'preset-selector'})
        assert preset_selector is not None

        option = soup.find('option', {'data-query': "nodes { certname ~ '.*' }"})
        assert option is not None
        assert 'Minimal Query' in option.text
        # Check default values
        assert option.get('data-endpoint') == 'pql'  # default endpoint
        assert option.get('data-raw-json') == 'false'  # default raw_json
        assert option.get('data-description') == ''  # default empty description

    finally:
        if os.path.exists(preset_file):
            os.unlink(preset_file)
        app.app.config['QUERY_PRESETS_FILE'] = None
