# -*- coding: utf-8 -*-

"""
flask_apiexceptions
~~~~~~~~~~~~~~~~~~~

Base API exception classes.

:copyright: (c) Fictive Kin.

"""

from __future__ import absolute_import
from __future__ import print_function

__version_info__ = ('1', '1', '1')
__version__ = '.'.join(__version_info__)
__author__ = 'Joel Perras'
__copyright__ = '(c) 2018 Fictive Kin, LLC'
__all__ = ['JSONExceptionHandler', 'ApiException', 'ApiError',
           'api_exception_handler']


from flask import jsonify, request
from werkzeug.exceptions import default_exceptions, HTTPException

import logging
logger = logging.getLogger(__name__)


class JSONExceptionHandler(object):
    """
    A Flask extension that converts default Flask exceptions to their
    application/json content type equivalent.

    ```
    from application.libs import JSONExceptionHandler
    exception_handler = JSONExceptionHandler()
    exception_handler.init_app(app)
    ```

    """

    # If we don't know what HTTP code to assign an exception, by default
    # we assign it a `500`. This also handles uncaught exceptions; e.g.
    # if our application raises any kind of Exception subclass that we don't
    # explicitly have a handler for, then we've probably got an application
    # error somewhere for that particular code path.
    default_status_code = 500

    default_message = 'An error occurred!'

    def __init__(self, app=None):
        """
        Initialize the extension.

        Any default configurations that do not require the application
        instance should be put here.
        """

        if app:
            self.init_app(app)

    def default_handler(self, error=None):
        """Default error handler to register with the application."""

        if error is None:
            message = self.default_message
        else:
            # If the error object contains a `message` attribute, then let's
            # use that as the message for our exception.
            if hasattr(error, 'message'):
                message = error.message
            # Werkzeug default exception types use `description` instead
            # of `message`.
            elif hasattr(error, 'description'):
                message = error.description
            else:
                message = self.default_message

        response = jsonify(message=message)

        # If our error object contains a specific error code, then let's use
        # that. If not, we will use our `default_status_code` that has been
        # defined for this class. This ensures that random exceptions that
        # are thrown by Python or by external libraries that we miss are
        # an application error.
        response.status_code = self.default_status_code

        if hasattr(error, 'status_code'):
            response.status_code = int(error.status_code)
        elif isinstance(error, HTTPException):
            response.status_code = error.code

        if response.status_code >= 500:
            logger.exception(error)
        else:
            logger.debug(error)

        return response

    def init_app(self, app):
        """
        Initialize the extension with any application-level configuration
        requirements.

        This is where we register the Werkzeug `HTTPException` class along
        with all the other default exception codes.
        """

        self.app = app

        # Register the default HTTP codes to be handled by our exception
        # handler.
        for code, v in default_exceptions.items():
            self.register(code)

        if not hasattr(self.app, 'extensions'):
            self.app.extensions = {}

        self.app.extensions['apiexceptions'] = self

    def register(self, code_or_exception, handler=None):
        """
        Register an exception class *or* numeric code with the default
        exception handler provided by this extension *or* the function provided
        at `handler` in the argument.

        """
        f = handler or self.default_handler
        self.app.register_error_handler(code_or_exception, f=f)

    @staticmethod
    def handle_404(error=None):
        """The default Werkzeug 404 handler does not include a
        message or description, which causes some consistency issues with our
        frontends when receiving a 404."""

        message = 'The resource at {} could not be found.'.format(request.path)
        response = jsonify(message=message)
        response.status_code = 404
        return response


class ApiError(object):
    """
    Contains information related to an API usage error.

    - code: a semantically readable error slug, e.g. `invalid-password`
    - info: information regarding the source of the error.  E.g., if the
      error was caused by invalid submitted data, the info can contain
      a list of fields that contained the bad data.  E.g.,
      ['username', 'other_field']
    - message: a human-readable description of what went wrong.

    All of the above data will be serialized into JSON to be returned to the
    client.

    """
    def __init__(self, code=None, info=None, message=None):
        self.code = code
        self.info = info
        self.message = message

    def serialize(self):
        """
        Construct response dictionary.
        """
        return {'code': self.code,
                'info': self.info,
                'message': self.message}


class ApiException(Exception):
    """
    An exception that may be raised by various API view endpoints.

    Can contain one or more ApiError objects and must include a HTTP status
    code.
    """

    # Default status code if none is set.
    status_code = 500

    message = None

    code = None

    info = None

    def __init__(self, status_code=None, error=None, message=None, info=None,
                 code=None):
        """
        Initialize the ApiException container object.

        If an `error` instance is provided, it will be added as an error
        contained within this wrapper. If any of `message`, `info`, or `code`
        are set, a new error object is created added.
        """

        super(ApiException, self).__init__()

        self._errors = []
        if error is not None:
            self._errors.append(error)

        self.status_code = status_code or self.status_code
        message = message or self.message
        code = code or self.code
        info = info or self.info

        if message or info or code:
            self.add_error(ApiError(message=message, code=code, info=info))

    def add_error(self, error):
        """
        Append an error to the list of errors contained with this
        ApiException instance.
        """
        self._errors.append(error)

    @property
    def errors(self):
        return self._errors

    def serialize(self):
        """
        Serialize the errors contained within this ApiException object to
        Python types that are easily convertible to JSON (or similar).
        """
        return {'errors': [e.serialize() for e in self.errors]}


def api_exception_handler(api_exception):
    """
    Jsonify and serialize ApiException-compatible objects and assign
    the correct response code.
    """
    response = jsonify(api_exception.serialize())
    response.status_code = api_exception.status_code
    return response
