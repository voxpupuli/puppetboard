import json

import pytest
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError, Timeout

from puppetboard import app
from puppetboard.views import packages as packages_view
from test import MockHTTPResponse

NODES = [
    {'certname': 'u1', 'timestamp': '2026-10-20T10:00:00.000Z',
     'facts.os.name': 'Ubuntu', 'facts.os.release.major': '22.04'},
    {'certname': 'u2', 'timestamp': '2026-10-20T10:00:00.000Z',
     'facts.os.name': 'Ubuntu', 'facts.os.release.major': '22.04'},
    {'certname': 'r1', 'timestamp': '2026-10-20T10:00:00.000Z',
     'facts.os.name': 'RedHat', 'facts.os.release.major': '9'},
    {'certname': 'x1', 'timestamp': '2026-10-20T10:00:00.000Z',
     'facts.os.name': None, 'facts.os.release.major': None},
]

ROWS = [
    {'certname': 'u1', 'package_name': 'openssl', 'version': '3.0.2-0ubuntu1.12', 'provider': 'apt'},
    {'certname': 'u1', 'package_name': 'libssl3', 'version': '3.0.2-0ubuntu1.12', 'provider': 'apt'},
    {'certname': 'u2', 'package_name': 'openssl', 'version': '3.0.2-0ubuntu1.15', 'provider': 'apt'},
    {'certname': 'r1', 'package_name': 'openssl-libs', 'version': '1:3.0.7-27.el9', 'provider': 'dnf'},
    {'certname': 'x1', 'package_name': 'openssl', 'version': '1.0', 'provider': 'apt'},
    # not in the inventory: other environment or deactivated node
    {'certname': 'gone', 'package_name': 'openssl', 'version': '1.0', 'provider': 'apt'},
]

SEARCH = ('/packages?pkg=openssl,libssl3,openssl-libs'
          '&t_Ubuntu+22.04=3.0.2-0ubuntu1.15')


class FakePuppetDB:
    """Answers the AST queries of the view by entity and records them."""

    def __init__(self, rows=(), nodes=(), names=(), error=None):
        self.data = {'package_inventory': list(rows), 'inventory': list(nodes),
                     'packages': list(names)}
        self.error = error
        self.queries = []

    def __call__(self, endpoint, query=None, **kwargs):
        assert endpoint == 'pql'
        ast = json.loads(query)
        self.queries.append(ast)
        if self.error:
            raise self.error
        return self.data[ast[1]]

    def query(self, entity):
        return next(q for q in self.queries if q[1] == entity)


@pytest.fixture
def enabled():
    app.app.config['ENABLE_PACKAGES'] = True
    packages_view.cache.clear()
    yield
    app.app.config['ENABLE_PACKAGES'] = False


def fake_db(mocker, **kwargs):
    fake = FakePuppetDB(**kwargs)
    mocker.patch.object(app.puppetdb, '_query', side_effect=fake)
    return fake


def group(results, label):
    return next(g for g in results['groups'] if g['label'] == label)


# --- pure logic ---

def test_build_results_statuses_and_counts():
    # Covers AE1, AE3
    results = packages_view.build_results(ROWS, NODES, {'Ubuntu 22.04': '3.0.2-0ubuntu1.15'})

    ubuntu = group(results, 'Ubuntu 22.04')
    assert ubuntu['servers'] == {'u1': 'below', 'u2': 'ok'}
    assert ubuntu['has_field'] is True
    redhat = group(results, 'RedHat 9')
    assert redhat['servers'] == {'r1': 'none'}
    assert redhat['has_field'] is True
    unknown = group(results, 'Unknown OS')
    assert unknown['servers'] == {'x1': 'none'}
    assert unknown['has_field'] is False

    assert results['servers'] == 4
    assert results['totals'] == {'below': 1, 'ok': 1, 'none': 2}
    # two rows for u1 (openssl and libssl3), none for the node outside the inventory
    assert [r[1] for r in results['rows']] == ['u1', 'u1', 'r1', 'x1', 'u2']
    assert [r[0] for r in results['rows']] == ['below', 'below', 'none', 'none', 'ok']
    assert results['groups'][-1]['label'] == 'Unknown OS'


def test_build_results_epoch_inherited():
    results = packages_view.build_results(ROWS, NODES, {'RedHat 9': '3.0.7-28.el9'})
    assert group(results, 'RedHat 9')['servers'] == {'r1': 'below'}


