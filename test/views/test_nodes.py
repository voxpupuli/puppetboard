from bs4 import BeautifulSoup


def test_default_node_view(client, mocker,
                           mock_puppetdb_environments,
                           mock_puppetdb_default_nodes):
    rv = client.get('/nodes')
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    for label in ['failed', 'changed', 'unreported', 'noop']:
        vals = soup.find_all('a',
                             {"class": "ui %s label status" % label})
        assert len(vals) == 1
        assert 'node-%s' % label in vals[0].attrs['href']

    headers = [header.get_text(strip=True)
               for header in soup.select('#main-table thead th')]
    assert 'Facts' in headers
    facts_column_index = headers.index('Facts')

    rows = soup.select('#main-table tbody tr')
    assert len(rows) >= 5

    facts_cells = [row.select('td')[facts_column_index] for row in rows]
    assert all(cell.get('data-order') for cell in facts_cells)
    assert all(cell.find('a') is not None for cell in facts_cells)

    assert rv.status_code == 200


def test_node_view(client, mocker,
                   mock_puppetdb_environments,
                   mock_puppetdb_default_nodes):
    rv = client.get('/node/node-failed')
    assert rv.status_code == 200

    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'

    vals = soup.find_all('table', {"id": "facts_table"})
    assert len(vals) == 1

    vals = soup.find_all('table', {"id": "reports_table"})
    assert len(vals) == 1
