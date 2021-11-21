from puppetboard import app
from puppetboard.views.query import QueryForm


def test_form_valid(capsys):
    for form in [QueryForm]:
        with app.app.test_request_context():
            qf = form()
            out, err = capsys.readouterr()
            assert qf is not None
            assert err == ""
            assert out == ""
