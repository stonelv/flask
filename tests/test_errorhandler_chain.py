import sys
import os
# Add the src directory to the path to use the local Flask version
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from flask import Blueprint, Flask


class ExceptionA(Exception):
    pass


class ExceptionB(Exception):
    pass


class ExceptionC(ExceptionA):
    pass


def test_blueprint_errorhandler_chain():
    """Test that multiple errorhandler decorators can be chained."""
    blueprint = Blueprint('test', __name__)

    # Test chained errorhandlers
    @blueprint.errorhandler(ExceptionB)
    @blueprint.errorhandler(ExceptionA)
    def handle_both(e):
        return f"Handled: {type(e).__name__}", 500

    # Test single errorhandler
    @blueprint.errorhandler(ExceptionC)
    def handle_c(e):
        return "Handled C", 500

    app = Flask(__name__)
    app.register_blueprint(blueprint)

    # Test that the errorhandlers are registered
    @app.route('/test-a')
    def test_a():
        raise ExceptionA("Test A")

    @app.route('/test-b')
    def test_b():
        raise ExceptionB("Test B")

    @app.route('/test-c')
    def test_c():
        raise ExceptionC("Test C")

    with app.test_client() as client:
        # Test ExceptionA
        response = client.get('/test-a')
        assert response.status_code == 500
        assert b"Handled: ExceptionA" in response.data

        # Test ExceptionB
        response = client.get('/test-b')
        assert response.status_code == 500
        assert b"Handled: ExceptionB" in response.data

        # Test ExceptionC
        response = client.get('/test-c')
        assert response.status_code == 500
        assert b"Handled C" in response.data


def test_app_errorhandler_chain():
    """Test that multiple app_errorhandler decorators can be chained."""
    blueprint = Blueprint('test', __name__)

    # Test chained app_errorhandlers
    @blueprint.app_errorhandler(ExceptionB)
    @blueprint.app_errorhandler(ExceptionA)
    def handle_both_app(e):
        return f"App Handled: {type(e).__name__}", 500

    app = Flask(__name__)
    app.register_blueprint(blueprint)

    # Test that the errorhandlers are registered
    @app.route('/test-app-a')
    def test_app_a():
        raise ExceptionA("Test App A")

    @app.route('/test-app-b')
    def test_app_b():
        raise ExceptionB("Test App B")

    with app.test_client() as client:
        # Test ExceptionA
        response = client.get('/test-app-a')
        assert response.status_code == 500
        assert b"App Handled: ExceptionA" in response.data

        # Test ExceptionB
        response = client.get('/test-app-b')
        assert response.status_code == 500
        assert b"App Handled: ExceptionB" in response.data
