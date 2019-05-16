from __future__ import unicode_literals
from __future__ import absolute_import

from flask_wtf import FlaskForm
from wtforms import (
    HiddenField, RadioField, SelectField,
    TextAreaField, BooleanField, StringField,
    PasswordField, validators
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


class LoginForm(FlaskForm):
    """The form used to login to Puppetboard"""
    username = StringField('Username', [validators.DataRequired(message='Username is required')])
    password = PasswordField('Password', [validators.DataRequired(message='Password is required')])
    remember = BooleanField('Remember me')
