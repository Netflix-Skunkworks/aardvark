Aardvark
========
<img align="center" alt="Aardvark Logo" src="docs/images/aardvark_logo.jpg" width="10%" display="block">

Aardvark is a multi-account AWS IAM Access Advisor API


## Install:

    pip install aardvark

The phantomjs executable must be downloaded from http://phantomjs.org/download.html

## Configure Aardvark

The Aardvark config wizard will guide you through the setup.
- List of AWS Accounts, their names and identifiers.
- The name of the IAM Role to assume into in each account.
- The Database connection string.
- Location of the PhantomJS executable.
```
    aardvark config
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

    aardvark update

or

    aardvark update -a dev,test,prod

## API
Swagger is available for the API at `<Aardvark_Host>/apidocs/#!`.

## Notes

### Threads
Aardvark will launch the number of threads specified in the configuration.  Each of these threads
will launch a PhantomJS process to retrieve Access Advisor data for an account and then persist the
data.  We have discovered in testing that more than `6` threads causes the Phantom processes to fail
to complete.

### Database
The `regex` query is only supported in Postgres (natively) and SQLite (via some magic courtesy of Xion
  in the `sqla_regex` file).

## TODO:

See [TODO](TODO.md)
