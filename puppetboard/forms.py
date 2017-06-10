from __future__ import unicode_literals
from __future__ import absolute_import

from flask_wtf import FlaskForm
from wtforms import (
    HiddenField, RadioField, SelectField,
    TextAreaField, BooleanField, validators
)


class QueryForm(FlaskForm):
    """The form used to allow freeform queries to be executed against
    PuppetDB."""
    query = TextAreaField('Query', [validators.Required(
        message='A query is required.')])
    endpoints = RadioField('API endpoint', choices=[
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
        ('pql', 'PQL'),
    ])
    rawjson = BooleanField('Raw JSON')
