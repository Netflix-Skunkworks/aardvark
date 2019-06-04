#!/bin/bash

echo "Creating aardvark db if not already created..."
/usr/local/bin/aardvark create_db

echo "Creating the collector cronjob..."
/bin/sed -i -e "s/AARDVARK_CRONJOB_SPEC/$AARDVARK_CRONJOB_SPEC/g" \
            -e "s/AARDVARK_ACCOUNTS/$AARDVARK_ACCOUNTS/g" \
            -e "s#ENV_AWS_CONTAINER_CREDENTIALS_RELATIVE_URI#$AWS_CONTAINER_CREDENTIALS_RELATIVE_URI#g" \
            -e "s#ENV_AWS_CONTAINER_CREDENTIALS_FULL_URI#$AWS_CONTAINER_CREDENTIALS_FULL_URI#g" \
            -e "s#ENV_AWS_CONTAINER_AUTHORIZATION_TOKEN#$AWS_CONTAINER_AUTHORIZATION_TOKEN#g" \
            /etc/cron.d/aardvark-collector
echo "Starting cron daemon..."
/usr/sbin/cron -f
