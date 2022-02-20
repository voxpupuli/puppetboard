import json

import pytest
from pypuppetdb.types import Fact

from puppetboard import app
from puppetboard.views.inventory import inventory_facts


@pytest.fixture
def mock_puppetdb_inventory_facts(mocker):
    nodes = ['node1', 'node2']
    facts_list = [
        Fact(
            node=node,
            name=fact_name,
            value='foobar',
            environment='production',
        )
        for node in nodes
        for fact_name in inventory_facts()[1]  # fact names
    ]
    return mocker.patch.object(app.puppetdb, 'facts', return_value=iter(facts_list))


def test_inventory_json(client, mocker,
                        mock_puppetdb_environments,
                        mock_puppetdb_inventory_facts):

    rv = client.get('/inventory/json')
    assert rv.status_code == 200

    result_json = json.loads(rv.data.decode('utf-8'))
    assert len(result_json['data']) == 2
