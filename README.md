Aardvark
========
[![NetflixOSS Lifecycle](https://img.shields.io/osslifecycle/Netflix/osstracker.svg)]()
[![Gitter chat](https://badges.gitter.im/gitterHQ/gitter.png)](https://gitter.im/netflix-repokid)

<img align="center" alt="Aardvark Logo" src="docs/images/aardvark_logo.jpg" width="10%" display="block">

Aardvark is a multi-account AWS IAM Access Advisor API (and caching layer).

Aardvark uses PhantomJS to log into the AWS Console and obtain access advisor data.  It then presents a RESTful API for other apps to query.

## Install:

```bash
mkvirtualenv aardvark
git clone git@github.com:Netflix-Skunkworks/aardvark.git
cd aardvark
python setup.py develop
```

### Known Dependencies
 - [PhantomJS*](http://phantomjs.org/download.html)
 - libpq-dev
 
**Note**: Aardvark requires at least phantomjs 2.1.1.  We've seen odd behavior running with older versions.

## Configure Aardvark

The Aardvark config wizard will guide you through the setup.
```
% aardvark config

Aardvark can use SWAG to look up accounts. https://github.com/Netflix-Skunkworks/swag-client
Do you use SWAG to track accounts? [yN]: no
ROLENAME: Aardvark
DATABASE [sqlite:////home/github/aardvark/aardvark.db]:
# Threads [5]: 
Path to phantomjs: 

>> Writing to config.py
```
- Whether to use [SWAG](https://github.com/Netflix-Skunkworks/swag-client) to enumerate your AWS accounts. (Optional, but useful when you have many accounts.)
- The name of the IAM Role to assume into in each account.
- The Database connection string. (Defaults to sqlite in the current working directory. Use RDS Postgres for production.)
- Location of the PhantomJS executable. (Will attempt to find `phantomjs` in your path before asking.)  Ensure it is at least `v2.1.1`.

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
```

So if you are monitoring `n` accounts, you will always need `n+1` roles. (`n` AardvarkRoles and `1` AardvarkInstanceProfile).

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

## Notes

### Threads
Aardvark will launch the number of threads specified in the configuration.  Each of these threads
will launch a PhantomJS process to retrieve Access Advisor data for an account and then persist the
data.  We have discovered in testing that more than `6` threads causes the Phantom processes to fail
to complete.

### Database
The `regex` query is only supported in Postgres (natively) and SQLite (via some magic courtesy of Xion
  in the `sqla_regex` file).

### Access Advisor Data
Aardvark currently only supports gathering access advisor data for IAM Roles.  AWS provides data for other item types like IAM Users, IAM Groups, and Managed Policies.  Aardvark does not support these other items.  It would be easy enough to add support if you would like to contribute.

### TLS
We recommend enabling TLS for any service. Instructions for setting up TLS are out of scope for this document.

## TODO:

See [TODO](TODO.md)
