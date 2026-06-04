Logging
=======

Flask uses standard Python :mod:`logging`. Messages about your Flask
application are logged with :meth:`app.logger <flask.Flask.logger>`,
which takes the same name as :attr:`app.name <flask.Flask.name>`. This
logger can also be used to log your own messages.

.. code-block:: python

    @app.route('/login', methods=['POST'])
    def login():
        user = get_user(request.form['username'])

        if user.check_password(request.form['password']):
            login_user(user)
            app.logger.info('%s logged in successfully', user.username)
            return redirect(url_for('index'))
        else:
            app.logger.info('%s failed to log in', user.username)
            abort(401)

If you don't configure logging, Python's default log level is usually
'warning'. Nothing below the configured level will be visible.


Basic Configuration
-------------------

When you want to configure logging for your project, you should do it as soon
as possible when the program starts. If :meth:`app.logger <flask.Flask.logger>`
is accessed before logging is configured, it will add a default handler. If
possible, configure logging before creating the application object.

This example uses :func:`~logging.config.dictConfig` to create a logging
configuration similar to Flask's default, except for all logs::

    from logging.config import dictConfig

    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi']
        }
    })

    app = Flask(__name__)


Default Configuration
`````````````````````

If you do not configure logging yourself, Flask will add a
:class:`~logging.StreamHandler` to :meth:`app.logger <flask.Flask.logger>`
automatically. During requests, it will write to the stream specified by the
WSGI server in ``environ['wsgi.errors']`` (which is usually
:data:`sys.stderr`). Outside a request, it will log to :data:`sys.stderr`.


Removing the Default Handler
````````````````````````````

If you configured logging after accessing
:meth:`app.logger <flask.Flask.logger>`, and need to remove the default
handler, you can import and remove it::

    from flask.logging import default_handler

    app.logger.removeHandler(default_handler)


Email Errors to Admins
----------------------

When running the application on a remote server for production, you probably
won't be looking at the log messages very often. The WSGI server will probably
send log messages to a file, and you'll only check that file if a user tells
you something went wrong.

To be proactive about discovering and fixing bugs, you can configure a
:class:`logging.handlers.SMTPHandler` to send an email when errors and higher
are logged. ::

    import logging
    from logging.handlers import SMTPHandler

    mail_handler = SMTPHandler(
        mailhost='127.0.0.1',
        fromaddr='server-error@example.com',
        toaddrs=['admin@example.com'],
        subject='Application Error'
    )
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))

    if not app.debug:
        app.logger.addHandler(mail_handler)

This requires that you have an SMTP server set up on the same server. See the
Python docs for more information about configuring the handler.


Injecting Request Information
-----------------------------

Seeing more information about the request, such as the IP address, may help
debugging some errors. You can subclass :class:`logging.Formatter` to inject
your own fields that can be used in messages. You can change the formatter for
Flask's default handler, the mail handler defined above, or any other
handler. ::

    from flask import has_request_context, request
    from flask.logging import default_handler

    class RequestFormatter(logging.Formatter):
        def format(self, record):
            if has_request_context():
                record.url = request.url
                record.remote_addr = request.remote_addr
            else:
                record.url = None
                record.remote_addr = None

            return super().format(record)

    formatter = RequestFormatter(
        '[%(asctime)s] %(remote_addr)s requested %(url)s\n'
        '%(levelname)s in %(module)s: %(message)s'
    )
    default_handler.setFormatter(formatter)
    mail_handler.setFormatter(formatter)


Other Libraries
---------------

Other libraries may use logging extensively, and you want to see relevant
messages from those logs too. The simplest way to do this is to add handlers
to the root logger instead of only the app logger. ::

    from flask.logging import default_handler

    root = logging.getLogger()
    root.addHandler(default_handler)
    root.addHandler(mail_handler)

Depending on your project, it may be more useful to configure each logger you
care about separately, instead of configuring only the root logger. ::

    for logger in (
        logging.getLogger(app.name),
        logging.getLogger('sqlalchemy'),
        logging.getLogger('other_package'),
    ):
        logger.addHandler(default_handler)
        logger.addHandler(mail_handler)


Werkzeug
````````

Werkzeug logs basic request/response information to the ``'werkzeug'`` logger.
If the root logger has no handlers configured, Werkzeug adds a
:class:`~logging.StreamHandler` to its logger.


Flask Extensions
````````````````

Depending on the situation, an extension may choose to log to
:meth:`app.logger <flask.Flask.logger>` or its own named logger. Consult each
extension's documentation for details.


Structured Logging
------------------

Flask now includes built-in support for structured logging, which provides
several benefits for debugging and monitoring your application:

- **Request ID Generation**: Each request is automatically assigned a unique
  request ID for traceability.
- **Request Context Logging**: Every log message automatically includes the
  current request ID when a request is active.
- **Request Completion Logs**: Detailed logs for each completed request,
  including method, path, status code, and duration.
- **Enhanced Exception Logging**: Exceptions include the request ID and full
  stack trace for easier debugging.


Enabling Structured Logging
```````````````````````````

To use structured logging, you can configure Flask's built-in
:class:`~flask.logging.StructuredFormatter` with your logging handlers.
This formatter outputs JSON logs with rich context information.

