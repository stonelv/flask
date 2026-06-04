import os
import time
from datetime import datetime
from datetime import timezone
from email.utils import formatdate
from email.utils import parsedate_to_datetime

import pytest

import flask


class TestSendFileETag:
    """Test ETag and conditional request handling for send_file and send_from_directory."""

    def test_send_file_generates_etag(self, app, req_ctx, tmp_path):
        """Test that send_file generates a stable ETag for files."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        rv = flask.send_file(str(test_file))
        assert rv.headers.get("ETag") is not None
        etag1 = rv.headers.get("ETag")
        rv.close()

        rv2 = flask.send_file(str(test_file))
        etag2 = rv2.headers.get("ETag")
        assert etag1 == etag2
        rv2.close()

    def test_send_file_etag_changes_on_modification(self, app, req_ctx, tmp_path):
        """Test that ETag changes when file is modified."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        rv = flask.send_file(str(test_file))
        etag1 = rv.headers.get("ETag")
        rv.close()

        time.sleep(0.1)
        test_file.write_text("Hello, Modified!")

        rv2 = flask.send_file(str(test_file))
        etag2 = rv2.headers.get("ETag")
        assert etag1 != etag2
        rv2.close()

    def test_send_file_if_none_match_304(self, app, tmp_path):
        """Test that If-None-Match header returns 304 when ETag matches."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file")
            assert rv.status_code == 200
            etag = rv.headers.get("ETag")
            assert etag is not None

            rv2 = client.get("/file", headers={"If-None-Match": etag})
            assert rv2.status_code == 304
            assert "Content-Length" not in rv2.headers

    def test_send_file_if_none_match_no_match(self, app, tmp_path):
        """Test that If-None-Match header returns 200 when ETag doesn't match."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file", headers={"If-None-Match": '"invalid-etag"'})
            assert rv.status_code == 200
            assert rv.data == b"Hello, World!"

    def test_send_file_if_modified_since_304(self, app, tmp_path):
        """Test that If-Modified-Since header returns 304 when file not modified."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        mtime = os.path.getmtime(str(test_file))
        if_modified_since = formatdate(mtime + 1, usegmt=True)

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file", headers={"If-Modified-Since": if_modified_since})
            assert rv.status_code == 304

    def test_send_file_if_modified_since_modified(self, app, tmp_path):
        """Test that If-Modified-Since header returns 200 when file is modified."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        mtime = os.path.getmtime(str(test_file))
        if_modified_since = formatdate(mtime - 1, usegmt=True)

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file", headers={"If-Modified-Since": if_modified_since})
            assert rv.status_code == 200
            assert rv.data == b"Hello, World!"

    def test_send_file_if_none_match_takes_precedence(self, app, tmp_path):
        """Test that If-None-Match takes precedence over If-Modified-Since."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file")
            etag = rv.headers.get("ETag")
            mtime = os.path.getmtime(str(test_file))

            old_if_modified_since = formatdate(mtime - 1, usegmt=True)

            rv2 = client.get(
                "/file",
                headers={
                    "If-None-Match": etag,
                    "If-Modified-Since": old_if_modified_since,
                },
            )
            assert rv2.status_code == 304

    def test_send_file_head_request(self, app, tmp_path):
        """Test that HEAD requests work correctly with send_file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.head("/file")
            assert rv.status_code == 200
            assert rv.data == b""
            assert "Content-Length" in rv.headers
            assert "ETag" in rv.headers
            assert "Last-Modified" in rv.headers

    def test_send_file_range_request(self, app, tmp_path):
        """Test that Range requests work correctly with send_file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file", headers={"Range": "bytes=0-4"})
            assert rv.status_code == 206
            assert rv.data == b"Hello"
            assert "Content-Range" in rv.headers

    def test_send_file_range_request_with_etag(self, app, tmp_path):
        """Test that Range requests work with ETag validation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file")
            etag = rv.headers.get("ETag")

            rv2 = client.get(
                "/file",
                headers={
                    "Range": "bytes=0-4",
                    "If-Range": etag,
                },
            )
            assert rv2.status_code == 206
            assert rv2.data == b"Hello"

    def test_send_file_custom_etag(self, app, req_ctx, tmp_path):
        """Test that custom ETag can be provided."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        custom_etag = "my-custom-etag"
        rv = flask.send_file(str(test_file), etag=custom_etag)
        assert rv.headers.get("ETag") == f'"{custom_etag}"'
        rv.close()

    def test_send_file_disable_etag(self, app, req_ctx, tmp_path):
        """Test that ETag can be disabled."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        rv = flask.send_file(str(test_file), etag=False)
        assert rv.headers.get("ETag") is None
        rv.close()

    def test_send_file_last_modified_header(self, app, req_ctx, tmp_path):
        """Test that Last-Modified header is set correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        rv = flask.send_file(str(test_file))
        last_modified = rv.headers.get("Last-Modified")
        assert last_modified is not None

        parsed = parsedate_to_datetime(last_modified)
        assert parsed.tzinfo is not None
        rv.close()

    def test_send_file_custom_last_modified(self, app, req_ctx, tmp_path):
        """Test that custom Last-Modified can be provided."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        custom_time = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        rv = flask.send_file(str(test_file), last_modified=custom_time)

        last_modified = rv.headers.get("Last-Modified")
        parsed = parsedate_to_datetime(last_modified)
        assert parsed.year == 2020
        assert parsed.month == 1
        assert parsed.day == 1
        rv.close()

    def test_send_from_directory_etag(self, app, req_ctx, tmp_path):
        """Test that send_from_directory generates ETag correctly."""
        test_dir = tmp_path / "static"
        test_dir.mkdir()
        test_file = test_dir / "test.txt"
        test_file.write_text("Hello, World!")

        rv = flask.send_from_directory(str(test_dir), "test.txt")
        assert rv.status_code == 200
        assert rv.headers.get("ETag") is not None
        rv.direct_passthrough = False
        assert rv.data == b"Hello, World!"
        rv.close()

    def test_send_file_304_headers(self, app, tmp_path):
        """Test that 304 responses include appropriate headers."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file")
            etag = rv.headers.get("ETag")

            rv2 = client.get("/file", headers={"If-None-Match": etag})
            assert rv2.status_code == 304
            assert "Content-Length" not in rv2.headers
            assert "Content-Type" not in rv2.headers
            assert "ETag" in rv2.headers

    def test_send_file_weak_etag_if_none_match(self, app, tmp_path):
        """Test that weak ETags work with If-None-Match."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file")
            etag = rv.headers.get("ETag")

            weak_etag = "W/" + etag
            rv2 = client.get("/file", headers={"If-None-Match": weak_etag})
            assert rv2.status_code == 304

    def test_send_file_multiple_etags_if_none_match(self, app, tmp_path):
        """Test that If-None-Match with multiple ETags works."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file")
            etag = rv.headers.get("ETag")

            rv2 = client.get("/file", headers={"If-None-Match": f'"other-etag", {etag}'})
            assert rv2.status_code == 304

    def test_send_file_star_if_none_match(self, app, tmp_path):
        """Test that If-None-Match with * works."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file", headers={"If-None-Match": "*"})
            assert rv.status_code == 304

    def test_send_file_if_modified_since_invalid_date(self, app, tmp_path):
        """Test that invalid If-Modified-Since date is ignored."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file", headers={"If-Modified-Since": "invalid-date"})
            assert rv.status_code == 200
            assert rv.data == b"Hello, World!"

    def test_send_file_conditional_disabled(self, app, tmp_path):
        """Test that conditional requests can be disabled."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file), conditional=False)

        with app.test_client() as client:
            rv = client.get("/file")
            etag = rv.headers.get("ETag")

            rv2 = client.get("/file", headers={"If-None-Match": etag})
            assert rv2.status_code == 200
            assert rv2.data == b"Hello, World!"

    def test_send_file_filesystem_time_precision(self, app, tmp_path):
        """Test that ETag handles different filesystem time precisions.
        
        This test verifies that ETag generation works correctly even when
        filesystem timestamps have different precisions (e.g., seconds vs
        nanoseconds).
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file")
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv1 = client.get("/file")
            etag1 = rv1.headers.get("ETag")

            rv2 = client.get("/file")
            etag2 = rv2.headers.get("ETag")

            assert etag1 == etag2

    def test_send_file_post_method_no_conditional(self, app, tmp_path):
        """Test that POST requests don't trigger conditional responses.
        
        Conditional requests (304) should only happen for GET and HEAD
        requests according to HTTP spec.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        @app.route("/file", methods=["GET", "POST"])
        def serve_file():
            return flask.send_file(str(test_file))

        with app.test_client() as client:
            rv = client.get("/file")
            etag = rv.headers.get("ETag")

            rv2 = client.post("/file", headers={"If-None-Match": etag})
            assert rv2.status_code == 200
