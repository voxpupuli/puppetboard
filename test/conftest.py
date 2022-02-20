import os

import pytest
from pypuppetdb.types import Node

from puppetboard import app


@pytest.fixture
def mock_puppetdb_environments(mocker):
    environments = [
        {'name': 'production'},
        {'name': 'staging'}
    ]
    return mocker.patch.object(app.puppetdb, 'environments',
                               return_value=environments)


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
    ]
    return mocker.patch.object(app.puppetdb, 'nodes',
                               return_value=iter(node_list))


@pytest.fixture
def input_data(request):
    data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'data')
    with open('%s/%s' % (data_path, request.function.__name__), "r") as fp:
        data = fp.read()
    return data


@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    client = app.app.test_client()
    return client
