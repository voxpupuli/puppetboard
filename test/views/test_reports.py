import json

from puppetboard import app
from test import MockDbQuery


def test_json_report_ok(client, mocker, input_data,
                        mock_puppetdb_environments,
                        mock_puppetdb_default_nodes):
    query_response = json.loads(input_data)

    query_data = {
        'reports': [
            {
                'validate': {
                    'data': query_response[:100],
                    'checks': {
                        'limit': 100,
                        'offset': 0
                    }
                }
            }
        ]
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    app.puppetdb.last_total = 499

    rv = client.get('/reports/json')

    assert rv.status_code == 200
    result_json = json.loads(rv.data.decode('utf-8'))

    assert 'data' in result_json
    assert len(result_json['data']) == 100
