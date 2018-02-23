Flask-ApiExceptions
===================

Flask-ApiExceptions is a Flask extension that provides the basic
functionality for serializing uncaught exceptions as HTTP responses for
a JSON-based REST API.

Installation
------------

You can install this extension with ``pip``:

.. code:: bash

    $ pip install flask_apiexceptions

Or, you can clone the repository:

.. code:: bash

    $ git clone https://github.com/jperras/flask_apiexceptions.git

Running the Tests
-----------------

`Tox <https://pypi.python.org/pypi/tox>`__ is used to run the tests,
which are written using `PyTest <https://docs.pytest.org/en/latest/>`__.
To run them, clone the repository (indicated above), ensure ``tox`` is
installed and available, and run:

.. code:: bash

    $ cd path/to/flask_apiexceptions
    $ tox

Usage
-----

This package includes an extension named ``JSONExceptionHandler``, which
can be added to your application in the usual way:

::

    from flask import Flask
    from flask_apiexceptions import JSONExceptionHandler

    app = Flask(__name__)
    exception_handler = JSONExceptionHandler(app)

The extension can also be initialized via deferred application init if
you’re using an application factory:

::

    exception_handler = JSONExceptionHandler()
    exception_hander.init_app(app)

Once initialized, the extension doesn’t actually do anything by default.
You’ll have to configure it to handle Werkzeug HTTP error codes or
custom ``Exception`` classes.

Custom Exception Class Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An example showing how we can raise a custom exception within a view
method, and have that exception be transformed into a JSON response:

.. code:: python

    class MissingUserError(Exception):
        status_code = 404
        message = 'No such user exists.'

    @app.route('/not-found')
    def testing():
        raise MissingUserError()

    ext = JSONExceptionHandler(app)
    ext.register(code_or_exception=MissingUserError)

    with app.app_context():
        with app.test_client() as c:
            rv = c.get('/not-found')

    assert rv.status_code == 404
    assert rv.headers['content-type'] == 'application/json'
    assert json.loads(rv.data)['message'] == 'No such user exists.'

This uses the ``JSONExceptionHandler.default_handler()`` to transform
the ``CustomError`` exception class into a suitable response. It
attempts to introspect the exception instance returned for a ``message``
or ``description`` attribute, and also checks to see if there exists a
``status_code`` attribute.

If any of those fields are found, the default handler will populate the
response data with the given message, and set the response status code.
If no message or status code is present, a default response of
``{"message": "An error occurred!"}`` with an
``HTTP/1.1 500 Internal Server Error`` status code is set.

If you’d like to handle custom exception classes in a different manner,
say because you have more complex data captured within an exception
instance, or the attributes are not conveniently named ``message`` or
``description``, then you can specify a custom handler for the exception
type:

.. code:: python

    from flask_apiexceptions import JSONExceptionHandler

    app = Flask(__name__)
    ext = JSONExceptionHandler(app)

    class CaffeineError(Exception):
        teapot_code = 418
        special = {'foo': 'bar'}

    def caffeine_handler(error):
        response = jsonify(data=error.special)
        response.status_code = error.teapot_code
        return response

    @app.route('/testing')
    def testing():
        raise CaffeineError()

    ext.register(code_or_exception=CaffeineError, handler=caffeine_handler)

    with app.app_context():
        with app.test_client() as c:
            rv = c.get('/testing')

    assert rv.status_code == 418
    assert rv.headers['content-type'] == 'application/json'
    assert json.loads(rv.data)['data'] == CaffeineError.special

This is also how, incidentally, you could use a response content type
other than ``application/json``. Simply construct your own response
object isntead of using ``jsonify()`` within your handler, as long as it
produces a valid response as a return value.

Using ``ApiException`` and ``ApiError`` objects
-----------------------------------------------

``Flask-ApiExceptions`` includes a few convenience classes and a handler
method for setting up structured API error responses. They are entirely
optional, but provide some sane defaults that should cover most
situatiosn.

An ``ApiException`` instance wraps one or more ``ApiError`` instances.
In this sense the ``ApiException`` is simply the container for the
actual error message. The ``ApiError`` instance accepts optional
``code``, ``message``, and ``info`` attributes.

The idea is that the ``code`` should be an identifier for the type of
error, for example ``invalid-data`` or ``does-not-exist``. The
``message`` field should provide a more detailed and precise description
of the error. The ``info`` field can be used for any additional metadata
or unstructured information that may be required.

The ``info`` field, if utilized, should contain data that is JSON
serializable.

