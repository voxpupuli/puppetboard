from flask import render_template
from werkzeug.exceptions import InternalServerError

from puppetboard.core import environments, get_app

app = get_app()


@app.errorhandler(400)
def bad_request(e):
    envs = environments()
    return render_template('400.html', envs=envs), 400


@app.errorhandler(403)
def forbidden(e):
    envs = environments()
    return render_template('403.html', envs=envs), 403


@app.errorhandler(404)
def not_found(e):
    envs = environments()
    return render_template('404.html', envs=envs), 404


@app.errorhandler(412)
def precond_failed(e):
    """We're slightly abusing 412 to handle missing features
    depending on the API version."""
    envs = environments()
    return render_template('412.html', envs=envs), 412


@app.errorhandler(500)
def server_error(e):
    envs = {}
    try:
        envs = environments()
    except InternalServerError:
        pass
    return render_template('500.html', envs=envs), 500