def test_build_results_server_status_is_most_severe():
    # Covers AE4: one row per installed version, the server takes the worst
    rows = [
        {'certname': 'u1', 'package_name': 'linux-image', 'version': '5.15.0-1', 'provider': 'apt'},
        {'certname': 'u1', 'package_name': 'linux-image', 'version': '5.15.0-9', 'provider': 'apt'},
        {'certname': 'u2', 'package_name': 'linux-image', 'version': '5.15.0-9', 'provider': 'apt'},
        {'certname': 'u2', 'package_name': 'cryptography', 'version': '1.0', 'provider': 'pip3'},
    ]
    results = packages_view.build_results(rows, NODES, {'Ubuntu 22.04': '5.15.0-5'})
    assert [r[0] for r in results['rows']] == ['below', 'none', 'ok', 'ok']
    assert group(results, 'Ubuntu 22.04')['servers'] == {'u1': 'below', 'u2': 'none'}


def test_build_results_orphan_and_invalid_thresholds():
    results = packages_view.build_results(ROWS, NODES, {'Debian 12': '1.0', 'Ubuntu 22.04': '<3.0'})
    debian = group(results, 'Debian 12')
    assert debian['total'] == 0
    assert debian['has_field'] is True
    assert debian['raw'] == '1.0'
    ubuntu = group(results, 'Ubuntu 22.04')
    assert ubuntu['invalid'] is True
    assert ubuntu['servers'] == {'u1': 'none', 'u2': 'none'}
    assert results['any_invalid'] is True
    assert results['groups'][-2]['label'] == 'Debian 12'


def test_build_results_no_comparable_package_has_no_field():
    rows = [{'certname': 'u1', 'package_name': 'requests', 'version': '2.0', 'provider': 'pip3'}]
    results = packages_view.build_results(rows, NODES, {})
    assert group(results, 'Ubuntu 22.04')['has_field'] is False


def test_parse_names():
    assert packages_view.parse_names(' a, b,,a ,' + 'x' * 300) == (['a', 'b'], False)
    names, too_many = packages_view.parse_names(','.join(f'p{i}' for i in range(11)))
    assert len(names) == 10
    assert too_many is True
    assert packages_view.parse_names(None) == ([], False)


def test_parse_thresholds():
    args = {'t_Ubuntu 22.04': '1.0', 't_Unknown OS': '1.0', 't_': '1.0', 'pkg': 'a',
            't_Debian 12': ' ', 't_' + 'x' * 101: '1.0'}
    assert packages_view.parse_thresholds(args) == {'Ubuntu 22.04': '1.0'}
    many = {f't_os{i}': '1.0' for i in range(60)}
    assert len(packages_view.parse_thresholds(many)) == packages_view.MAX_THRESHOLDS


# --- routes ---

def test_packages_disabled(client, mock_puppetdb_environments):
    app.app.config['ENABLE_PACKAGES'] = False
    assert client.get('/packages').status_code == 403
    assert client.get('/staging/packages').status_code == 403
    assert client.get('/packages/names/json?q=ssl').status_code == 403


def test_packages_empty_page(client, mocker, mock_puppetdb_environments, enabled):
    fake = fake_db(mocker)
    rv = client.get('/packages')
    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.find('div', id='pkg_dropdown') is not None
    assert 'Pick one or more package names' in soup.text
    assert fake.queries == []


def test_packages_unknown_env(client, mock_puppetdb_environments, enabled):
    assert client.get('/nope/packages').status_code == 404


def test_names_autocomplete(client, mocker, enabled):
    fake = fake_db(mocker, names=[{'package_name': 'libssl3'}, {'package_name': 'libssl3'},
                                  {'package_name': 'openssl'}, {'package_name': 'a,b'}])
    rv = client.get('/packages/names/json?q=SSL')
    assert rv.status_code == 200
    assert json.loads(rv.data) == {'success': True, 'results': [
        {'name': 'libssl3', 'value': 'libssl3'}, {'name': 'openssl', 'value': 'openssl'}]}
    prefix, contains = fake.queries
    assert ['~', 'package_name', '(?i)^SSL'] in prefix[2]
    assert ['~', 'package_name', '(?i)SSL'] in contains[2]
    assert ['limit', packages_view.MAX_SUGGESTIONS] in prefix

    # served from the cache the second time, case-insensitively
    client.get('/packages/names/json?q=ssl')
    assert len(fake.queries) == 2


def test_names_autocomplete_prefix_first(client, mocker, enabled):
    def answer(endpoint, query=None, **kwargs):
        pattern = json.loads(query)[2][2][2]
        if pattern.startswith('(?i)^'):
            return [{'package_name': 'perl'}]
        return [{'package_name': 'libperl5'}, {'package_name': 'perl'}]

    mocker.patch.object(app.puppetdb, '_query', side_effect=answer)
    rv = client.get('/packages/names/json?q=perl')
    assert [r['name'] for r in json.loads(rv.data)['results']] == ['perl', 'libperl5']


