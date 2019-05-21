import boto3
import json
import os
import os.path
import logging
from logging import DEBUG, Formatter, StreamHandler
from logging.config import dictConfig
import sys

from jinja2 import Environment, PackageLoader, select_autoescape
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flasgger import Swagger


db = SQLAlchemy()

from aardvark.view import mod as advisor_bp  # noqa

BLUEPRINTS = [
    advisor_bp
]

API_VERSION = '1'


def create_app():
    app = Flask(__name__, static_url_path='/static')
    Swagger(app)

    path = _find_config()
    if not path:
        print('No config. Trying to generate one from a template.')
        try:
            env = Environment(loader=PackageLoader('aardvark', 'templates'), autoescape=select_autoescape(['html', 'xml']))
            config_template = env.get_template('config.py.j2')
            config_json = json.loads(os.environ.get('config_json', {}))
            if not set(['role_name', 'region', 'secret_id']) <= set(config_json.keys()) or \
                    len([v for v in config_json.itervalues() if not v]) > 0:
                raise Exception('At least one of config variables {k} missing or empty.'.format(k=', '.join(config_json.keys())))
            session = boto3.session.Session(region_name=config_json['region'])
            client = session.client('secretsmanager')
            secret = json.loads(client.get_secret_value(SecretId=config_json['secret_id']))['SecretString']
            with open('/etc/aardvark/config.py') as fd:
                print >>fd, config_template.render(role_name=config_json['role_name'],
                                                   region=config_json['region'],
                                                   db_username=secret['username'],
                                                   db_password=secret['password'],
                                                   db_endpoint=secret['host'],
                                                   db_name=secret['dbname'])
        except Exception:
            print('Failed generating config from template. Falling back to hardcoded values.')
            # no template found; catchall
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

    # Blueprints
    for bp in BLUEPRINTS:
        app.register_blueprint(bp, url_prefix="/api/{0}".format(API_VERSION))

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
            app.logger
            dictConfig(app.config.get('LOG_CFG'))
            app.logger = logging.getLogger(__name__)
        else:
            handler = StreamHandler(stream=sys.stderr)

            handler.setFormatter(Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'))
            app.logger.setLevel(app.config.get('LOG_LEVEL', DEBUG))
            app.logger.addHandler(handler)
