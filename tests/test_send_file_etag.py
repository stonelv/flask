"""Tests for stable ETag generation and conditional requests in send_file.

This module tests the custom ETag generation and 304 response header
filtering added to Flask's send_file and send_from_directory functions.
"""

import hashlib
import os
import tempfile
import typing as t
from datetime import datetime, timedelta, timezone
from email.utils import formatdate
from io import BytesIO
from pathlib import Path

import flask
import pytest


def app_with_send_file_route() -> flask.Flask:
    """Create a Flask app with a send_file route for testing."""
    app = flask.Flask(__name__)
    
    @app.route("/send-file")
    def send_file_route():
        return flask.send_file(
            flask.request.args["path"],
            etag=True,
        )
    
    return app


class TestStableETagGeneration:
    """Test the stable ETag generation based on mtime and size.
    
    These tests verify that our custom _generate_stable_etag function
    produces stable ETags based only on file modification time (seconds
    precision) and size, not on inode or other filesystem-specific
    attributes that may change across systems or restarts.
    """
    
    def test_etag_generation_based_on_mtime_and_size(self, tmp_path: Path) -> None:
        """ETag should be based on mtime (seconds) and size, not inode."""
        from flask.helpers import _generate_stable_etag
        
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Hello, World!")
        
        stat = os.stat(test_file)
        mtime_seconds = int(stat.st_mtime)
        size = stat.st_size
        
        expected_input = f"{mtime_seconds}-{size}"
        expected_etag = hashlib.md5(expected_input.encode("utf-8")).hexdigest()
        
        actual_etag = _generate_stable_etag(test_file)
        
        assert actual_etag == expected_etag
    
    def test_etag_stable_quick_writes(self, tmp_path: Path) -> None:
        """ETag should be stable for writes within the same second.
        
        This tests that using seconds-precision mtime prevents ETag
        thrashing when files are written multiple times within the
        same second.
        """
        from flask.helpers import _generate_stable_etag
        
        test_file = tmp_path / "test.txt"
        
        test_file.write_bytes(b"Version 1")
        stat1 = os.stat(test_file)
        etag1 = _generate_stable_etag(test_file)
        
        test_file.write_bytes(b"Version 2")
        stat2 = os.stat(test_file)
        etag2 = _generate_stable_etag(test_file)
        
        if int(stat1.st_mtime) == int(stat2.st_mtime) and stat1.st_size == stat2.st_size:
            assert etag1 == etag2, "ETag should be stable for same mtime(sec) and size"
        else:
            assert etag1 != etag2, "ETag should change if mtime(sec) or size differs"
    
    def test_etag_changes_when_content_changes(self, tmp_path: Path) -> None:
        """ETag should change when file content (and thus size) changes."""
        from flask.helpers import _generate_stable_etag
        
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Content A")
        etag1 = _generate_stable_etag(test_file)
        
        test_file.write_bytes(b"Content B which is longer")
        etag2 = _generate_stable_etag(test_file)
        
        assert etag1 != etag2, "ETag should change when content differs"
    
    def test_etag_send_file_integration(self, tmp_path: Path) -> None:
        """send_file with etag=True should use our stable ETag.
        
        This verifies that send_file actually uses our custom
        _generate_stable_etag function when etag=True.
        """
        from flask.helpers import _generate_stable_etag
        
        test_file = tmp_path / "test.txt"
        content = b"send_file integration test"
        test_file.write_bytes(content)
        
        expected_etag = _generate_stable_etag(test_file)
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv = client.get(f"/send-file?path={test_file}")
            
            assert rv.status_code == 200
            
            etag_header = rv.headers.get("ETag")
            assert etag_header is not None
            assert etag_header == f'"{expected_etag}"'
            
            rv.close()


