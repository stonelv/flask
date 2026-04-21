import pytest
from werkzeug.exceptions import Forbidden
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import NotFound

import flask


def test_error_handler_no_match(app, client):
    class CustomException(Exception):
        pass

    @app.errorhandler(CustomException)
    def custom_exception_handler(e):
        assert isinstance(e, CustomException)
        return "custom"

    with pytest.raises(TypeError) as exc_info:
        app.register_error_handler(CustomException(), None)

    assert "CustomException() is an instance, not a class." in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        app.register_error_handler(list, None)

    assert "'list' is not a subclass of Exception." in str(exc_info.value)

    @app.errorhandler(500)
    def handle_500(e):
        assert isinstance(e, InternalServerError)

        if e.original_exception is not None:
            return f"wrapped {type(e.original_exception).__name__}"

        return "direct"

    with pytest.raises(ValueError) as exc_info:
        app.register_error_handler(999, None)

    assert "Use a subclass of HTTPException" in str(exc_info.value)

    @app.route("/custom")
    def custom_test():
        raise CustomException()

    @app.route("/keyerror")
    def key_error():
        raise KeyError()

    @app.route("/abort")
    def do_abort():
        flask.abort(500)

    app.testing = False
    assert client.get("/custom").data == b"custom"
    assert client.get("/keyerror").data == b"wrapped KeyError"
    assert client.get("/abort").data == b"direct"


def test_error_handler_subclass(app):
    class ParentException(Exception):
        pass

    class ChildExceptionUnregistered(ParentException):
        pass

    class ChildExceptionRegistered(ParentException):
        pass

    @app.errorhandler(ParentException)
    def parent_exception_handler(e):
        assert isinstance(e, ParentException)
        return "parent"

    @app.errorhandler(ChildExceptionRegistered)
    def child_exception_handler(e):
        assert isinstance(e, ChildExceptionRegistered)
        return "child-registered"

    @app.route("/parent")
    def parent_test():
        raise ParentException()

    @app.route("/child-unregistered")
    def unregistered_test():
        raise ChildExceptionUnregistered()

    @app.route("/child-registered")
    def registered_test():
        raise ChildExceptionRegistered()

    c = app.test_client()

    assert c.get("/parent").data == b"parent"
    assert c.get("/child-unregistered").data == b"parent"
    assert c.get("/child-registered").data == b"child-registered"


def test_error_handler_http_subclass(app):
    class ForbiddenSubclassRegistered(Forbidden):
        pass

    class ForbiddenSubclassUnregistered(Forbidden):
        pass

    @app.errorhandler(403)
    def code_exception_handler(e):
        assert isinstance(e, Forbidden)
        return "forbidden"

    @app.errorhandler(ForbiddenSubclassRegistered)
    def subclass_exception_handler(e):
        assert isinstance(e, ForbiddenSubclassRegistered)
        return "forbidden-registered"

    @app.route("/forbidden")
    def forbidden_test():
        raise Forbidden()

    @app.route("/forbidden-registered")
    def registered_test():
        raise ForbiddenSubclassRegistered()

    @app.route("/forbidden-unregistered")
    def unregistered_test():
        raise ForbiddenSubclassUnregistered()

    c = app.test_client()

    assert c.get("/forbidden").data == b"forbidden"
    assert c.get("/forbidden-unregistered").data == b"forbidden"
    assert c.get("/forbidden-registered").data == b"forbidden-registered"


def test_error_handler_blueprint(app):
    bp = flask.Blueprint("bp", __name__)

    @bp.errorhandler(500)
    def bp_exception_handler(e):
        return "bp-error"

    @bp.route("/error")
    def bp_test():
        raise InternalServerError()

    @app.errorhandler(500)
    def app_exception_handler(e):
        return "app-error"

    @app.route("/error")
    def app_test():
        raise InternalServerError()

    app.register_blueprint(bp, url_prefix="/bp")

    c = app.test_client()

    assert c.get("/error").data == b"app-error"
    assert c.get("/bp/error").data == b"bp-error"


