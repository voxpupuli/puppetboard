"""Browser regressions; see README's CSV browser test instructions."""
import csv
import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from flask import render_template

from puppetboard import app
from puppetboard.core import get_app

playwright = pytest.importorskip("playwright.sync_api", reason="CSV browser tests require Playwright")
STATIC = Path(__file__).resolve().parents[2] / "puppetboard" / "static"


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as driver:
        instance = driver.chromium.launch()
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(accept_downloads=True)
    tab = context.new_page()
    tab.set_default_timeout(5000)
    errors = []
    tab.on("pageerror", lambda error: errors.append(str(error)))
    tab.route("http://puppetboard.test/", lambda route: route.fulfill(body="<html><body></body></html>"))
    tab.goto("http://puppetboard.test/")
    for filename in [
        "libs/jquery/jquery.min.js",
        "libs/datatables.net/jquery.dataTables.min.js",
        "libs/datatables.net-buttons/dataTables.buttons.min.js",
        "libs/datatables.net-buttons/buttons.html5.min.js",
        "libs/datatables.net-buttons/buttons.colVis.min.js",
        "libs/datatables.net-se/dataTables.semanticui.min.js",
        "libs/datatables.net-buttons-se/buttons.semanticui.min.js",
        "libs/moment.js/moment-with-locales.min.js",
        "js/pretty.js",
        "js/export.js",
        "js/utils.js",
    ]:
        tab.add_script_tag(path=str(STATIC / filename))
    yield tab
    context.close()
    assert not errors


def download_csv(page, button=0):
    try:
        with page.expect_download() as pending:
            page.get_by_role("button", name="Download as CSV", exact=True).nth(button).click()
    except playwright.TimeoutError:
        pytest.fail("No CSV download: " + " ".join(page.get_by_role("alert").all_text_contents()))
    download = pending.value
    assert download.suggested_filename.endswith(".csv")
    content = Path(download.path()).read_bytes()
    assert content.startswith(b"\xef\xbb\xbf")
    return list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))


def test_client_export_filters_all_pages_and_preserves_csv_values(page):
    page.evaluate("""() => {
      $('body').append('<table id="client"><thead><tr><th>Name</th><th>Value</th>' +
        '<th>Hidden</th><th></th></tr></thead></table>');
      window.table = $('#client').DataTable({
        data: [
          ['keep-2', 'comma, quote " and\\nnew line — café', 'secret', 'action'],
          ['omit', 'no', 'secret', 'action'],
          ['keep-1', '=1+1', 'secret', 'action']
        ],
        pageLength: 1,
        columnDefs: [{targets: 2, visible: false}]
      });
      table.search('keep').order([0, 'asc']).page(1).draw(false);
    }""")
    before = page.evaluate("JSON.stringify(table.page.info())")
    assert download_csv(page) == [
        ["Name", "Value"],
        ["keep-1", "'=1+1"],
        ["keep-2", 'comma, quote " and\nnew line — café'],
    ]
    assert page.evaluate("JSON.stringify(table.page.info())") == before


def test_server_export_fetches_all_batches_and_preserves_filters_and_page(page):
    requests = []
    rows = [[f'<a href="/node/{index}">node-{index:04d}</a>', f'value,{index}', 'action']
            for index in range(1005)]

    def respond(route):
        params = parse_qs(urlparse(route.request.url).query)
        requests.append(params)
        start = int(params["start"][0])
        length = int(params["length"][0])
        route.fulfill(json={
            "draw": int(params["draw"][0]),
            "recordsTotal": 3000,
            "recordsFiltered": len(rows),
            "data": rows[start:start + length],
        })

    page.route("http://puppetboard.test/reports/json*", respond)
    page.evaluate("""() => {
      $('body').append('<table id="server"><thead><tr><th>Name</th><th>Value</th>' +
        '<th class="no-export">Compare</th></tr></thead></table>');
      window.table = $('#server').DataTable({
        serverSide: true, ajax: '/reports/json', pageLength: 10,
        search: {search: 'node'}, order: [[0, 'desc']],
        searchCols: [{search: '{"min":"2026-01-01"}'}, null, null]
      });
    }""")
    page.wait_for_selector("#server tbody a")
    page.evaluate("table.page(2).draw(false)")
    page.wait_for_function("$('#server tbody a').first().text() === 'node-0020'")
    before = page.evaluate("JSON.stringify(table.page.info())")
    requests.clear()
    result = download_csv(page)
    assert len(result) == 1006
    assert result[0] == ["Name", "Value"]
    assert result[1] == ["node-0000", "value,0"]
    assert result[-1] == ["node-1004", "value,1004"]
    assert [request["start"] for request in requests] == [["0"], ["1000"]]
    assert all(request["length"] == ["1000"] for request in requests)
    assert all(request["search[value]"] == ["node"] for request in requests)
    assert all(request["order[0][dir]"] == ["desc"] for request in requests)
    assert all(request["columns[0][search][value]"] == ['{"min":"2026-01-01"}']
               for request in requests)
    assert page.evaluate("JSON.stringify(table.page.info())") == before
    assert page.locator(".csv-export-copy").count() == 0
    assert page.get_by_role("button", name="Download as CSV", exact=True).count() == 1


