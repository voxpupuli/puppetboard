from bs4 import BeautifulSoup

from puppetboard import app
from . import MockDbQuery


def test_first_test():
    assert app is not None


def test_no_env(client, mock_puppetdb_environments):
    rv = client.get('/nonexistent/')

    assert rv.status_code == 404


def test_offline_mode(client, mocker,
                      mock_puppetdb_environments,
                      mock_puppetdb_default_nodes):
    app.app.config['OFFLINE_MODE'] = True

    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/')
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == 'Puppetboard'
    for link in soup.find_all('link'):
        assert "//" not in link['href']
        if 'offline' in link['href']:
            rv = client.get(link['href'])
            assert rv.status_code == 200

    for script in soup.find_all('script'):
        if "src" in script.attrs:
            assert "//" not in script['src']

    assert rv.status_code == 200


def test_offline_static(client):
    rv = client.get('/offline/css/google_fonts.css')

    assert 'Content-Type' in rv.headers
    assert 'text/css' in rv.headers['Content-Type']
    assert rv.status_code == 200

    rv = client.get('/offline/Semantic-UI-2.1.8/semantic.min.css')
    assert 'Content-Type' in rv.headers
    assert 'text/css' in rv.headers['Content-Type']
    assert rv.status_code == 200


def test_health_status(client):
    rv = client.get('/status')

    assert rv.status_code == 200
    assert rv.data.decode('utf-8') == 'OK'


def test_custom_title(client, mocker,
                      mock_puppetdb_environments,
                      mock_puppetdb_default_nodes):

    default_title = app.app.config['PAGE_TITLE']

    custom_title = 'Dev - Puppetboard'
    app.app.config['PAGE_TITLE'] = custom_title

    query_data = {
        'nodes': [[{'count': 10}]],
        'resources': [[{'count': 40}]],
    }

    dbquery = MockDbQuery(query_data)

    mocker.patch.object(app.puppetdb, '_query', side_effect=dbquery.get)
    rv = client.get('/')
    soup = BeautifulSoup(rv.data, 'html.parser')
    assert soup.title.contents[0] == custom_title

    # restore the global state
    app.app.config['PAGE_TITLE'] = default_title
