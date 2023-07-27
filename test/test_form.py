from puppetboard import forms
from puppetboard.core import get_app

app = get_app()
app.config['SECRET_KEY'] = 'the random string'


def test_form_valid(capsys):
    for form in [forms.QueryForm]:
        with app.test_request_context():
            qf = form()
            out, err = capsys.readouterr()
            assert qf is not None
            assert err == ""
            assert out == ""