@pytest.mark.parametrize("failure", ["http", "invalid", "incomplete", "changed"])
def test_server_export_failure_is_visible_and_retryable(page, failure):
    downloads = []
    fail_export = True
    page.on("download", lambda download: downloads.append(download))

    def respond(route):
        params = parse_qs(urlparse(route.request.url).query)
        if fail_export and params["length"] == ["1000"]:
            if failure == "http":
                route.fulfill(status=500, body="Backend error")
                return
            if failure == "invalid":
                route.fulfill(json={"data": "invalid"})
                return
            if failure == "incomplete":
                route.fulfill(json={"recordsFiltered": 1001, "data": []})
                return
            start = int(params["start"][0])
            route.fulfill(json={
                "recordsFiltered": 1001 if start == 0 else 1002,
                "data": [[str(index)] for index in range(1000)] if start == 0 else [["last"]]
            })
            return
        route.fulfill(json={
            "draw": int(params["draw"][0]), "recordsTotal": 1, "recordsFiltered": 1,
            "data": [["first"]]
        })

    page.route("http://puppetboard.test/data*", respond)
    page.evaluate("""() => {
      $('body').append('<table id="failed"><thead><tr><th>Name</th></tr></thead></table>');
      $('#failed').DataTable({serverSide: true, ajax: '/data'});
    }""")
    page.wait_for_selector("#failed tbody td")
    button = page.get_by_role("button", name="Download as CSV", exact=True)
    button.click()
    alert = page.get_by_role("alert")
    alert.wait_for(state="visible")
    assert "CSV export failed:" in alert.inner_text()
    assert button.is_enabled()
    assert not downloads
    assert page.locator("#failed tbody td").inner_text() == "first"
    fail_export = False
    assert download_csv(page) == [["Name"], ["first"]]
    assert alert.is_hidden()


@pytest.mark.parametrize("value", [{"os": {"name": "Debian"}, "cpus": [1, 2]}, "<literal>, \"text\"\nnext", False, 0])
def test_fact_export_uses_original_value_not_pretty_html(page, value):
    page.evaluate("""() => {
      $('body').append('<table id="facts_table"><thead><tr><th>Node</th>' +
        '<th class="fact_value">Value</th></tr></thead></table>');
    }""")
    rows = [["node", json.dumps(["/fact/value", value])]]
    application = get_app()
    with application.test_request_context("/"):
        macro = application.jinja_env.get_template("_macros.html").module
        script = macro.datatable_init("facts_table", "/facts", None, 10, [10, 25], fact="os")
    page.route("http://puppetboard.test/facts*", lambda route: route.fulfill(json={
        "draw": 1, "recordsTotal": 1, "recordsFiltered": 1, "data": rows
    }))
    page.evaluate(script)
    page.wait_for_selector("#facts_table tbody a")
    result = download_csv(page)
    if isinstance(value, (dict, bool)):
        expected = json.dumps(value, separators=(",", ":"))
    else:
        expected = str(value)
    assert result == [["Node", "Value"], ["node", expected]]


def test_each_table_gets_its_own_export_and_retains_column_buttons(page):
    page.evaluate("""() => {
      $('body').append('<table id="one"><thead><tr><th>First</th></tr></thead></table>' +
        '<table id="two"><thead><tr><th>Second</th></tr></thead></table>');
      $('#one').DataTable({data: [['one']], dom: 'Bt', buttons: [
        {extend: 'colvisGroup', text: 'Minimal columns', show: [0]}
      ]});
      $('#two').DataTable({data: [['two']]});
    }""")
    assert download_csv(page, 0) == [["First"], ["one"]]
    assert download_csv(page, 1) == [["Second"], ["two"]]
    assert page.get_by_role("button", name="Minimal columns").is_visible()


