"""Launch the Photo Organizer web UI without a console window.

The .pyw extension tells Windows to use pythonw.exe, which runs
Python without opening a terminal. The Flask server runs in the
background and the browser opens automatically.
"""

import sys
import threading
import webbrowser

# Ensure the project is on the path
sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")

from photo_organizer.web import create_app

PORT = 5000

def open_browser():
    webbrowser.open(f"http://127.0.0.1:{PORT}")

if __name__ == "__main__":
    app = create_app()
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