Here's a minimal configuration example::

    import logging
    from flask import Flask
    from flask.logging import StructuredFormatter

    app = Flask(__name__)

    # Configure structured logging
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    @app.route('/')
    def index():
        app.logger.info('Processing index request')
        return 'Hello, World!'

With this configuration, your logs will look like this::

    {
        "timestamp": "2023-06-15T10:30:45.123456Z",
        "level": "INFO",
        "module": "app",
        "function": "index",
        "line": 15,
        "message": "Processing index request",
        "request_id": "a1b2c3d4e5f67890abcdef123456789"
    }


Accessing Request ID
````````````````````

You can access the current request ID in your code using the
:func:`~flask.logging.get_request_id` function::

    from flask.logging import get_request_id

    @app.route('/api/data')
    def get_data():
        request_id = get_request_id()
        app.logger.info(f'Processing data request with ID: {request_id}')
        # Your logic here
        return jsonify({'status': 'success'})

You can also manually set a request ID if you want to use an external
tracking ID (e.g., from a request header)::

    from flask.logging import set_request_id, get_request_id
    from flask import request

    @app.before_request
    def use_external_request_id():
        # Use X-Request-ID header if provided, otherwise generate one
        external_id = request.headers.get('X-Request-ID')
        if external_id:
            set_request_id(external_id)


Request Completion Logs
```````````````````````

Flask automatically logs the completion of each request with detailed
information. When using the default logging configuration, you'll see
logs like::

    GET /api/data 200 (45.23ms)

When using structured logging, the request completion log will include
all relevant details in JSON format::

    {
        "timestamp": "2023-06-15T10:30:45.123456Z",
        "level": "INFO",
        "module": "app",
        "function": "_log_request_completion",
        "line": 1050,
        "message": "GET /api/data 200 (45.23ms)",
        "request_id": "a1b2c3d4e5f67890abcdef123456789",
        "request_info": {
            "method": "GET",
            "path": "/api/data",
            "status_code": 200,
            "duration_ms": 45.23,
            "request_id": "a1b2c3d4e5f67890abcdef123456789"
        }
    }


Exception Logging
`````````````````

When an exception occurs, Flask's exception logging now automatically
includes the request ID and full stack trace. This makes it much easier
to trace which request caused an error.

With the default configuration, exception logs will include the request ID
in the message::

    [a1b2c3d4e5f67890abcdef123456789] Exception on /api/error [GET]
    Traceback (most recent call last):
      File "/path/to/app.py", line 25, in error_endpoint
        raise ValueError("Something went wrong")
    ValueError: Something went wrong

When using structured logging, exceptions will be formatted with the
full context and stack trace in the JSON output::

    {
        "timestamp": "2023-06-15T10:30:45.123456Z",
        "level": "ERROR",
        "module": "app",
        "function": "log_exception",
        "line": 987,
        "message": "[a1b2c3d4e5f67890abcdef123456789] Exception on /api/error [GET]",
        "request_id": "a1b2c3d4e5f67890abcdef123456789",
        "request_info": {
            "method": "GET",
            "path": "/api/error",
            "request_id": "a1b2c3d4e5f67890abcdef123456789"
        },
        "exception": "Traceback (most recent call last):\n  File \"/path/to/app.py\", line 25, in error_endpoint\n    raise ValueError(\"Something went wrong\")\nValueError: Something went wrong"
    }


Minimal Setup Example
`````````````````````

Here's a complete minimal example showing how to set up structured logging
in your Flask application::

    import logging
    from flask import Flask, jsonify
    from flask.logging import StructuredFormatter, get_request_id

    app = Flask(__name__)

    # Configure structured logging
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    
    # Remove default handler and add structured handler
    from flask.logging import default_handler
    app.logger.removeHandler(default_handler)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    @app.route('/')
    def index():
        request_id = get_request_id()
        app.logger.info(f'Serving index page for request: {request_id}')
        return 'Welcome to the Structured Logging Demo!'

    @app.route('/api/data')
    def get_data():
        app.logger.info('Processing data request')
        return jsonify({
            'status': 'success',
            'data': {'key': 'value'}
        })

    @app.route('/api/error')
    def cause_error():
        app.logger.warning('About to raise an exception')
        raise ValueError('This is a test exception')

    if __name__ == '__main__':
        app.run(debug=True)

This configuration ensures:
1. Every request gets a unique request ID
2. All log messages include the request ID when in a request context
3. Request completion is logged with method, path, status code, and duration
4. Exceptions include the request ID and full stack trace
5. All logs are output in JSON format for easy parsing by log aggregation tools


Key Benefits
````````````

1. **Traceability**: Easily trace all log messages related to a single
   request using the request ID.
   
2. **Debugging**: Quickly identify which request caused an error and see
   all related log entries.
   
3. **Monitoring**: Structured JSON logs can be easily parsed by log
   aggregation tools like ELK Stack, Splunk, or Datadog.
   
4. **Performance Analysis**: Request duration logs help identify slow
   endpoints and performance bottlenecks.
   
5. **Backward Compatibility**: The default logging behavior is preserved,
   so existing applications continue to work without modification.