To use these constructs, you need to register the appropriate exception
class as well as an ``api_exception_handler`` that is provided for just
this purpose:

.. code:: python

    from flask_apiexceptions import (
        JSONExceptionHandler, ApiException, ApiError, api_exception_handler)

    app = Flask(__name__)
    ext = JSONExceptionHandler(app)
    ext.register(code_or_exception=ApiException, handler=api_exception_handler)

    @app.route('/custom')
    def testing():
        error = ApiError(code='teapot', message='I am a little teapot.')
        raise ApiException(status_code=418, error=error)


    with app.app_context():
        with app.test_client() as c:
            rv = c.get('/custom')

            # JSON response looks like...
            # {"errors": [{"code": "teapot", "message": "I am a little teapot."}]}

    assert rv.status_code == 418
    assert rv.headers['content-type'] == 'application/json'

    json_data = json.loads(rv.data)
    assert json_data['errors'][0]['message'] == 'I am a little teapot.'
    assert json_data['errors'][0]['code'] == 'teapot'
    assert json_data['errors'][0]['info'] is None

Note that, when using the ``ApiException`` and ``ApiError`` classes, the
status code is set on the ``ApiException`` instance. This makes more
sense when you can set multiple ``ApiError`` objects to the same
``ApiException``:

.. code:: python

    from flask_apiexceptions import ApiException, ApiError

    # ...

    @app.route('/testing')
    def testing():
        exc = ApiException(status_code=400)
        invalid_address_error = ApiError(code='invalid-data',
                                         message='The address provided is invalid.')
        invalid_phone_error = ApiError(code='invalid-data',
                                       message='The phone number does not exist.',
                                       info={'area_code': '555'})
        exc.add_error(invalid_address_error)
        exc.add_error(invalid_phone_error)

        raise exc

        # JSON response format:
        # {"errors": [
        #     {"code": "invalid-data", "message": "The address provided is invalid."},
        #     {"code": "invalid-data", "message": "The phone number does not exist.", "info": {"area_code": "444"}}
        # ]}

If you only want a single ``error`` to be instantiated within the
``ApiException``, this can be done via the constructor of the latter as a
shorthand:

.. code:: python

    exc = ApiException(
        status_code=400,
        code='invalid-data',
        message='The address provided is invalid',
        info={'zip_code': '90210'})

which is the equivalent of:

.. code:: python

    exc = ApiException(status_code=400)
    error=ApiError(
        code='invalid-data',
        message='The address provided is invalid',
        info={'zip_code': '90210'}))

    exc.add_error(error)

A useful pattern is to subclass ``ApiException`` into distinctly useful
exception types, on which you can define default class-level attributes that
will be used to populate the correct ``error`` object on instantiation. For
example:

.. code:: python

    class MissingResourceError(ApiException):
        status_code = 404
        message = "No such resource exists."
        code = 'not-found'

    # ...

    @app.route('/posts/<int:post_id>')
    def post_by_id(post_id):
        """Fetch a single post by ID from the database."""

        post = Post.query.filter(Post.id == post_id).one_or_none()
        if post is None:
            raise MissingResourceError()

        # 404 response, wiht JSON body:
        # {"errors": [
        #     {"code": "not-found", "message": "No such resource exists."}
        # ]}

The nice thing about this particular pattern is that you can raise
*semantically correct* exceptions within your codebase, and can choose to
handle them in the call stack. If you don't handle them, they simply bubble up
to the exception handler (if you've configured the
``flask_apiexceptions.api_exception_handler`` or similar) registered with
Flask, and are then transformed into a useful response for the requesting client.

.. code:: python

    class MissingResourceError(ApiException):
        status_code = 404
        message = "No such resource exists."
        code = 'not-found'

    class Post(db.Model):
        # ...
        @classmethod
        def query_by_id(cls, post_id):
            """Query Post by ID, raise exception if not found."""
            result = cls.query.filter(cls.id == post_id).one_or_none()
            if result is None:
                raise MissingResourceError()

            return result

    @app.route('/posts/<int:post_id>')
    def post_by_id(post_id):
        """Fetch a single post by ID from the database."""

        try:
            post = Post.query_by_id(post_id)
        except MissingResourceError as e:
            # We can do whatever we want now that we've caught the exception.
            # For the sake of illustration, we're just going to log it.
            app.logger.exception("Could not locate post!")

            # Will bubble up the exception until it is rendered to JSON
            # for the client.
            raise e
