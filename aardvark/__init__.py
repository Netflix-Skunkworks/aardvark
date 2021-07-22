import logging
import os.path
from logging.config import dictConfig

from dynaconf.contrib import FlaskDynaconf
from flasgger import Swagger
from flask import Flask

from aardvark.config import settings
from aardvark.persistence.sqlalchemy import SQLAlchemyPersistence
from aardvark.advisors import advisor_bp

BLUEPRINTS = [advisor_bp]

API_VERSION = "1"

log = logging.getLogger("aardvark")


def create_app(*args, **kwargs):
    init_logging()
    app = Flask(__name__, static_url_path="/static")
    Swagger(app)
    persistence = SQLAlchemyPersistence()

    FlaskDynaconf(app, **kwargs)

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


def init_logging():
    log_cfg = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s %(levelname)s: %(message)s '
                    '[in %(pathname)s:%(lineno)d]'
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filename': 'aardvark.log',
                'maxBytes': 10485760,
                'backupCount': 100,
                'encoding': 'utf8'
            },
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            'aardvark': {
                'handlers': ['file', 'console'],
                'level': 'DEBUG'
            }
        }
    }
    dictConfig(log_cfg)


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
