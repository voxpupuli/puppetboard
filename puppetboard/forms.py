from collections import OrderedDict

from flask_wtf import FlaskForm
from wtforms import (BooleanField, SelectField, TextAreaField, validators)

from puppetboard.core import get_app

app = get_app()
QUERY_ENDPOINTS = OrderedDict([
    # PuppetDB API endpoint, Form name
    ('pql', 'PQL'),
    ('nodes', 'Nodes'),
    ('resources', 'Resources'),
    ('facts', 'Facts'),
    ('factsets', 'Fact Sets'),
    ('fact-paths', 'Fact Paths'),
    ('fact-contents', 'Fact Contents'),
    ('reports', 'Reports'),
    ('events', 'Events'),
    ('catalogs', 'Catalogs'),
    ('edges', 'Edges'),
    ('environments', 'Environments'),
])
ENABLED_QUERY_ENDPOINTS = app.config.get(
    'ENABLED_QUERY_ENDPOINTS', list(QUERY_ENDPOINTS.keys()))


class QueryForm(FlaskForm):
    """The form used to allow freeform queries to be executed against
    PuppetDB."""
    query = TextAreaField('Query', [validators.DataRequired(
        message='A query is required.')])
    endpoints = SelectField('API endpoint', choices=[
        (key, value) for key, value in QUERY_ENDPOINTS.items()
        if key in ENABLED_QUERY_ENDPOINTS], default='pql')
    rawjson = BooleanField('Raw JSON')
