from task_center import create_app
from task_center.config import setup_logging

app = create_app()
setup_logging(app)

if __name__ == '__main__':
    app.run(debug=True)