def test_names_autocomplete_full_prefix_page(client, mocker, enabled):
    mocker.patch.object(packages_view, 'MAX_SUGGESTIONS', 1)
    fake = fake_db(mocker, names=[{'package_name': 'perl'}])
    rv = client.get('/packages/names/json?q=perl')
    assert [r['name'] for r in json.loads(rv.data)['results']] == ['perl']
    assert len(fake.queries) == 1


def test_names_autocomplete_short_fragment(client, mocker, enabled):
    fake = fake_db(mocker)
    rv = client.get('/packages/names/json?q=s')
    assert json.loads(rv.data) == {'success': True, 'results': []}
    assert fake.queries == []


def test_names_autocomplete_escapes_regex(client, mocker, enabled):
    fake = fake_db(mocker)
    client.get('/packages/names/json?q=libstdc%2B%2B')
    assert ['~', 'package_name', '(?i)^libstdc\\+\\+'] in fake.query('packages')[2]


def test_names_autocomplete_error(client, mocker, enabled):
    fake = fake_db(mocker, error=Timeout('slow'))
    rv = client.get('/packages/names/json?q=ssl')
    assert rv.status_code == 502
    assert json.loads(rv.data)['success'] is False
    # errors are not cached
    client.get('/packages/names/json?q=ssl')
    assert len(fake.queries) == 2
    assert fake.queries[0] == fake.queries[1]


def test_search_queries_filter_environment(client, mocker, mock_puppetdb_environments, enabled):
    fake = fake_db(mocker, rows=ROWS, nodes=NODES)
    names_filter = ['in', 'package_name', ['array', ['openssl', 'libssl3', 'openssl-libs']]]
    with_packages = ['in', 'certname',
                     ['from', 'package_inventory', ['extract', 'certname', names_filter]]]

    client.get('/staging' + SEARCH)
    packages_ast = fake.query('package_inventory')
    assert packages_ast[2][2] == [
        'and', names_filter,
        ['in', 'certname', ['from', 'inventory', ['extract', 'certname',
                                                  ['=', 'environment', 'staging']]]]]
    assert ['order_by', ['certname', 'package_name', 'version']] in packages_ast
    assert ['limit', packages_view.MAX_ROWS + 1] in packages_ast
    assert fake.query('inventory')[2][2] == ['and', ['=', 'environment', 'staging'], with_packages]

    fake.queries.clear()
    client.get('/*' + SEARCH)
    assert fake.query('package_inventory')[2][2] == names_filter
    assert fake.query('inventory')[2][2] == with_packages


def test_search_page(client, mocker, mock_puppetdb_environments, enabled):
    # Covers AE6: the shared link renders the same search
    fake_db(mocker, rows=ROWS, nodes=NODES)
    rv = client.get(SEARCH)
    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')

    selected = [i['data-value'] for i in soup.select('#pkg_dropdown .item')]
    assert selected == ['openssl', 'libssl3', 'openssl-libs']
    assert soup.find('input', {'name': 'pkg'})['value'] == 'openssl,libssl3,openssl-libs'

    field = soup.find('input', {'name': 't_Ubuntu 22.04'})
    assert field['value'] == '3.0.2-0ubuntu1.15'
    assert field['aria-label'] == 'Threshold for Ubuntu 22.04 (2 servers)'
    assert soup.find('input', {'name': 't_RedHat 9'}) is not None
    assert soup.find('input', {'name': 't_Unknown OS'}) is None

    ubuntu_row = [c.text.strip() for c in soup.find('th', string='Ubuntu 22.04').parent.find_all('td')]
    assert ubuntu_row[0] == '2'
    assert ubuntu_row[2:] == ['1', '1', '0']
    redhat_row = [c.text.strip() for c in soup.find('th', string='RedHat 9').parent.find_all('td')]
    assert redhat_row[2:] == ['–', '–', '1']

    html = rv.data.decode()
    for text in ('Below threshold', 'Up to date', 'No verdict'):
        assert text in html
    assert 'No threshold set yet' not in html

    # the environment selector keeps the search
    env_urls = [i['data-value'] for i in soup.select('.select-environment .item')]
    assert all('pkg=openssl' in url and 't_Ubuntu' in url for url in env_urls)


def test_search_no_threshold_message(client, mocker, mock_puppetdb_environments, enabled):
    fake_db(mocker, rows=ROWS, nodes=NODES)
    rv = client.get('/packages?pkg=openssl')
    assert 'No threshold set yet' in rv.data.decode()


def test_search_escapes_agent_data(client, mocker, mock_puppetdb_environments, enabled):
    hostile = '<img src=x onerror=alert(1)>'
    rows = [{'certname': 'u1', 'package_name': hostile, 'version': hostile, 'provider': 'apt'}]
    nodes = [dict(NODES[0], **{'facts.os.name': hostile})]
    fake_db(mocker, rows=rows, nodes=nodes)
    rv = client.get('/packages?pkg=openssl')
    assert hostile not in rv.data.decode()


