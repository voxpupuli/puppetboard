from __future__ import unicode_literals
from __future__ import absolute_import

from flask.ext.wtf import Form
from wtforms import (
    HiddenField, RadioField, SelectField,
    TextAreaField, validators
)


class QueryForm(Form):
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
        ])

class CatalogForm(Form):
    """The form used to compare the catalogs of different nodes."""
    compare = HiddenField('compare')
    against = SelectField('against')
