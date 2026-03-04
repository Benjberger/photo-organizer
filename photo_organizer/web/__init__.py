"""Flask web UI for Photo Organizer."""

import secrets

from flask import Flask, render_template


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__,
                static_folder="static",
                template_folder="templates")

    app.secret_key = secrets.token_hex(16)

    from photo_organizer.web.routes import (
        browse, thumbnails, metadata, organize,
        duplicates, rename, review, select, group,
    )

    app.register_blueprint(browse.bp)
    app.register_blueprint(thumbnails.bp)
    app.register_blueprint(metadata.bp)
    app.register_blueprint(organize.bp)
    app.register_blueprint(duplicates.bp)
    app.register_blueprint(rename.bp)
    app.register_blueprint(review.bp)
    app.register_blueprint(select.bp)
    app.register_blueprint(group.bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app
