"""
Test configuration for Flask-Simple-Auth.
"""

import pytest
from flask import Flask
from flask_simple_auth import SimpleAuth


@pytest.fixture
def app():
    """Create a test Flask app."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def auth(app):
    """Create a SimpleAuth instance."""
    return SimpleAuth(app)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()