#!/usr/bin/env python3
"""
Bootstrap script for Flask development environment.

Sets up everything needed for Flask development:
1. Creates virtual environment
2. Installs development dependencies
3. Installs Flask in editable mode
4. Sets up pre-commit hooks
5. Runs initial tests

Usage:
    python scripts/bootstrap.py
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"→ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
    )

    if check and result.returncode != 0:
        print(f"✗ Command failed with exit code {result.returncode}")
        sys.exit(1)

    print()
    return result


def check_python_version() -> None:
    """Check that Python version meets requirements."""
    if sys.version_info < (3, 10):
        print(f"✗ Python 3.10+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def create_venv() -> None:
    """Create virtual environment if it doesn't exist."""
    venv_path = ROOT / ".venv"
    if venv_path.exists():
        print(f"✓ Virtual environment already exists at {venv_path}")
        return

    print("Creating virtual environment...")
    run_command([sys.executable, "-m", "venv", str(venv_path)])
    print(f"✓ Created virtual environment at {venv_path}")


def get_venv_python() -> str:
    """Get path to venv Python executable."""
    venv_path = ROOT / ".venv"
    if sys.platform == "win32":
        return str(venv_path / "Scripts" / "python.exe")
    return str(venv_path / "bin" / "python")


def install_dependencies() -> None:
    """Install development dependencies."""
    venv_python = get_venv_python()

    print("Upgrading pip...")
    run_command([venv_python, "-m", "pip", "install", "--upgrade", "pip"])

    print("Installing development dependencies...")
    run_command([venv_python, "-m", "pip", "install", "-e", ".[dev,docs,tests]"])

    print("✓ Dependencies installed")


def setup_precommit() -> None:
    """Set up pre-commit hooks."""
    venv_python = get_venv_python()

    print("Installing pre-commit hooks...")
    result = run_command([venv_python, "-m", "pre_commit", "install"], check=False)

    if result.returncode == 0:
        print("✓ Pre-commit hooks installed")
    else:
        print("⚠ Pre-commit setup failed (may not be configured yet)")
        print("  Run manually: pre-commit install")


def run_initial_tests() -> None:
    """Run initial test suite to verify setup."""
    venv_python = get_venv_python()

    print("Running initial test suite...")
    result = run_command([venv_python, "-m", "pytest", "tests/", "-v", "--tb=short"], check=False)

    if result.returncode == 0:
        print("✓ All tests passed")
    else:
        print("⚠ Some tests failed (this may be expected on certain platforms)")
        print("  Review the output above for details")


def print_next_steps() -> None:
    """Print next steps for the developer."""
    print("\n" + "=" * 60)
    print("✅ Flask development environment ready!")
    print("=" * 60)
    print()
    print("Activate the virtual environment:")
    if sys.platform == "win32":
        print("  .venv\\Scripts\\activate")
    else:
        print("  source .venv/bin/activate")
    print()
    print("Common commands:")
    print("  pytest tests/              # Run tests")
    print("  pytest tests/test_basic.py # Run specific test file")
    print("  ruff check .               # Lint code")
    print("  ruff format .              # Format code")
    print("  mypy src/                  # Type check")
    print("  sphinx-build docs/ docs/_build  # Build docs")
    print()
    print("For more information, see:")
    print("  - CONTRIBUTING.rst")
    print("  - docs/development.rst")
    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap Flask development environment.",
        epilog="""Examples:
  bootstrap.py                # full setup
  bootstrap.py --skip-tests   # setup without running tests""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running initial tests",
    )

    args = parser.parse_args()

    print("Flask Development Environment Bootstrap")
    print("=" * 60)
    print()

    # Step 1: Check Python version
    print("Step 1: Checking Python version")
    print("-" * 60)
    check_python_version()
    print()

    # Step 2: Create virtual environment
    print("Step 2: Creating virtual environment")
    print("-" * 60)
    create_venv()
    print()

    # Step 3: Install dependencies
    print("Step 3: Installing dependencies")
    print("-" * 60)
    install_dependencies()
    print()

    # Step 4: Set up pre-commit
    print("Step 4: Setting up pre-commit hooks")
    print("-" * 60)
    setup_precommit()
    print()

    # Step 5: Run initial tests (optional)
    if not args.skip_tests:
        print("Step 5: Running initial tests")
        print("-" * 60)
        run_initial_tests()
        print()
    else:
        print("Step 5: Skipping initial tests (--skip-tests)")
        print()

    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    main()