@pytest.mark.parametrize("empty", [True, False])
def test_server_export_handles_hidden_columns_and_empty_results(page, empty):
    def respond(route):
        params = parse_qs(urlparse(route.request.url).query)
        route.fulfill(json={
            "draw": int(params["draw"][0]), "recordsTotal": 0 if empty else 1,
            "recordsFiltered": 0 if empty else 1,
            "data": [] if empty else [["one", "secret", "three"]],
        })

    page.route("http://puppetboard.test/hidden*", respond)
    page.evaluate("""() => {
      $('body').append('<table id="hidden"><thead><tr><th>First</th><th>Hidden</th>' +
        '<th>Third</th></tr></thead></table>');
      window.table = $('#hidden').DataTable({
        serverSide: true, ajax: '/hidden', columnDefs: [{targets: 1, visible: false}]
      });
    }""")
    page.wait_for_function("$('#hidden').DataTable().ajax.json() !== undefined")
    expected = [["First", "Third"]]
    if not empty:
        expected.append(["one", "three"])
    assert download_csv(page) == expected


def test_nodes_page_exports_with_bundled_offline_assets(
        page, client, monkeypatch, mock_puppetdb_environments, mock_puppetdb_default_nodes):
    application = get_app()
    monkeypatch.setitem(application.config, "OFFLINE_MODE", True)

    def respond(route):
        response = client.get(urlparse(route.request.url).path)
        route.fulfill(status=response.status_code, body=response.data,
                      content_type=response.content_type)

    page.route("http://puppetboard.test/**", respond)
    page.goto("http://puppetboard.test/nodes")
    page.locator("#main-table-search").fill("node-failed")
    result = download_csv(page)
    assert result[0] == ["Status", "Certname", "Catalog", "Report", "Facts"]
    assert len(result) == 2
    assert result[1][1] == "node-failed"


def test_query_page_preserves_structured_and_literal_values(
        page, client, monkeypatch, mocker, mock_puppetdb_environments):
    application = get_app()
    monkeypatch.setitem(application.config, "OFFLINE_MODE", True)
    monkeypatch.setitem(application.config, "WTF_CSRF_ENABLED", False)
    mocker.patch.object(app.puppetdb, "_query", return_value=[
                            {"certname": "node-a", "facts": {"items": ["a", "b"]},
                             "literal": '<literal>, "quoted"\nnext'}
                        ])
    response = client.post("/query", data={"query": "inventory {}", "endpoints": "pql"})
    assert response.status_code == 200

    def respond(route):
        path = urlparse(route.request.url).path
        if path == "/query":
            route.fulfill(body=response.data, content_type=response.content_type)
        else:
            static = client.get(path)
            route.fulfill(status=static.status_code, body=static.data,
                          content_type=static.content_type)

    page.route("http://puppetboard.test/**", respond)
    page.goto("http://puppetboard.test/query")
    result = download_csv(page)
    assert result == [
        ["certname", "facts", "literal"],
        ["node-a", '{"items":["a","b"]}', '<literal>, "quoted"\nnext'],
    ]


def test_report_tables_export_independently_and_keep_column_presets(page, client, monkeypatch):
    application = get_app()
    monkeypatch.setitem(application.config, "OFFLINE_MODE", True)
    start = datetime(2026, 1, 1)
    with application.test_request_context("/report/node-a/hash"):
        html = render_template(
            "report.html", current_env="*", envs={}, current_show_error_as="raw",
            report=SimpleNamespace(node="node-a", version="1", start=start,
                                   end=start + timedelta(seconds=10)),
            logs=[{"timestamp": "2026-01-01T00:00:01Z", "level": "notice",
                   "source": "Puppet", "tags": ["notice"], "message": "changed",
                   "location": "/etc/puppet/test.pp:1", "short_location": "test.pp:1"}],
            events=[{"resource": "File[/tmp/test]", "status": "success",
                     "old": "absent", "new": "present", "failed": False}],
            metrics=[{"category": "time", "name": "total", "value": 10}],
        )

    def respond(route):
        path = urlparse(route.request.url).path
        if path == "/report/node-a/hash":
            route.fulfill(body=html, content_type="text/html")
        else:
            response = client.get(path)
            route.fulfill(status=response.status_code, body=response.data,
                          content_type=response.content_type)

    page.route("http://puppetboard.test/**", respond)
    page.goto("http://puppetboard.test/report/node-a/hash")
    logs = download_csv(page, 0)
    assert logs[0] == ["Timestamp", "Level", "Message", "Location (short)"]
    assert logs[1][0] == "2026-01-01T00:00:01Z"
    assert page.get_by_role("button", name="Minimal columns").evaluate(
        "element => element.classList.contains('active')"
    )
    page.get_by_role("button", name="More columns (classic)").click()
    assert download_csv(page, 0)[0] == ["Timestamp", "Source", "Tags", "Message", "Location"]
    assert download_csv(page, 1) == [
        ["Resource", "Status", "Changed From", "Changed To"],
        ["File[/tmp/test]", "success", "absent", "present"],
    ]
    assert download_csv(page, 2) == [["Category", "Name", "Value"], ["time", "total", "10"]]
