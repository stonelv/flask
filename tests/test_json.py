import datetime
import decimal
import io
import uuid

import pytest
from werkzeug.http import http_date

import flask
from flask import json
from flask.json.provider import DefaultJSONProvider


@pytest.mark.parametrize("debug", (True, False))
def test_bad_request_debug_message(app, client, debug):
    app.config["DEBUG"] = debug
    app.config["TRAP_BAD_REQUEST_ERRORS"] = False

    @app.route("/json", methods=["POST"])
    def post_json():
        flask.request.get_json()
        return None

    rv = client.post("/json", data=None, content_type="application/json")
    assert rv.status_code == 400
    contains = b"Failed to decode JSON object" in rv.data
    assert contains == debug


def test_json_bad_requests(app, client):
    @app.route("/json", methods=["POST"])
    def return_json():
        return flask.jsonify(foo=str(flask.request.get_json()))

    rv = client.post("/json", data="malformed", content_type="application/json")
    assert rv.status_code == 400


def test_json_custom_mimetypes(app, client):
    @app.route("/json", methods=["POST"])
    def return_json():
        return flask.request.get_json()

    rv = client.post("/json", data='"foo"', content_type="application/x+json")
    assert rv.data == b"foo"


@pytest.mark.parametrize(
    "test_value,expected", [(True, '"\\u2603"'), (False, '"\u2603"')]
)
def test_json_as_unicode(test_value, expected, app, app_ctx):
    app.json.ensure_ascii = test_value
    rv = app.json.dumps("\N{SNOWMAN}")
    assert rv == expected


def test_json_dump_to_file(app, app_ctx):
    test_data = {"name": "Flask"}
    out = io.StringIO()

    flask.json.dump(test_data, out)
    out.seek(0)
    rv = flask.json.load(out)
    assert rv == test_data


@pytest.mark.parametrize(
    "test_value", [0, -1, 1, 23, 3.14, "s", "longer string", True, False, None]
)
def test_jsonify_basic_types(test_value, app, client):
    url = "/jsonify_basic_types"
    app.add_url_rule(url, url, lambda x=test_value: flask.jsonify(x))
    rv = client.get(url)
    assert rv.mimetype == "application/json"
    assert flask.json.loads(rv.data) == test_value


def test_jsonify_dicts(app, client):
    d = {
        "a": 0,
        "b": 23,
        "c": 3.14,
        "d": "t",
        "e": "Hi",
        "f": True,
        "g": False,
        "h": ["test list", 10, False],
        "i": {"test": "dict"},
    }

    @app.route("/kw")
    def return_kwargs():
        return flask.jsonify(**d)

    @app.route("/dict")
    def return_dict():
        return flask.jsonify(d)

    for url in "/kw", "/dict":
        rv = client.get(url)
        assert rv.mimetype == "application/json"
        assert flask.json.loads(rv.data) == d


def test_jsonify_arrays(app, client):
    """Test jsonify of lists and args unpacking."""
    a_list = [
        0,
        42,
        3.14,
        "t",
        "hello",
        True,
        False,
        ["test list", 2, False],
        {"test": "dict"},
    ]

    @app.route("/args_unpack")
    def return_args_unpack():
        return flask.jsonify(*a_list)

    @app.route("/array")
    def return_array():
        return flask.jsonify(a_list)

    for url in "/args_unpack", "/array":
        rv = client.get(url)
        assert rv.mimetype == "application/json"
        assert flask.json.loads(rv.data) == a_list


@pytest.mark.parametrize(
    "value", [datetime.datetime(1973, 3, 11, 6, 30, 45), datetime.date(1975, 1, 5)]
)
def test_jsonify_datetime(app, client, value):
    @app.route("/")
    def index():
        return flask.jsonify(value=value)

    r = client.get()
    assert r.json["value"] == http_date(value)


class FixedOffset(datetime.tzinfo):
    """Fixed offset in hours east from UTC.

    This is a slight adaptation of the ``FixedOffset`` example found in
    https://docs.python.org/2.7/library/datetime.html.
    """

    def __init__(self, hours, name):
        self.__offset = datetime.timedelta(hours=hours)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return datetime.timedelta()


@pytest.mark.parametrize("tz", (("UTC", 0), ("PST", -8), ("KST", 9)))
def test_jsonify_aware_datetimes(tz):
    """Test if aware datetime.datetime objects are converted into GMT."""
    tzinfo = FixedOffset(hours=tz[1], name=tz[0])
    dt = datetime.datetime(2017, 1, 1, 12, 34, 56, tzinfo=tzinfo)
    gmt = FixedOffset(hours=0, name="GMT")
    expected = dt.astimezone(gmt).strftime('"%a, %d %b %Y %H:%M:%S %Z"')
    assert flask.json.dumps(dt) == expected


