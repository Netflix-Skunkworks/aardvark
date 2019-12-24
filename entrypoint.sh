#!/bin/bash
set -ex

# set the default values of environment variables
AARDVARK_ROLE="${AARDVARK_ROLE:-Aardvark}"
AARDVARK_DATA_DIR="${AARDVARK_DATA_DIR:-/data}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
AWS_ARN_PARTITION="${AWS_ARN_PARTITION:-aws}"

# if the database uri is not set, create sqlite database
if [[ -z "${AARDVARK_DATABASE_URI}" ]]; then
  AARDVARK_DATABASE_URI="sqlite:///$AARDVARK_DATA_DIR/aardvark.db"
fi

# write the configuration file to disk
cat > /etc/aardvark/config.py <<EOF
ROLENAME = "$AARDVARK_ROLE"
REGION = "$AWS_DEFAULT_REGION"
ARN_PARTITION = "$AWS_ARN_PARTITION"
SQLALCHEMY_DATABASE_URI = "$AARDVARK_DATABASE_URI"
SQLALCHEMY_TRACK_MODIFICATIONS = False
NUM_THREADS = 5
LOG_CFG = {
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
EOF

# hand of the foreground process to the passed command
exec "$@"
