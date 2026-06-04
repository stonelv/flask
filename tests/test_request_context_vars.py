import concurrent.futures
import threading

import flask
import pytest


class TestRequestContextVars:
    def test_disabled_by_default(self, app, client):
        @app.route("/")
        def index():
            return flask.render_template_string(
                "{{ request_id is undefined }}"
                "{{ remote_addr is undefined }}"
                "{{ user_agent is undefined }}"
            )

        rv = client.get("/")
        assert rv.data == b"TrueTrueTrue"

    def test_enabled_injects_default_vars(self, app, client):
        app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True

        @app.route("/test")
        def index():
            return flask.render_template("request_context_vars.html")

        rv = client.get(
            "/test",
            headers={"User-Agent": "TestBrowser/1.0"},
            environ_base={"REMOTE_ADDR": "192.168.1.100"},
        )
        data = rv.data.decode("utf-8")

        assert "request_id:" in data
        request_id = data.split("request_id:")[1].split("\n")[0]
        assert len(request_id) > 0

        assert "remote_addr:192.168.1.100" in data
        assert "user_agent:TestBrowser/1.0" in data
        assert "request_method:GET" in data
        assert "request_path:/test" in data

    def test_custom_processor(self, app, client):
        app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True

        @app.request_context_var_processor
        def inject_custom_vars():
            return {"custom_var": "custom_value"}

        @app.route("/")
        def index():
            return flask.render_template_string(
                "{{ custom_var }}|{{ request_id }}"
            )

        rv = client.get("/")
        data = rv.data.decode("utf-8")
        assert "custom_value" in data
        assert len(data.split("|")[1]) > 0

    def test_exclude_default_vars(self, app, client):
        app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True
        app.config["REQUEST_CONTEXT_VARS_INCLUDE_DEFAULT"] = False

        @app.request_context_var_processor
        def inject_custom_vars():
            return {"custom_var": "custom_value"}

        @app.route("/")
        def index():
            return flask.render_template_string(
                "{{ custom_var }}|{{ request_id is undefined }}"
            )

        rv = client.get("/")
        assert rv.data == b"custom_value|True"

    def test_user_values_take_precedence(self, app, client):
        app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True

        @app.route("/")
        def index():
            return flask.render_template_string(
                "{{ request_id }}",
                request_id="user_provided_id"
            )

        rv = client.get("/")
        assert rv.data == b"user_provided_id"

    def test_request_id_isolation_concurrent(self, app):
        app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True

        @app.route("/<int:request_num>")
        def index(request_num):
            id1 = flask.render_template_string("{{ request_id }}")
            id2 = flask.render_template_string("{{ request_id }}")
            assert id1 == id2
            return id1

        def make_request(num):
            with app.test_client() as c:
                rv = c.get(f"/{num}")
                return num, rv.data.decode("utf-8")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        result_dict = dict(results)
        assert len(set(result_dict.values())) == 20

        for i in range(20):
            assert len(result_dict[i]) > 0

    def test_request_id_same_within_request(self, app, client):
        app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True

        @app.route("/")
        def index():
            id1 = flask.render_template_string("{{ request_id }}")
            id2 = flask.render_template_string("{{ request_id }}")
            return f"{id1}|{id2}"

        rv = client.get("/")
        id1, id2 = rv.data.decode("utf-8").split("|")
        assert id1 == id2
        assert len(id1) > 0

    def test_outside_request_context(self, app, app_ctx):
        app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True

        result = flask.render_template_string(
            "{{ request_id is undefined }}"
            "{{ remote_addr is undefined }}"
        )
        assert result == "TrueTrue"

    def test_post_request_vars(self, app, client):
        app.config["REQUEST_CONTEXT_VARS_ENABLED"] = True

        @app.route("/submit", methods=["POST"])
        def submit():
            return flask.render_template_string(
                "{{ request_method }}|{{ request_path }}"
            )

        rv = client.post("/submit")
        assert rv.data == b"POST|/submit"

    def test_processor_decorator(self, app):
        @app.request_context_var_processor
        def my_processor():
            return {"key": "value"}

        assert my_processor in app.request_context_var_processors[None]