def test_jsonify_uuid_types(app, client):
    """Test jsonify with uuid.UUID types"""

    test_uuid = uuid.UUID(bytes=b"\xde\xad\xbe\xef" * 4)
    url = "/uuid_test"
    app.add_url_rule(url, url, lambda: flask.jsonify(x=test_uuid))

    rv = client.get(url)

    rv_x = flask.json.loads(rv.data)["x"]
    assert rv_x == str(test_uuid)
    rv_uuid = uuid.UUID(rv_x)
    assert rv_uuid == test_uuid


def test_json_decimal():
    rv = flask.json.dumps(decimal.Decimal("0.003"))
    assert rv == '"0.003"'


def test_json_attr(app, client):
    @app.route("/add", methods=["POST"])
    def add():
        json = flask.request.get_json()
        return str(json["a"] + json["b"])

    rv = client.post(
        "/add",
        data=flask.json.dumps({"a": 1, "b": 2}),
        content_type="application/json",
    )
    assert rv.data == b"3"


def test_tojson_filter(app, req_ctx):
    # The tojson filter is tested in Jinja, this confirms that it's
    # using Flask's dumps.
    rv = flask.render_template_string(
        "const data = {{ data|tojson }};",
        data={"name": "</script>", "time": datetime.datetime(2021, 2, 1, 7, 15)},
    )
    assert rv == (
        'const data = {"name": "\\u003c/script\\u003e",'
        ' "time": "Mon, 01 Feb 2021 07:15:00 GMT"};'
    )


def test_json_customization(app, client):
    class X:  # noqa: B903, for Python2 compatibility
        def __init__(self, val):
            self.val = val

    def default(o):
        if isinstance(o, X):
            return f"<{o.val}>"

        return DefaultJSONProvider.default(o)

    class CustomProvider(DefaultJSONProvider):
        def object_hook(self, obj):
            if len(obj) == 1 and "_foo" in obj:
                return X(obj["_foo"])

            return obj

        def loads(self, s, **kwargs):
            kwargs.setdefault("object_hook", self.object_hook)
            return super().loads(s, **kwargs)

    app.json = CustomProvider(app)
    app.json.default = default

    @app.route("/", methods=["POST"])
    def index():
        return flask.json.dumps(flask.request.get_json()["x"])

    rv = client.post(
        "/",
        data=flask.json.dumps({"x": {"_foo": 42}}),
        content_type="application/json",
    )
    assert rv.data == b'"<42>"'


def _has_encoding(name):
    try:
        import codecs

        codecs.lookup(name)
        return True
    except LookupError:
        return False


def test_json_key_sorting(app, client):
    app.debug = True
    assert app.json.sort_keys
    d = dict.fromkeys(range(20), "foo")

    @app.route("/")
    def index():
        return flask.jsonify(values=d)

    rv = client.get("/")
    lines = [x.strip() for x in rv.data.strip().decode("utf-8").splitlines()]
    sorted_by_str = [
        "{",
        '"values": {',
        '"0": "foo",',
        '"1": "foo",',
        '"10": "foo",',
        '"11": "foo",',
        '"12": "foo",',
        '"13": "foo",',
        '"14": "foo",',
        '"15": "foo",',
        '"16": "foo",',
        '"17": "foo",',
        '"18": "foo",',
        '"19": "foo",',
        '"2": "foo",',
        '"3": "foo",',
        '"4": "foo",',
        '"5": "foo",',
        '"6": "foo",',
        '"7": "foo",',
        '"8": "foo",',
        '"9": "foo"',
        "}",
        "}",
    ]
    sorted_by_int = [
        "{",
        '"values": {',
        '"0": "foo",',
        '"1": "foo",',
        '"2": "foo",',
        '"3": "foo",',
        '"4": "foo",',
        '"5": "foo",',
        '"6": "foo",',
        '"7": "foo",',
        '"8": "foo",',
        '"9": "foo",',
        '"10": "foo",',
        '"11": "foo",',
        '"12": "foo",',
        '"13": "foo",',
        '"14": "foo",',
        '"15": "foo",',
        '"16": "foo",',
        '"17": "foo",',
        '"18": "foo",',
        '"19": "foo"',
        "}",
        "}",
    ]

    try:
        assert lines == sorted_by_int
    except AssertionError:
        assert lines == sorted_by_str


def test_html_method():
    class ObjectWithHTML:
        def __html__(self):
            return "<p>test</p>"

    result = json.dumps(ObjectWithHTML())
    assert result == '"<p>test</p>"'