def test_default_error_handler():
    bp = flask.Blueprint("bp", __name__)

    @bp.errorhandler(HTTPException)
    def bp_exception_handler(e):
        assert isinstance(e, HTTPException)
        assert isinstance(e, NotFound)
        return "bp-default"

    @bp.errorhandler(Forbidden)
    def bp_forbidden_handler(e):
        assert isinstance(e, Forbidden)
        return "bp-forbidden"

    @bp.route("/undefined")
    def bp_registered_test():
        raise NotFound()

    @bp.route("/forbidden")
    def bp_forbidden_test():
        raise Forbidden()

    app = flask.Flask(__name__)

    @app.errorhandler(HTTPException)
    def catchall_exception_handler(e):
        assert isinstance(e, HTTPException)
        assert isinstance(e, NotFound)
        return "default"

    @app.errorhandler(Forbidden)
    def catchall_forbidden_handler(e):
        assert isinstance(e, Forbidden)
        return "forbidden"

    @app.route("/forbidden")
    def forbidden():
        raise Forbidden()

    @app.route("/slash/")
    def slash():
        return "slash"

    app.register_blueprint(bp, url_prefix="/bp")

    c = app.test_client()
    assert c.get("/bp/undefined").data == b"bp-default"
    assert c.get("/bp/forbidden").data == b"bp-forbidden"
    assert c.get("/undefined").data == b"default"
    assert c.get("/forbidden").data == b"forbidden"
    # Don't handle RequestRedirect raised when adding slash.
    assert c.get("/slash", follow_redirects=True).data == b"slash"


class TestGenericHandlers:
    """Test how very generic handlers are dispatched to."""

    class Custom(Exception):
        pass

    @pytest.fixture()
    def app(self, app):
        @app.route("/custom")
        def do_custom():
            raise self.Custom()

        @app.route("/error")
        def do_error():
            raise KeyError()

        @app.route("/abort")
        def do_abort():
            flask.abort(500)

        @app.route("/raise")
        def do_raise():
            raise InternalServerError()

        app.config["PROPAGATE_EXCEPTIONS"] = False
        return app

    def report_error(self, e):
        original = getattr(e, "original_exception", None)

        if original is not None:
            return f"wrapped {type(original).__name__}"

        return f"direct {type(e).__name__}"

    @pytest.mark.parametrize("to_handle", (InternalServerError, 500))
    def test_handle_class_or_code(self, app, client, to_handle):
        """``InternalServerError`` and ``500`` are aliases, they should
        have the same behavior. Both should only receive
        ``InternalServerError``, which might wrap another error.
        """

        @app.errorhandler(to_handle)
        def handle_500(e):
            assert isinstance(e, InternalServerError)
            return self.report_error(e)

        assert client.get("/custom").data == b"wrapped Custom"
        assert client.get("/error").data == b"wrapped KeyError"
        assert client.get("/abort").data == b"direct InternalServerError"
        assert client.get("/raise").data == b"direct InternalServerError"

    def test_handle_generic_http(self, app, client):
        """``HTTPException`` should only receive ``HTTPException``
        subclasses. It will receive ``404`` routing exceptions.
        """

        @app.errorhandler(HTTPException)
        def handle_http(e):
            assert isinstance(e, HTTPException)
            return str(e.code)

        assert client.get("/error").data == b"500"
        assert client.get("/abort").data == b"500"
        assert client.get("/not-found").data == b"404"

    def test_handle_generic(self, app, client):
        """Generic ``Exception`` will handle all exceptions directly,
        including ``HTTPExceptions``.
        """

        @app.errorhandler(Exception)
        def handle_exception(e):
            return self.report_error(e)

        assert client.get("/custom").data == b"direct Custom"
        assert client.get("/error").data == b"direct KeyError"
        assert client.get("/abort").data == b"direct InternalServerError"
        assert client.get("/not-found").data == b"direct NotFound"


