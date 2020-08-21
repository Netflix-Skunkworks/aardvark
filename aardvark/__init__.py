# ensure absolute import for python3
from __future__ import absolute_import

import logging
import os.path
from logging.config import dictConfig

from flasgger import Swagger
from flask import Flask

from aardvark.configuration import CONFIG
from aardvark.persistence.sqlalchemy import SQLAlchemyPersistence
from aardvark.view import advisor_bp

BLUEPRINTS = [advisor_bp]

API_VERSION = "1"

persistence = SQLAlchemyPersistence()
dictConfig(CONFIG["logging"].get())
log = logging.getLogger("aardvark")


def create_app(test_config=None):
    app = Flask(__name__, static_url_path="/static")
    Swagger(app)

    if test_config is not None:
        app.config.update(test_config)

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

    # Blueprints
    for bp in BLUEPRINTS:
        app.register_blueprint(bp, url_prefix="/api/{0}".format(API_VERSION))

    # Extensions:
    persistence.init_db()

    return app


def _find_config():
    """Search for config.py in order of preference and return path if it exists, else None"""
    CONFIG_PATHS = [
        os.path.join(os.getcwd(), "config.py"),
        "/etc/aardvark/config.py",
        "/apps/aardvark/config.py",
    ]
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None
