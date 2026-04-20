RBAC Example
=============

Demonstrates Role-Based Access Control (RBAC) with three roles: admin,
editor, and viewer. Includes a reusable permission decorator, protected
endpoints, and consistent error handling.


Roles and Permissions
---------------------

- **admin**: read, write, delete, manage (full access)
- **editor**: read, write (can read and modify content)
- **viewer**: read (can only read content)


Test Users
----------

- admin_user / admin123 (role: admin)
- editor_user / editor123 (role: editor)
- viewer_user / viewer123 (role: viewer)


Protected Endpoints
-------------------

- ``GET /api/manage``: Requires "manage" permission (admin only)
- ``GET /api/content``: Requires "read" permission (all roles)
- ``POST /api/content``: Requires "write" permission (admin, editor)
- ``PUT /api/content``: Requires "write" permission (admin, editor)
- ``DELETE /api/content``: Requires "write" permission (admin, editor)

All unauthorized requests return a consistent 403 response with the message:
"Forbidden: You do not have permission to access this resource."


Install
-------

Create a virtualenv and activate it::

    $ python3 -m venv .venv
    $ . .venv/bin/activate

Or on Windows cmd::

    $ py -3 -m venv .venv
    $ .venv\Scripts\activate.bat

Install the example::

    $ pip install -e .

Or if you are using the main branch, install Flask from source before
installing the example::

    $ pip install -e ../..
    $ pip install -e .


Run
---

.. code-block:: text

    $ flask --app rbac_example run

Open http://127.0.0.1:5000 in a browser or use curl/Postman to test the
API endpoints with HTTP Basic Auth.

Example curl commands::

    # Test login
    $ curl -u admin_user:admin123 -X POST http://127.0.0.1:5000/login

    # Read content (all roles)
    $ curl -u viewer_user:viewer123 http://127.0.0.1:5000/api/content

    # Create content (requires write permission)
    $ curl -u editor_user:editor123 -X POST http://127.0.0.1:5000/api/content

    # Access manage endpoint (admin only)
    $ curl -u admin_user:admin123 http://127.0.0.1:5000/api/manage

    # Viewer trying to create content (will return 403)
    $ curl -u viewer_user:viewer123 -X POST http://127.0.0.1:5000/api/content


Test
----

::

    $ pip install '.[test]'
    $ pytest

Run with coverage report::

    $ coverage run -m pytest
    $ coverage report