class TestConditionalRequests:
    """Test conditional request handling (If-None-Match, If-Modified-Since).
    
    These tests verify that when a client sends conditional request headers,
    the server correctly returns 304 Not Modified when the resource hasn't
    changed, and 200 OK with the full response when it has.
    """
    
    def test_if_none_match_exact_match(self, tmp_path: Path) -> None:
        """If-None-Match with exact ETag should return 304.
        
        RFC 7232: If-None-Match with one or more entity-tags, the
        recipient MUST use the weak comparison function when comparing
        entity-tags.
        """
        test_file = tmp_path / "test.txt"
        content = b"conditional request test"
        test_file.write_bytes(content)
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv1 = client.get(f"/send-file?path={test_file}")
            assert rv1.status_code == 200
            
            etag = rv1.headers.get("ETag")
            assert etag is not None
            
            rv1.close()
            
            rv2 = client.get(
                f"/send-file?path={test_file}",
                headers={"If-None-Match": etag},
            )
            
            assert rv2.status_code == 304
            assert rv2.data == b""
            
            rv2.close()
    
    def test_if_none_match_star(self, tmp_path: Path) -> None:
        """If-None-Match: * should return 304 if the file exists.
        
        RFC 7232: The value "*" is special, meaning "any current
        representation of the target resource".
        """
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"star match test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv = client.get(
                f"/send-file?path={test_file}",
                headers={"If-None-Match": "*"},
            )
            
            assert rv.status_code == 304
            
            rv.close()
    
    def test_if_none_match_no_match(self, tmp_path: Path) -> None:
        """If-None-Match with non-matching ETag should return 200."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"no match test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv = client.get(
                f"/send-file?path={test_file}",
                headers={"If-None-Match": '"nonexistent-etag"'},
            )
            
            assert rv.status_code == 200
            
            rv.close()
    
    def test_if_modified_since_same_time(self, tmp_path: Path) -> None:
        """If-Modified-Since with same time as Last-Modified returns 304."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"if-modified-since test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv1 = client.get(f"/send-file?path={test_file}")
            assert rv1.status_code == 200
            
            last_modified = rv1.headers.get("Last-Modified")
            assert last_modified is not None
            
            rv1.close()
            
            rv2 = client.get(
                f"/send-file?path={test_file}",
                headers={"If-Modified-Since": last_modified},
            )
            
            assert rv2.status_code == 304
            
            rv2.close()
    
    def test_if_modified_since_newer(self, tmp_path: Path) -> None:
        """If-Modified-Since with a future date returns 304.
        
        If the requested variant has not been modified since the time
        specified in this field, the server SHOULD return a 304 response.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"future date test")
        
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        if_modified_since = formatdate(future_date.timestamp(), usegmt=True)
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv = client.get(
                f"/send-file?path={test_file}",
                headers={"If-Modified-Since": if_modified_since},
            )
            
            assert rv.status_code == 304
            
            rv.close()
    
    def test_both_headers_if_none_match_takes_precedence(self, tmp_path: Path) -> None:
        """If-None-Match should take precedence over If-Modified-Since.
        
        RFC 7232: If both If-None-Match and If-Modified-Since are present,
        the server MUST ignore If-Modified-Since unless If-None-Match
        evaluates to false.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"precedence test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv1 = client.get(f"/send-file?path={test_file}")
            assert rv1.status_code == 200
            
            etag = rv1.headers.get("ETag")
            assert etag is not None
            
            rv1.close()
            
            past_date = datetime.now(timezone.utc) - timedelta(days=1)
            if_modified_since = formatdate(past_date.timestamp(), usegmt=True)
            
            rv2 = client.get(
                f"/send-file?path={test_file}",
                headers={
                    "If-None-Match": etag,
                    "If-Modified-Since": if_modified_since,
                },
            )
            
            assert rv2.status_code == 304
            
            rv2.close()


