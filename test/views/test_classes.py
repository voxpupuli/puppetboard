import json
from types import SimpleNamespace

from bs4 import BeautifulSoup
from pypuppetdb.types import Node

from puppetboard import app
from puppetboard.views import classes as classes_view
from test import MockDbQuery

import pprint
import logging


def test_classes_disabled(client, mocker,
                          mock_puppetdb_environments,
                          mock_puppetdb_default_nodes):
    app.app.config['ENABLE_CLASS'] = False
    rv = client.get('/classes')
    assert rv.status_code == 403


def test_classes_view(client, mocker,
                      mock_puppetdb_environments,
                      mock_puppetdb_default_nodes):
    app.app.config['ENABLE_CLASS'] = True

    rv = client.get('/classes')
    assert rv.status_code == 200
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'


def test_class_resource_view(client, mocker,
                             mock_puppetdb_environments,
                             mock_puppetdb_default_nodes):
    app.app.config['ENABLE_CLASS'] = True

    rv = client.get('/class_resource/My::Class')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    vals = soup.find_all('h1', {"id": "class_name"})
    assert len(vals) == 1
    assert 'My::Class' in vals[0].string


def mock_class_events(mocker, node_name, class_name):
    node = Node('_', node_name, latest_report_hash='1234567',
                report_timestamp='2013-08-01T09:57:00.000Z',
                status_report='failed')
    mocker.patch.object(app.puppetdb, 'nodes',
                        side_effect=lambda *a, **kw: iter([node]))
    event = SimpleNamespace(item={'class': class_name}, status='failure')
    report = SimpleNamespace(events=lambda: iter([event]))
    mocker.patch.object(app.puppetdb, 'reports',
                        side_effect=lambda *a, **kw: iter([report]))
    mocker.patch.object(classes_view.cache, 'get', return_value=None)


def test_classes_json_escapes_class_name(client, mocker,
                                        mock_puppetdb_environments):
    xss = '<b>My::Class</b>'
    mock_class_events(mocker, 'node-failed', xss)

    rv = client.get('/classes/json')
    assert rv.status_code == 200

    line = json.loads(rv.data.decode('utf-8'))['data'][0]
    link = BeautifulSoup(line[0], 'html.parser').find('a')
    assert link.find('b') is None
    assert link.text == xss


def test_class_resource_json_escapes_node_name(client, mocker,
                                               mock_puppetdb_environments):
    xss = '<b>node</b>'
    mock_class_events(mocker, xss, 'My::Class')

    rv = client.get('/class_resource/My::Class/json')
    assert rv.status_code == 200

    line = json.loads(rv.data.decode('utf-8'))['data'][0]
    link = BeautifulSoup(line[0], 'html.parser').find('a')
    assert link.find('b') is None
    assert link.text == xss
