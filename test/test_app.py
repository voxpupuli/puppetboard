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
    offline_statics = [
        {
            "content_type": 'text/css',
            "assets": [
                "static/libs/fomantic-ui/semantic.min.css",
                "static/libs/datatables.net-se/dataTables.semanticui.min.css",
                "static/libs/datatables.net-buttons-se/buttons.semanticui.min.css",
                "static/libs/billboard.js/billboard.min.css",
                "static/css/fonts.css",
            ]
        },
        {
            "content_type": 'application/javascript',
            "assets": [
                "static/libs/moment.js/moment-with-locales.min.js",
                "static/libs/jquery/jquery.min.js",
                "static/libs/fomantic-ui/semantic.min.js",
                "static/libs/datatables.net/jquery.dataTables.min.js",
                "static/libs/datatables.net-buttons/dataTables.buttons.min.js",
                "static/libs/datatables.net-buttons/buttons.html5.min.js",
                "static/libs/datatables.net-buttons/buttons.colVis.min.js",
                "static/libs/datatables.net-buttons-se/buttons.semanticui.min.js",
                "static/libs/datatables.net-se/dataTables.semanticui.min.js",
                "static/libs/billboard.js/billboard.pkgd.min.js",
            ]

        }
    ]

    for category_statics in offline_statics:
        content_type = category_statics.get('content_type')

        for asset in category_statics.get('assets'):
            rv = client.get(asset)

            assert 'Content-Type' in rv.headers
            assert content_type in rv.headers['Content-Type']
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
