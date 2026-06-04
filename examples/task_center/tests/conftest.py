import pytest
import asyncio
from task_center import create_app
from task_center.database import db_session, Base, get_engine
from task_center.executor import executor


import tempfile
import os

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Use a temporary file database for testing multi-threading
    db_file = tempfile.mktemp(suffix='.db')
    app = create_app({
        "TESTING": True,
        "DATABASE": f"sqlite:///{db_file}",
    })

    # Recreate tables for test database
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Set engine for executor
    executor.set_engine(engine)

    yield app

    # Cleanup - wait for tasks to complete before removing database
    try:
        executor.wait_for_all_tasks(timeout=5)
    except:
        pass
    executor.clear()
    db_session.remove()
    engine.dispose()
    try:
        os.unlink(db_file)
    except:
        pass


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
async def async_loop():
    """Create an asyncio loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
