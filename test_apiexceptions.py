"""
test_apiexceptions
~~~~~~~~~~~~~~~~~~

Tests for Flask-APIExceptions extension and related functionality.

"""

import pytest
import flask
from flask import json, jsonify
from flask_apiexceptions import (
    JSONExceptionHandler, ApiException, api_exception_handler, ApiError)


@pytest.fixture
def app():
    """Flask application fixture."""

    app = flask.Flask(__name__)
    return app


def test_initialize_extension(app):

    assert 'apiexceptions' not in getattr(app, 'extensions', dict())

    JSONExceptionHandler(app)

    assert 'apiexceptions' in app.extensions
    assert isinstance(app.extensions['apiexceptions'],
                      JSONExceptionHandler)


def test_deferred_init_app(app):
    """Deferred initialization test."""

    assert 'apiexceptions' not in getattr(app, 'extensions', dict())

    ext = JSONExceptionHandler()
    ext.init_app(app)

    assert 'apiexceptions' in app.extensions
    assert isinstance(app.extensions['apiexceptions'],
                      JSONExceptionHandler)


def test_register_exception_type(app):
    """Register an exception type with the default handler."""

    class CustomError(Exception):
        message = 'A custom error message'

    @app.route('/testing')
    def testing():
        raise CustomError()

    ext = JSONExceptionHandler(app)
    ext.register(code_or_exception=CustomError)

    with app.app_context():
        with app.test_client() as c:
            rv = c.get('/testing')

    assert rv.status_code == 500  # Default status code.
    assert rv.headers['content-type'] == 'application/json'
    assert json.loads(rv.data)['message'] == 'A custom error message'


def test_register_exception_code_and_handler(app):
    """Handle Flask 404s with JSONExceptionHandler."""

    ext = JSONExceptionHandler(app)
    ext.register(code_or_exception=404,
                 handler=JSONExceptionHandler.handle_404)

    with app.app_context():
        with app.test_client() as c:
            rv = c.get('/notfound')

    assert rv.status_code == 404
    assert rv.headers['content-type'] == 'application/json'
    assert json.loads(rv.data)['message'] == ('The resource at /notfound could'
                                              ' not be found.')


def test_register_exception_class_and_handler(app):
    """Custom exception handling."""

    class CustomError(Exception):
        teapot_code = 418
        special = {'foo': 'bar'}

    def custom_handler(error):
        response = jsonify(data=error.special)
        response.status_code = error.teapot_code
        return response

    @app.route('/testing')
    def testing():
        raise CustomError()

    ext = JSONExceptionHandler(app)
    ext.register(code_or_exception=CustomError, handler=custom_handler)

    with app.app_context():
        with app.test_client() as c:
            rv = c.get('/testing')

    assert rv.status_code == 418
    assert rv.headers['content-type'] == 'application/json'
    assert json.loads(rv.data)['data'] == CustomError.special


def test_api_exception_handler(app):
    """Use JSONExceptionHandler.api_exception_handler to capture ApiException
    objects that are raised."""

    @app.route('/custom')
    def testing():
        error = ApiError(code='teapot', message='I am a little teapot.')
        raise ApiException(status_code=418, error=error)

    ext = JSONExceptionHandler(app)
    ext.register(code_or_exception=ApiException, handler=api_exception_handler)

    with app.app_context():
        with app.test_client() as c:
            rv = c.get('/custom')

    assert rv.status_code == 418
    assert rv.headers['content-type'] == 'application/json'

    json_data = json.loads(rv.data)
    assert json_data['errors'][0]['message'] == 'I am a little teapot.'
    assert json_data['errors'][0]['code'] == 'teapot'
    assert json_data['errors'][0]['info'] is None


def test_exception_auto_populate_error():
    """If no ApiError object is provided, create one by default in
    ApiException."""

    exc = ApiException(
        status_code=418,
        code='bad_inputs',
        message='Something happened.',
        info={'key': 'value'})

    assert len(exc.errors) == 1
    assert isinstance(exc.errors[0], ApiError)
    assert exc.errors[0].code == 'bad_inputs'
    assert exc.errors[0].message == 'Something happened.'
    assert exc.errors[0].info == {'key': 'value'}

    exc = ApiException(
        status_code=418,
        code='bad_inputs')

    assert len(exc.errors) == 1
    assert isinstance(exc.errors[0], ApiError)
    assert exc.errors[0].code == 'bad_inputs'
    assert exc.errors[0].message is None
    assert exc.errors[0].info is None

    exc = ApiException(
        status_code=418,
        message='Whoopsie! That is no good.')

    assert len(exc.errors) == 1
    assert isinstance(exc.errors[0], ApiError)
    assert exc.errors[0].info is None
    assert exc.errors[0].code is None
    assert exc.errors[0].message == 'Whoopsie! That is no good.'

    exc = ApiException(
        status_code=418,
        info={'key': 'value'})

    assert len(exc.errors) == 1
    assert isinstance(exc.errors[0], ApiError)
    assert exc.errors[0].info == {'key': 'value'}
    assert exc.errors[0].code is None
    assert exc.errors[0].message is None


def test_api_exception_subclass_variations(app):
    """Subclass ApiException with class attribute descriptors."""

    class CustomError(ApiException):
        status_code = 418
        message = "A class attribute exception message."
        code = 'class-attribute'
        info = {'foo': 'bar'}

    @app.route('/testing')
    def testing():
        raise CustomError()

    ext = JSONExceptionHandler(app)

    # Use the api_exception_handler since CustomError is a subclass of
    # ApiException
    ext.register(code_or_exception=CustomError, handler=api_exception_handler)

    with app.app_context():
        with app.test_client() as c:
            rv = c.get('/testing')

    assert rv.status_code == 418
    assert rv.headers['content-type'] == 'application/json'
    assert json.loads(rv.data)['errors'] == [
        {'code': CustomError.code,
         'message': CustomError.message,
         'info': CustomError.info}]
