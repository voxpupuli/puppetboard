from types import SimpleNamespace

from pypuppetdb.types import Node

from puppetboard import app


def test_failures_escapes_error(client, mocker,
                                mock_puppetdb_environments,
                                mock_puppetdb_default_nodes):
    xss = '<script>alert(1)</script>'
    report = SimpleNamespace(logs=[
        {'level': 'err', 'source': xss, 'message': xss},
    ])
    mocker.patch.object(app.puppetdb, 'reports',
                        side_effect=lambda *a, **kw: iter([report]))

    for show_error_as in ['friendly', 'raw']:
        rv = client.get(f'/failures/{show_error_as}', follow_redirects=True)
        assert rv.status_code == 200

        page = rv.data.decode('utf-8')
        assert xss not in page
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in page


def test_failures_escapes_fallback_message(client, mocker,
                                           mock_puppetdb_environments):
    xss = '<b>node</b>'
    node = Node('_', xss, latest_report_hash='1234567',
                report_timestamp='2013-08-01T09:57:00.000Z',
                status_report='failed')
    mocker.patch.object(app.puppetdb, 'nodes',
                        side_effect=lambda *a, **kw: iter([node]))
    # no error logs, so the generic message is shown
    report = SimpleNamespace(logs=[
        {'level': 'notice', 'source': 'Puppet', 'message': 'done'},
    ])
    mocker.patch.object(app.puppetdb, 'reports',
                        side_effect=lambda *a, **kw: iter([report]))

    rv = client.get('/failures', follow_redirects=True)
    assert rv.status_code == 200

    page = rv.data.decode('utf-8')
    assert xss not in page
    assert 'Node &lt;b&gt;node&lt;/b&gt; is failing' in page
