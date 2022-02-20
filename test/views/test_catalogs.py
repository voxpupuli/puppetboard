import json

from bs4 import BeautifulSoup

from puppetboard import app


def test_catalogs_disabled(client, mocker,
                           mock_puppetdb_environments,
                           mock_puppetdb_default_nodes):
    app.app.config['ENABLE_CATALOG'] = False
    rv = client.get('/catalogs')
    assert rv.status_code == 403


def test_catalogs_view(client, mocker,
                       mock_puppetdb_environments,
                       mock_puppetdb_default_nodes):
    app.app.config['ENABLE_CATALOG'] = True

    # below code checks last_total, which should be set after _query
    # so we need to simulate that. the value doesn't matter.
    app.puppetdb.last_total = 0
    rv = client.get('/catalogs')
    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'


def test_catalogs_json(client, mocker,
                       mock_puppetdb_environments,
                       mock_puppetdb_default_nodes):
    app.app.config['ENABLE_CATALOG'] = True

    # below code checks last_total, which should be set after _query
    # so we need to simulate that. the value doesn't matter.
    app.puppetdb.last_total = 0
    rv = client.get('/catalogs/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'data' in result_json

    for line in result_json['data']:
        assert len(line) == 3
        found_status = None
        for status in ['failed', 'changed', 'unchanged', 'noop', 'unreported']:
            val = BeautifulSoup(line[0], 'html.parser').find_all(
                'a', {"href": "/node/node-%s" % status})
            if len(val) == 1:
                found_status = status
                break
        assert found_status, 'Line does not match any known status'

        val = BeautifulSoup(line[2], 'html.parser').find_all(
            'form', {"method": "GET",
                     "action": "/catalogs/compare/node-%s" % found_status})
        assert len(val) == 1


def test_catalogs_json_compare(client, mocker,
                               mock_puppetdb_environments,
                               mock_puppetdb_default_nodes):
    app.app.config['ENABLE_CATALOG'] = True

    # below code checks last_total, which should be set after _query
    # so we need to simulate that. the value doesn't matter.
    app.puppetdb.last_total = 0
    rv = client.get('/catalogs/compare/node-unreported/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert 'data' in result_json

    for line in result_json['data']:
        assert len(line) == 3
        found_status = None
        for status in ['failed', 'changed', 'unchanged', 'noop', 'unreported']:
            val = BeautifulSoup(line[0], 'html.parser').find_all(
                'a', {"href": "/node/node-%s" % status})
            if len(val) == 1:
                found_status = status
                break
        assert found_status, 'Line does not match any known status'

        val = BeautifulSoup(line[2], 'html.parser').find_all(
            'form', {"method": "GET",
                     "action": "/catalogs/compare/node-unreported...node-%s" %
                               found_status})
        assert len(val) == 1
