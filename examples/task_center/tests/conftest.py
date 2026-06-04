import pytest
import asyncio
import os
import tempfile
import time
import logging
from task_center import create_app, db
from task_center.executor import get_executor, _executor as global_executor


@pytest.fixture
def app():
    # Use a temporary file database to avoid connection isolation issues
    # with in-memory SQLite databases across threads
    db_fd, db_path = tempfile.mkstemp(suffix='.sqlite')
    os.close(db_fd)
    
    try:
        # Reset global executor state
        global_executor.reset()
        
        app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        })
        
        with app.app_context():
            db.create_all()
        
        yield app
        
        # Stop executor before cleaning up database
        global_executor.stop(timeout=5)
        
        # Wait for thread to actually stop
        for _ in range(50):
            if global_executor._thread_stopped:
                break
            time.sleep(0.1)
        
        # Clear logging handlers to prevent closed file errors
        task_logger = logging.getLogger("task_center")
        for handler in task_logger.handlers[:]:
            task_logger.removeHandler(handler)
        
        with app.app_context():
            db.drop_all()
            db.engine.dispose()
            
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def executor(app):
    return get_executor()


@pytest.fixture
async def async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