class TestMultipleErrorHandlers:
    """Test registering handlers for multiple exception types or codes at once."""

    def test_errorhandler_multiple_exceptions(self, app):
        """Test @app.errorhandler with multiple exception types."""

        class ExceptionA(Exception):
            pass

        class ExceptionB(Exception):
            pass

        class ExceptionC(Exception):
            pass

        @app.errorhandler([ExceptionA, ExceptionB])
        def handle_a_and_b(e):
            return f"handled {type(e).__name__}"

        @app.errorhandler(ExceptionC)
        def handle_c(e):
            return "handled ExceptionC"

        @app.route("/a")
        def raise_a():
            raise ExceptionA()

        @app.route("/b")
        def raise_b():
            raise ExceptionB()

        @app.route("/c")
        def raise_c():
            raise ExceptionC()

        c = app.test_client()
        assert c.get("/a").data == b"handled ExceptionA"
        assert c.get("/b").data == b"handled ExceptionB"
        assert c.get("/c").data == b"handled ExceptionC"

    def test_errorhandler_multiple_codes(self, app):
        """Test @app.errorhandler with multiple HTTP status codes."""
        from werkzeug.exceptions import MethodNotAllowed
        from werkzeug.exceptions import NotFound

        @app.errorhandler([404, 405])
        def handle_404_and_405(e):
            return f"error {e.code}", e.code

        @app.errorhandler(500)
        def handle_500(e):
            return "error 500", 500

        @app.route("/test")
        def test_route():
            return "ok"

        c = app.test_client()
        response = c.get("/not-found")
        assert response.status_code == 404
        assert response.data == b"error 404"

        response = c.post("/test")
        assert response.status_code == 405
        assert response.data == b"error 405"

    def test_register_error_handler_multiple(self, app):
        """Test register_error_handler with multiple exception types."""

        class ExceptionX(Exception):
            pass

        class ExceptionY(Exception):
            pass

        def handle_x_and_y(e):
            return f"handled {type(e).__name__}"

        app.register_error_handler([ExceptionX, ExceptionY], handle_x_and_y)

        @app.route("/x")
        def raise_x():
            raise ExceptionX()

        @app.route("/y")
        def raise_y():
            raise ExceptionY()

        c = app.test_client()
        assert c.get("/x").data == b"handled ExceptionX"
        assert c.get("/y").data == b"handled ExceptionY"

    def test_blueprint_app_errorhandler_multiple(self, app):
        """Test Blueprint.app_errorhandler with multiple exception types."""
        bp = flask.Blueprint("bp", __name__)

        class ExceptionM(Exception):
            pass

        class ExceptionN(Exception):
            pass

        @bp.app_errorhandler([ExceptionM, ExceptionN])
        def handle_m_and_n(e):
            return f"bp handled {type(e).__name__}"

        @app.route("/m")
        def raise_m():
            raise ExceptionM()

        @app.route("/n")
        def raise_n():
            raise ExceptionN()

        app.register_blueprint(bp)

        c = app.test_client()
        assert c.get("/m").data == b"bp handled ExceptionM"
        assert c.get("/n").data == b"bp handled ExceptionN"


class TestErrorHandlerPriority:
    """Test error handler priority and inheritance matching rules."""

    def test_specificity_priority(self, app):
        """Test that more specific exception classes take precedence."""

        class ParentException(Exception):
            pass

        class ChildException(ParentException):
            pass

        @app.errorhandler(ParentException)
        def handle_parent(e):
            return "parent"

        @app.errorhandler(ChildException)
        def handle_child(e):
            return "child"

        @app.route("/parent")
        def raise_parent():
            raise ParentException()

        @app.route("/child")
        def raise_child():
            raise ChildException()

        c = app.test_client()
        assert c.get("/parent").data == b"parent"
        assert c.get("/child").data == b"child"

    def test_inheritance_matching(self, app):
        """Test that child exceptions match parent handlers when no specific handler exists."""

        class GrandParentException(Exception):
            pass

        class ParentException(GrandParentException):
            pass

        class ChildException(ParentException):
            pass

        @app.errorhandler(GrandParentException)
        def handle_grandparent(e):
            return f"grandparent: {type(e).__name__}"

        @app.route("/grandparent")
        def raise_grandparent():
            raise GrandParentException()

        @app.route("/parent")
        def raise_parent():
            raise ParentException()

        @app.route("/child")
        def raise_child():
            raise ChildException()

        c = app.test_client()
        assert c.get("/grandparent").data == b"grandparent: GrandParentException"
        assert c.get("/parent").data == b"grandparent: ParentException"
        assert c.get("/child").data == b"grandparent: ChildException"

    def test_registration_order_priority(self, app):
        """Test that later registrations override earlier ones for the same exception."""

        class TestException(Exception):
            pass

        @app.errorhandler(TestException)
        def first_handler(e):
            return "first"

        @app.errorhandler(TestException)
        def second_handler(e):
            return "second"

        @app.route("/test")
        def raise_test():
            raise TestException()

        c = app.test_client()
        assert c.get("/test").data == b"second"

    def test_http_code_vs_generic_exception_priority(self, app):
        """Test that HTTP code handlers take precedence over generic exception handlers.

        When an HTTPException is raised, handlers registered for the specific
        HTTP status code take precedence over handlers registered for more
        general exception classes like Exception.
        """
        from werkzeug.exceptions import NotFound

        @app.errorhandler(Exception)
        def handle_generic_exception(e):
            return "generic exception"

        @app.errorhandler(404)
        def handle_404(e):
            return "not found"

        c = app.test_client()
        assert c.get("/non-existent").data == b"not found"

    def test_blueprint_vs_app_priority(self, app):
        """Test that blueprint handlers take precedence over app handlers for matching requests."""
        bp = flask.Blueprint("bp", __name__)

        class TestException(Exception):
            pass

        @bp.errorhandler(TestException)
        def bp_handler(e):
            return "blueprint"

        @app.errorhandler(TestException)
        def app_handler(e):
            return "app"

        @bp.route("/test")
        def bp_route():
            raise TestException()

        @app.route("/test")
        def app_route():
            raise TestException()

        app.register_blueprint(bp, url_prefix="/bp")

        c = app.test_client()
        assert c.get("/bp/test").data == b"blueprint"
        assert c.get("/test").data == b"app"

    def test_mixed_specificity_and_registration_order(self, app):
        """Test that specificity takes precedence over registration order."""

        class ParentException(Exception):
            pass

        class ChildException(ParentException):
            pass

        @app.errorhandler(ChildException)
        def child_handler(e):
            return "child"

        @app.errorhandler(ParentException)
        def parent_handler(e):
            return "parent"

        @app.route("/child")
        def raise_child():
            raise ChildException()

        @app.route("/parent")
        def raise_parent():
            raise ParentException()

        c = app.test_client()
        assert c.get("/child").data == b"child"
        assert c.get("/parent").data == b"parent"


