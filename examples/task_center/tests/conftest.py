import pytest
import os
import tempfile
from task_center import create_app, db
from task_center.config import Config

class TestConfig(Config):
    TESTING = True
    TASK_EXECUTOR_MAX_WORKERS = 4

@pytest.fixture
def app():
    # Create a temporary file for the database to support concurrent access
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    TestConfig.SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    
    # Clean up the temporary database file
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
