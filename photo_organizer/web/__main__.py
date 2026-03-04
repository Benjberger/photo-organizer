"""Run the web UI: python -m photo_organizer.web"""

from photo_organizer.web import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
