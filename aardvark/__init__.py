# ensure absolute import for python3
from __future__ import absolute_import

import os.path
import logging
from logging import DEBUG, Formatter, StreamHandler
from logging.config import dictConfig
import sys

from flask import Flask
from flasgger import Swagger

from aardvark.models.sqlalchemy.utils import db_session, init_db
from aardvark.view import mod as advisor_bp  # noqa

BLUEPRINTS = [advisor_bp]

API_VERSION = "1"


def create_app():
    app = Flask(__name__, static_url_path="/static")
    Swagger(app)

    path = _find_config()
    if not path:
        print("No config")
        app.config.from_pyfile("_config.py")
    else:
        app.config.from_pyfile(path)

    # For ELB and/or Eureka
    @app.route("/healthcheck")
    def healthcheck():
        """Healthcheck
        Simple healthcheck that indicates the services is up
        ---
        responses:
          200:
            description: service is up
        """
        return "ok"

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    # Blueprints
    for bp in BLUEPRINTS:
        app.register_blueprint(bp, url_prefix="/api/{0}".format(API_VERSION))

    # Extensions:
    init_db()
    setup_logging(app)

    return app


def _find_config():
    """Search for config.py in order of preference and return path if it exists, else None"""
    CONFIG_PATHS = [
        os.path.join(os.getcwd(), "config.ini"),
        "/etc/aardvark/config.ini",
        "/apps/aardvark/config.ini",
    ]
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None


def setup_logging(app):
    if not app.debug:
        if app.config.get("LOG_CFG"):
            # initialize the Flask logger (removes all handlers)
            dictConfig(app.config.get("LOG_CFG"))
            app.logger = logging.getLogger(__name__)
        else:
            handler = StreamHandler(stream=sys.stderr)

            handler.setFormatter(
                Formatter(
                    "%(asctime)s %(levelname)s: %(message)s "
                    "[in %(pathname)s:%(lineno)d]"
                )
            )
            app.logger.setLevel(app.config.get("LOG_LEVEL", DEBUG))
            app.logger.addHandler(handler)
