import os.path
import logging
from logging import DEBUG, Formatter, StreamHandler
from logging.config import dictConfig
import sys

from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flasgger import Swagger

db = SQLAlchemy()

API_VERSION = '1'


def create_app():
    app = Flask(__name__, static_url_path='/static')
    Swagger(app)

    path = _find_config()
    if not path:
        print('No config')
        app.config.from_pyfile('_config.py')
    else:
        app.config.from_pyfile(path)

    # For ELB and/or Eureka
    @app.route('/healthcheck')
    def healthcheck():
        """Healthcheck
        Simple healthcheck that indicates the services is up
        ---
        responses:
          200:
            description: service is up
        """
        return 'ok'

    from aardvark import advisors
    app.register_blueprint(advisors.bp, url_prefix=f"/api/{API_VERSION}")

    # Extensions:
    db.init_app(app)
    setup_logging(app)

    return app


def _find_config():
    """Search for config.py in order of preference and return path if it exists, else None"""
    CONFIG_PATHS = [os.path.join(os.getcwd(), 'config.py'),
                    '/etc/aardvark/config.py',
                    '/apps/aardvark/config.py']
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None


def setup_logging(app):
    if not app.debug:
        if app.config.get('LOG_CFG'):
            # initialize the Flask logger (removes all handlers)
            dictConfig(app.config.get('LOG_CFG'))
            app.logger = logging.getLogger(__name__)
        else:
            handler = StreamHandler(stream=sys.stderr)

            handler.setFormatter(Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'))
            app.logger.setLevel(app.config.get('LOG_LEVEL', DEBUG))
            app.logger.addHandler(handler)
