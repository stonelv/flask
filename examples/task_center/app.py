"""
Task Center Application Entry Point
Run this file to start the development server.
"""
from task_center import create_app

app = create_app()

if __name__ == "__main__":
    import sys
    port = 8888
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run(host="0.0.0.0", port=port, debug=True)