class TestHEADAndRangeRequests:
    """Test HEAD and Range request behavior.
    
    These tests verify that conditional requests work correctly with
    HEAD requests, and that Range requests have the expected behavior
    with conditional headers.
    """
    
    def test_head_request_etag_present(self, tmp_path: Path) -> None:
        """HEAD request should include ETag header but no body."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"head request test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv = client.head(f"/send-file?path={test_file}")
            
            assert rv.status_code == 200
            assert rv.headers.get("ETag") is not None
            assert rv.data == b""
            
            rv.close()
    
    def test_head_request_if_none_match(self, tmp_path: Path) -> None:
        """HEAD request with If-None-Match should return 304 on match."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"head conditional test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv1 = client.head(f"/send-file?path={test_file}")
            assert rv1.status_code == 200
            
            etag = rv1.headers.get("ETag")
            assert etag is not None
            
            rv1.close()
            
            rv2 = client.head(
                f"/send-file?path={test_file}",
                headers={"If-None-Match": etag},
            )
            
            assert rv2.status_code == 304
            
            rv2.close()
    
    def test_range_request_returns_206(self, tmp_path: Path) -> None:
        """Range request should return 206 Partial Content.
        
        Range requests with If-Range header should work correctly.
        """
        test_file = tmp_path / "test.txt"
        content = b"0123456789"
        test_file.write_bytes(content)
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv = client.get(
                f"/send-file?path={test_file}",
                headers={"Range": "bytes=0-4"},
            )
            
            assert rv.status_code == 206
            assert rv.data == b"01234"
            
            rv.close()


class TestWeakETagsAndMultipleETags:
    """Test weak ETag and multiple ETag handling.
    
    RFC 7232: If-None-Match uses weak comparison.
    """
    
    def test_if_none_match_with_weak_etag(self, tmp_path: Path) -> None:
        """If-None-Match with weak ETag should match strong ETag.
        
        Weak comparison: W/"etag" matches "etag" for If-None-Match.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"weak etag test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv1 = client.get(f"/send-file?path={test_file}")
            assert rv1.status_code == 200
            
            strong_etag = rv1.headers.get("ETag")
            assert strong_etag is not None
            assert not strong_etag.startswith("W/")
            
            weak_etag = f"W/{strong_etag}"
            
            rv1.close()
            
            rv2 = client.get(
                f"/send-file?path={test_file}",
                headers={"If-None-Match": weak_etag},
            )
            
            assert rv2.status_code == 304
            
            rv2.close()
    
    def test_multiple_etags_in_if_none_match(self, tmp_path: Path) -> None:
        """If-None-Match with multiple ETags should match any of them."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"multiple etags test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv1 = client.get(f"/send-file?path={test_file}")
            assert rv1.status_code == 200
            
            actual_etag = rv1.headers.get("ETag")
            assert actual_etag is not None
            
            rv1.close()
            
            rv2 = client.get(
                f"/send-file?path={test_file}",
                headers={"If-None-Match": '"other-etag1", "other-etag2", ' + actual_etag},
            )
            
            assert rv2.status_code == 304
            
            rv2.close()


class Test304ResponseHeaders:
    """Test that 304 responses have appropriate headers.
    
    RFC 7232: A 304 response MUST generate a response body of zero length.
    A server sending a 304 response MUST generate any of the following
    header fields that would have been sent in a 200 response to the same
    request: Cache-Control, Content-Location, Date, ETag, Expires, and
    Vary.
    """
    
    def test_304_response_has_etag(self, tmp_path: Path) -> None:
        """304 response should include ETag header."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"304 headers test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv1 = client.get(f"/send-file?path={test_file}")
            assert rv1.status_code == 200
            
            etag = rv1.headers.get("ETag")
            assert etag is not None
            
            rv1.close()
            
            rv2 = client.get(
                f"/send-file?path={test_file}",
                headers={"If-None-Match": etag},
            )
            
            assert rv2.status_code == 304
            assert rv2.headers.get("ETag") == etag
            
            rv2.close()
    
    def test_304_response_empty_body(self, tmp_path: Path) -> None:
        """304 response MUST have empty body."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"empty body test")
        
        app = app_with_send_file_route()
        
        with app.test_client() as client:
            rv1 = client.get(f"/send-file?path={test_file}")
            assert rv1.status_code == 200
            
            etag = rv1.headers.get("ETag")
            assert etag is not None
            
            rv1.close()
            
            rv2 = client.get(
                f"/send-file?path={test_file}",
                headers={"If-None-Match": etag},
            )
            
            assert rv2.status_code == 304
            assert rv2.data == b""
            
            rv2.close()