class TestErrorHandlerInputValidation:
    """Test input validation for error handler registration."""

    def test_errorhandler_rejects_string(self, app):
        """Test that errorhandler rejects string arguments like "404"."""
        with pytest.raises(TypeError) as exc_info:

            @app.errorhandler("404")
            def handle_string(e):
                return "not found"

        assert "Cannot pass a string or bytes" in str(exc_info.value)

    def test_errorhandler_rejects_bytes(self, app):
        """Test that errorhandler rejects bytes arguments."""
        with pytest.raises(TypeError) as exc_info:

            @app.errorhandler(b"404")
            def handle_bytes(e):
                return "not found"

        assert "Cannot pass a string or bytes" in str(exc_info.value)

    def test_errorhandler_rejects_invalid_sequence_elements(self, app):
        """Test that errorhandler rejects sequences with invalid elements."""
        with pytest.raises(TypeError) as exc_info:

            @app.errorhandler([404, "405"])
            def handle_mixed(e):
                return "error"

        assert "Invalid error handler argument" in str(exc_info.value)
        assert "'405'" in str(exc_info.value)

    def test_errorhandler_rejects_nested_sequences(self, app):
        """Test that errorhandler rejects nested sequences."""
        with pytest.raises(TypeError) as exc_info:

            @app.errorhandler([[404], [405]])
            def handle_nested(e):
                return "error"

        assert "Invalid error handler argument" in str(exc_info.value)
        assert "[404]" in str(exc_info.value)

    def test_register_error_handler_rejects_string(self, app):
        """Test that register_error_handler rejects string arguments."""

        def handler(e):
            return "error"

        with pytest.raises(TypeError) as exc_info:
            app.register_error_handler("404", handler)

        assert "Cannot pass a string or bytes" in str(exc_info.value)

    def test_register_error_handler_rejects_invalid_sequence_elements(self, app):
        """Test that register_error_handler rejects sequences with invalid elements."""

        def handler(e):
            return "error"

        with pytest.raises(TypeError) as exc_info:
            app.register_error_handler([ValueError, "typeerror"], handler)

        assert "Invalid error handler argument" in str(exc_info.value)


class TestBlueprintAppErrorHandlerMultipleCodes:
    """Test Blueprint.app_errorhandler with multiple HTTP status codes."""

    def test_blueprint_app_errorhandler_multiple_codes(self, app):
        """Test bp.app_errorhandler([404, 405]) registers handlers for both codes."""
        bp = flask.Blueprint("bp", __name__)

        @bp.app_errorhandler([404, 405])
        def handle_404_and_405(e):
            return f"bp handled error {e.code}", e.code

        @app.route("/test")
        def test_route():
            return "ok"

        app.register_blueprint(bp)

        c = app.test_client()

        response = c.get("/non-existent")
        assert response.status_code == 404
        assert response.data == b"bp handled error 404"

        response = c.post("/test")
        assert response.status_code == 405
        assert response.data == b"bp handled error 405"

    def test_blueprint_app_errorhandler_mixed_codes_and_exceptions(self, app):
        """Test bp.app_errorhandler with a mix of codes and exception classes."""
        bp = flask.Blueprint("bp", __name__)

        class CustomError(Exception):
            pass

        @bp.app_errorhandler([404, ValueError])
        def handle_404_and_value_error(e):
            if hasattr(e, "code"):
                return f"bp handled HTTP {e.code}"
            return f"bp handled {type(e).__name__}"

        @app.route("/value-error")
        def raise_value_error():
            raise ValueError("test")

        app.register_blueprint(bp)

        c = app.test_client()

        response = c.get("/non-existent")
        assert response.data == b"bp handled HTTP 404"

        response = c.get("/value-error")
        assert response.data == b"bp handled ValueError"