def test_search_invalid_threshold(client, mocker, mock_puppetdb_environments, enabled):
    fake_db(mocker, rows=ROWS, nodes=NODES)
    rv = client.get('/packages?pkg=openssl&t_Ubuntu+22.04=openssl-3.0.7-28.el9.x86_64')
    soup = BeautifulSoup(rv.data, 'html.parser')
    summary = soup.find(id='packages_focus')
    assert 'not versions' in summary.text
    link = summary.find('a')
    field = soup.find(id=link['href'][1:])
    assert field['value'] == 'openssl-3.0.7-28.el9.x86_64'
    assert field['aria-invalid'] == 'true'
    error_id = field['aria-describedby'].split()[1]
    assert 'Enter only the version' in soup.find(id=error_id).text


def test_search_error_keeps_form(client, mocker, mock_puppetdb_environments, enabled):
    fake_db(mocker, error=Timeout('slow'))
    rv = client.get(SEARCH)
    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert 'PuppetDB returned an error.' in soup.text
    assert 'has these packages' not in soup.text
    assert soup.find('input', {'name': 't_Ubuntu 22.04'})['value'] == '3.0.2-0ubuntu1.15'
    assert soup.find('input', {'name': 'pkg'})['value'] == 'openssl,libssl3,openssl-libs'
    # no count is shown as if it were data
    row = [c.text.strip() for c in soup.find('th', string='Ubuntu 22.04').parent.find_all('td')]
    assert row[0] == '–'
    assert row[2:] == ['–', '–', '–']
    assert soup.find('tfoot') is None


@pytest.mark.parametrize('status,message', [
    (400, 'PuppetDB returned an error (400).'),
    (None, 'PuppetDB returned an error.'),
])
def test_search_http_error(client, mocker, mock_puppetdb_environments, enabled, status, message):
    error = HTTPError('bad query')
    if status:
        error.response = MockHTTPResponse(status, 'bad query')
    fake_db(mocker, error=error)
    rv = client.get(SEARCH)
    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert message in soup.text
    assert 'has these packages' not in soup.text


def test_search_zero_servers(client, mocker, mock_puppetdb_environments, enabled):
    fake = fake_db(mocker, rows=[], nodes=NODES)
    soup = BeautifulSoup(client.get('/staging/packages?pkg=openssl').data, 'html.parser')
    assert 'No server in staging has these packages.' in soup.text
    assert soup.find('a', string='Search all environments') is not None
    # no node query when no package matched
    assert [q[1] for q in fake.queries] == ['package_inventory']

    soup = BeautifulSoup(client.get('/*/packages?pkg=openssl').data, 'html.parser')
    assert 'No server has these packages.' in soup.text
    assert soup.find('a', string='Search all environments') is None


def test_search_truncated(client, mocker, mock_puppetdb_environments, enabled):
    mocker.patch.object(packages_view, 'MAX_ROWS', 2)
    fake_db(mocker, rows=ROWS, nodes=NODES)
    html = client.get(SEARCH).data.decode()
    assert 'Results truncated at 2 rows' in html
    assert 'at least 1' in html


def test_search_truncation_drops_split_server(client, mocker, mock_puppetdb_environments, enabled):
    rows = [
        {'certname': 'u1', 'package_name': 'openssl', 'version': '3.0.2-0ubuntu1.12', 'provider': 'apt'},
        {'certname': 'u2', 'package_name': 'libssl3', 'version': '3.0.2-0ubuntu1.15', 'provider': 'apt'},
        # cut here: u2 would look up to date without this row
        {'certname': 'u2', 'package_name': 'openssl', 'version': '3.0.2-0ubuntu1.12', 'provider': 'apt'},
    ]
    mocker.patch.object(packages_view, 'MAX_ROWS', 2)
    fake_db(mocker, rows=rows, nodes=NODES)
    soup = BeautifulSoup(client.get(SEARCH).data, 'html.parser')
    row = [c.text.strip() for c in soup.find('th', string='Ubuntu 22.04').parent.find_all('td')]
    assert row[0] == 'at least 1'
    assert row[2:] == ['at least 1', 'at least 0', 'at least 0']


def test_search_too_many_names(client, mocker, mock_puppetdb_environments, enabled):
    fake = fake_db(mocker, rows=[], nodes=NODES)
    names = ','.join(f'p{i}' for i in range(12))
    html = client.get('/packages?pkg=' + names).data.decode()
    assert 'Only the first 10 packages are searched.' in html
    assert len(fake.query('package_inventory')[2][2][1][2][1]) == 10
