import pytest

from rbac_example import app as _app


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    _app.config.update({
        "TESTING": True,
    })
    yield _app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()
