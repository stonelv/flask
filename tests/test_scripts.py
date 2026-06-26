"""Tests for release automation scripts."""
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


class TestBumpVersion:
    """Tests for scripts/bump_version.py."""

    def test_script_exists(self):
        """Verify bump_version.py exists."""
        assert (SCRIPTS_DIR / "bump_version.py").exists()

    def test_help_output(self):
        """Test --help flag works."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bump_version.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "bump" in result.stdout.lower() or "version" in result.stdout.lower()
        assert "--dry-run" in result.stdout

    def test_patch_bump_dry_run(self):
        """Test patch version bump with --dry-run."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bump_version.py"), "patch", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        # Should succeed and show what would change
        assert result.returncode == 0
        assert "dry-run" in result.stdout.lower() or "would" in result.stdout.lower()

    def test_invalid_bump_type(self):
        """Test invalid bump type fails gracefully."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bump_version.py"), "invalid"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()


class TestGenerateChangelog:
    """Tests for scripts/generate_changelog.py."""

    def test_script_exists(self):
        """Verify generate_changelog.py exists."""
        assert (SCRIPTS_DIR / "generate_changelog.py").exists()

    def test_help_output(self):
        """Test --help flag works."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "generate_changelog.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "changelog" in result.stdout.lower() or "generate" in result.stdout.lower()
        assert "--dry-run" in result.stdout

    def test_dry_run(self):
        """Test --dry-run flag doesn't modify files."""
        changes_file = Path(__file__).parent.parent / "CHANGES.rst"
        original_content = changes_file.read_text() if changes_file.exists() else None

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "generate_changelog.py"), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # File should not be modified
        if original_content is not None:
            assert changes_file.read_text() == original_content

        # Should succeed or gracefully handle no tags
        assert result.returncode in [0, 1]
        if result.returncode == 0:
            assert "dry-run" in result.stdout.lower() or "no files" in result.stdout.lower()


class TestRollback:
    """Tests for scripts/rollback.py."""

    def test_script_exists(self):
        """Verify rollback.py exists."""
        assert (SCRIPTS_DIR / "rollback.py").exists()

    def test_help_output(self):
        """Test --help flag works."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "rollback.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "rollback" in result.stdout.lower() or "version" in result.stdout.lower()
        assert "--dry-run" in result.stdout

    def test_missing_version_arg(self):
        """Test missing version argument fails gracefully."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "rollback.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "required" in result.stderr.lower()

    def test_dry_run(self):
        """Test --dry-run with a version."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "rollback.py"), "3.1.0", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        # Should succeed and show what would be done
        assert result.returncode == 0
        assert "dry-run" in result.stdout.lower() or "would" in result.stdout.lower()


class TestBootstrap:
    """Tests for scripts/bootstrap.py."""

    def test_script_exists(self):
        """Verify bootstrap.py exists."""
        assert (SCRIPTS_DIR / "bootstrap.py").exists()

    def test_help_output(self):
        """Test --help flag works."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bootstrap.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "bootstrap" in result.stdout.lower() or "setup" in result.stdout.lower()
        assert "--skip-tests" in result.stdout
