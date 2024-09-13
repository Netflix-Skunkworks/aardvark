Aardvark - Multi-Account AWS IAM Access Advisor API
========
[![NetflixOSS Lifecycle](https://img.shields.io/osslifecycle/Netflix/osstracker.svg)]()
[![Discord chat](https://img.shields.io/discord/754080763070382130?logo=discord)](https://discord.gg/9kwMWa6)

<img align="center" alt="Aardvark Logo" src="docs/images/aardvark_logo.jpg" width="10%" display="block">

Aardvark is a multi-account AWS IAM Access Advisor API (and caching layer).

## Install:

Ensure that you have Python 3.6 or later. Python 2 is no longer supported.

```bash
git clone https://github.com/Netflix-Skunkworks/aardvark.git
cd aardvark
python3 -m venv env
. env/bin/activate
python setup.py develop
```

### Known Dependencies
 - libpq-dev

## Configure Aardvark

The Aardvark config wizard will guide you through the setup.
```
% aardvark config

Aardvark can use SWAG to look up accounts. https://github.com/Netflix-Skunkworks/swag-client
Do you use SWAG to track accounts? [yN]: no
ROLENAME: Aardvark
DATABASE [sqlite:////home/github/aardvark/aardvark.db]:
# Threads [5]:

>> Writing to config.py
```
- Whether to use [SWAG](https://github.com/Netflix-Skunkworks/swag-client) to enumerate your AWS accounts. (Optional, but useful when you have many accounts.)
- The name of the IAM Role to assume into in each account.
- The Database connection string. (Defaults to sqlite in the current working directory. Use RDS Postgres for production.)

## Create the DB tables

```
aardvark create_db
```

## IAM Permissions:

Aardvark needs an IAM Role in each account that will be queried.  Additionally, Aardvark needs to be launched with a role or user which can `sts:AssumeRole` into the different account roles.

AardvarkInstanceProfile:
- Only create one.
- Needs the ability to call `sts:AssumeRole` into all of the AardvarkRole's

AardvarkRole:
- Must exist in every account to be monitored.
- Must have a trust policy allowing `AardvarkInstanceProfile`.
- Has these permissions:
```
iam:GenerateServiceLastAccessedDetails
iam:GetServiceLastAccessedDetails
iam:listrolepolicies
iam:listroles
iam:ListUsers
iam:ListPolicies
iam:ListGroups
```

So if you are monitoring `n` accounts, you will always need `n+1` roles. (`n` AardvarkRoles and `1` AardvarkInstanceProfile).

Note: For locally running aardvark, you don't have to take care of the AardvarkInstanceProfile. Instead, just attach a policy which contains "sts:AssumeRole" to the user you are using on the AWS CLI to assume Aardvark Role. Also, the same user should be mentioned in the trust policy of Aardvark Role for proper assignment of the privileges.

## Gather Access Advisor Data

You'll likely want to refresh the Access Advisor data regularly.  We recommend running the `update` command about once a day.  Cron works great for this.

#### Without SWAG:

If you don't have SWAG you can pass comma separated account numbers:

    aardvark update -a 123456789012,210987654321

#### With SWAG:

Aardvark can use [SWAG](https://github.com/Netflix-Skunkworks/swag-client) to look up accounts, so you can run against all with:

    aardvark update

or by account name/tag with:

    aardvark update -a dev,test,prod


## API

### Start the API

    aardvark start_api -b 0.0.0.0:5000

In production, you'll likely want to have something like supervisor starting the API for you.

### Use the API

Swagger is available for the API at `<Aardvark_Host>/apidocs/#!`.

Aardvark responds to get/post requests. All results are paginated and pagination can be controlled by passing `count` and/or `page` arguments. Here are a few example queries:
```bash
curl localhost:5000/api/1/advisors
curl localhost:5000/api/1/advisors?phrase=SecurityMonkey
curl localhost:5000/api/1/advisors?arn=arn:aws:iam::000000000000:role/SecurityMonkey&arn=arn:aws:iam::111111111111:role/SecurityMonkey
curl localhost:5000/api/1/advisors?regex=^.*Monkey$
```

## Docker

Aardvark can also be deployed with Docker and Docker Compose. The Aardvark services are built on a shared container. You will need Docker and Docker Compose installed for this to work.

To configure the containers for your set of accounts create a `.env` file in the root of this directory. Define the environment variables within this file. This example uses AWS Access Keys. We recommend using instance roles in production.

```text
AARDVARK_ROLE=Aardvark
AARDVARK_ACCOUNTS=<account id>
AWS_DEFAULT_REGION=<aws region>
AWS_ACCESS_KEY_ID=<your access key>
AWS_SECRET_ACCESS_KEY=<you secret key>
```

| Name | Service | Description |
|---|---|---|
| `AARDVARK_ROLE` | `collector` | The name of the role for Aardvark to assume so that it can collect the data. |
| `AARDVARK_ACCOUNTS` | `collector` | Optional if using SWAG, otherwise required. Set this to a list of SWAG account name tags or a list of AWS account numbers from which to collect Access Advisor records. |
| `AWS_ARN_PARTITION` | `collector` | Required if not using an AWS Commercial region. For example, `aws-us-gov`. By default, this is `aws`. |
| `AWS_DEFAULT_REGION` | `collector` | Required if not running on an EC2 instance with an appropriate Instance Profile. Set these to the credentials of an AWS IAM user with permission to `sts:AssumeRole` to the Aardvark audit role. |
| `AWS_ACCESS_KEY_ID` | `collector` | Required if not running on an EC2 instance with an appropriate Instance Profile. Set these to the credentials of an AWS IAM user with permission to `sts:AssumeRole` to the Aardvark audit role. |
| `AWS_SECRET_ACCESS_KEY` | `collector` | Required if not running on an EC2 instance with an appropriate Instance Profile. Set these to the credentials of an AWS IAM user with permission to `sts:AssumeRole` to the Aardvark audit role. |
| `AARDVARK_DATABASE_URI` | `collector` and `apiserver` | Specify a custom database URI supported by SQL Alchemy. By default, this will use the `AARDVARK_DATA_DIR` value to create a SQLLite Database. Example: `sqlite:///$AARDVARK_DATA_DIR/aardvark.db` |

Once this file is created, then build the containers and start the services. Aardvark consists of three services:

- Init - The init container creates the database within the storage volume.
- API Server - This is the HTTP webserver will serve the data. By default, this is listening on [http://localhost:5000/apidocs/#!](http://localhost:5000/apidocs/#!).
- Collector - This is a daemon that will fetch and cache the data in the local SQL database. This should be run periodically.

```bash
# build the containers
docker-compose build

# start up the containers
docker-compose up
```

Finally, to clean up the environment

```bash
# bring down the containers
docker-compose down

# remove the containers
docker-compoes rm
```

## Notes

### Threads
Aardvark will launch the number of threads specified in the configuration.  Each of these threads
will retrieve Access Advisor data for an account and then persist the
data.

### Database
The `regex` query is only supported in Postgres (natively) and SQLite (via some magic courtesy of Xion
  in the `sqla_regex` file).

### TLS
We recommend enabling TLS for any service. Instructions for setting up TLS are out of scope for this document.

## Signals

> New in v0.3.1

Aardvark uses [Blinker](https://pythonhosted.org/blinker/) for signals in its update process. These signals can be used
for things like emitting metrics, additional logging, or taking more actions on accounts. You can use them by writing a
script that defines your handlers and calls `aardvark.manage.main()`. For example, create a file called
`signals_example.py` with the following contents:

```python
import logging

from aardvark.manage import main
from aardvark.updater import AccountToUpdate

logger = logging.getLogger('aardvark_signals')


@AccountToUpdate.on_ready.connect
def handle_on_ready(sender):
    logger.info(f"got on_ready from {sender}")


@AccountToUpdate.on_complete.connect
def handle_on_complete(sender):
    logger.info(f"got on_complete from {sender}")


if __name__ == "__main__":
    main()
```

This file can now be invoked in the same way as `manage.py`:

```bash
python signals_example.py update -a cool_account
```

The log output will be similar to the following:

```
INFO: getting bucket swag-bucket
INFO: Thread #1 updating account 123456789012 with all arns
INFO: got on_ready from <aardvark.updater.AccountToUpdate object at 0x10c379b50>
INFO: got on_complete from <aardvark.updater.AccountToUpdate object at 0x10c379b50>
INFO: Thread #1 persisting data for account 123456789012
INFO: Thread #1 FINISHED persisting data for account 123456789012
```

### Available signals

| Class | Signals |
|-------|---------|
| `manage.UpdateAccountThread` | `on_ready`, `on_complete`, `on_failure` |
| `updater.AccountToUpdate` | `on_ready`, `on_complete`, `on_error`, `on_failure` |

## TODO:

See [TODO](TODO.md)