class TestPrettyPrint:
    """Test the optional pretty-print feature for JSON responses.

    When a request includes ?pretty=1 query parameter or X-Flask-Pretty: 1 header,
    the JSON response should be indented with sorted keys.
    """

    def test_pretty_query_param_dict_view(self, app, client):
        """Test pretty-print with ?pretty=1 query parameter when view returns dict."""

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2, "m": 3}

        rv = client.get("/dict")
        assert b"\n" not in rv.data.strip() or b"  " not in rv.data

        rv = client.get("/dict?pretty=1")
        data = rv.data.decode()
        assert "  " in data
        assert '"a": 2' in data
        assert '"m": 3' in data
        assert '"z": 1' in data

    def test_pretty_query_param_list_view(self, app, client):
        """Test pretty-print with ?pretty=1 query parameter when view returns list."""

        @app.route("/list")
        def return_list():
            return [{"z": 1, "a": 2}, "b", "c"]

        rv = client.get("/list?pretty=1")
        data = rv.data.decode()
        assert "  " in data

    def test_pretty_query_param_jsonify(self, app, client):
        """Test pretty-print with ?pretty=1 query parameter when using jsonify."""

        @app.route("/jsonify")
        def use_jsonify():
            return flask.jsonify(z=1, a=2, m=3)

        rv = client.get("/jsonify?pretty=1")
        data = rv.data.decode()
        assert "  " in data

    def test_pretty_header(self, app, client):
        """Test pretty-print with X-Flask-Pretty: 1 header."""

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2, "m": 3}

        rv = client.get("/dict", headers={"X-Flask-Pretty": "1"})
        data = rv.data.decode()
        assert "  " in data

    def test_pretty_blueprint(self, app, client):
        """Test pretty-print works with blueprint views."""
        from flask import Blueprint

        bp = Blueprint("test", __name__)

        @bp.route("/data")
        def return_data():
            return {"z": 1, "a": 2}

        app.register_blueprint(bp, url_prefix="/api")

        rv = client.get("/api/data?pretty=1")
        data = rv.data.decode()
        assert "  " in data

    @pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "Yes", "on", "On"])
    def test_pretty_truthy_values(self, app, client, value):
        """Test pretty-print is enabled for various truthy values."""

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2}

        rv = client.get(f"/dict?pretty={value}")
        data = rv.data.decode()
        assert "  " in data

        rv = client.get("/dict", headers={"X-Flask-Pretty": value})
        data = rv.data.decode()
        assert "  " in data

    @pytest.mark.parametrize("value", ["0", "false", "False", "no", "No", "off", "Off", ""])
    def test_pretty_falsy_values(self, app, client, value):
        """Test pretty-print is NOT enabled for falsy values."""

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2}

        rv = client.get(f"/dict?pretty={value}")
        data = rv.data.decode()
        assert "  " not in data or '"z": 1' not in data

    def test_pretty_sort_keys_always_enabled(self, app, client):
        """Test that sort_keys is always enabled when pretty-print is requested."""
        app.json.sort_keys = False

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2, "m": 3}

        rv = client.get("/dict?pretty=1")
        data = rv.data.decode()
        lines = [line.strip() for line in data.strip().splitlines()]
        assert '"a": 2' in lines
        assert '"m": 3' in lines
        assert '"z": 1' in lines
        a_index = next(i for i, line in enumerate(lines) if '"a": 2' in line)
        m_index = next(i for i, line in enumerate(lines) if '"m": 3' in line)
        z_index = next(i for i, line in enumerate(lines) if '"z": 1' in line)
        assert a_index < m_index < z_index

    def test_default_behavior_unchanged(self, app, client):
        """Test that default behavior (without pretty parameter) is unchanged."""
        app.debug = False
        app.json.compact = True

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2}

        rv = client.get("/dict")
        data = rv.data.decode()
        assert "  " not in data
        assert b"\n" not in rv.data.strip()

    def test_no_request_context_still_compact(self, app, app_ctx):
        """Test that without request context, response is still compact."""
        rv = app.json.response({"z": 1, "a": 2})
        data = rv.data.decode()
        assert "  " not in data

    def test_debug_mode_still_works(self, app, client):
        """Test that debug mode still causes pretty-printing."""
        app.debug = True
        app.json.compact = None

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2}

        rv = client.get("/dict")
        data = rv.data.decode()
        assert "  " in data

    def test_compact_false_still_works(self, app, client):
        """Test that compact=False still causes pretty-printing."""
        app.debug = False
        app.json.compact = False

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2}

        rv = client.get("/dict")
        data = rv.data.decode()
        assert "  " in data

    def test_pretty_overrides_compact_true(self, app, client):
        """Test that pretty parameter overrides compact=True."""
        app.debug = False
        app.json.compact = True

        @app.route("/dict")
        def return_dict():
            return {"z": 1, "a": 2}

        rv = client.get("/dict?pretty=1")
        data = rv.data.decode()
        assert "  " in data
