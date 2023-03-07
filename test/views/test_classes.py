import json

from bs4 import BeautifulSoup

from puppetboard import app
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
