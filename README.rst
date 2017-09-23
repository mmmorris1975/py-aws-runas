=========
AWS RUNAS
=========

A command to provide a friendly way to do an AWS STS AssumeRole operation so you can perform AWS API actions
using a particular set of permissions.  Includes integration with roles requiring MFA authentication!  Works
off of profile names configured in the AWS SDK configuration file.

This tool initially performs an AWS STS GetSessionToken call to handle MFA credentials, and caches the session
credentials, then makes the AssumeRole call.  This allows us to not have to re-enter the MFA information (if required)
every time AssumeRole is called (or when the AssumeRole credentials expire), only when new Session Tokens are requested
(by default 12 hours).  Unlike older versions of this program, the cached credentials are not compatible with awscli,
but you should be able to use aws-runas to wrap awscli commands using an assumed role without needing to input MFA info
every time.

See the following for more information on AWS SDK configuration files:

- http://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html
- https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration
- https://boto3.readthedocs.io/en/latest/guide/configuration.html#aws-config-file

Requirements
============

- Tested on python 2.7 and python 3
- boto3 python library, version 1.3.1 or higher

Installation
============

Using `pip` is the preferred method to install this tool, and will install the package from pypi.  `pip install aws-runas`

It can also be installed via `pip` from a local copy of the source repo, `pip install .` from the repo directory should do the trick.
Running `make install` should also work as well.

Configuration
=============

To configure a profile in the .aws/config file for using AssumeRole, make sure the `source_profile` and `role_arn` attributes are
set for the profile.  The `role_arn` attribute will determine which role will be assumed for that profile.  The `source_profile`
attribute specifies the name of the profile which will be used to perform the GetSessionToken operation.

If the `mfa_serial` attribute is present in the profile configuration, That MFA device will be used when requesting or refreshing
the session token.

Example:

| [profile admin]
| source_profile = default
| role_arn = arn:aws:iam::987654321098:role/admin_role
| mfa_serial = arn:aws:iam::123456789098:mfa/iam_user

Usage
=====
| usage: aws-runas [-h] [-l] [-m] [-e] [-s] [-v] [-V] [profile] ...
|
| Create an environment for interacting with the AWS API using an assumed role
|
| positional arguments:
|   profile           name of profile
|   cmd               command to execute using configured profile
|
| optional arguments:
|   -h, --help        show this help message and exit
|   -l, --list-roles  list role ARNs you are able to assume
|   -m, --list-mfa    list the ARN of the MFA device associated with the account
|   -e, --expiration  Show token expiration time
|   -s, --session     print eval()-able session token info
|   -v, --verbose     print verbose/debug messages
|   -V, --version     print program version and exit

Listing available roles
-----------------------

Use the `-l` option to see the list of role ARNs your IAM account is authorized to assume.
May be helpful for setting up your AWS config file.  If `profile` arg is specified, list
roles available for the given profile, or the default profile if not specified.  May be
useful if you have multiple profiles configured each with their own IAM role configurations

Listing available MFA devices
-----------------------------

Use the `-m` option to list the ARNs of any MFA devices associated with your IAM account.
May be helpful for setting up your AWS config file.  If `profile` arg is specified, list
MFA devices available for the given profile, or the default profile if not specified. May
be useful if you have multiple profiles configured each with their own MFA device

Displaying session token expiration
-----------------------------------

Use the `-e` option to display the date and time which the session token will expire. If
`profile` arg is specified, display info for the given profile, otherwise use the 'default'
profile.  Specifying the profile name may be useful if you have multiple profiles configured
which you get session tokens for.

Injecting SessionToken credentials into the environment
-------------------------------------------------------

Use the `-s` option to output and eval()-able set of environment variables for the session
token credentials. If `profile` arg is specified, display the session token credentials for
the given profile, otherwise use the `default` profile.

Example:

| $ aws-runas -s
| export AWS_ACCESS_KEY_ID='xxxxxx'
| export AWS_SECRET_ACCESS_KEY='yyyyyy'
| export AWS_SESSION_TOKEN='zzzzz'

Or simply `eval $(aws-runas -s)` to add these env vars to the running environment.  Since
session tokens generally live for multiple hours, injecting these credentials into the
environment may be useful when using tools which can do AssumeRole on their own, and manage/refresh
the relativly short-lived AssumeRole credentials internally.

Injecting AssumeRole credentials into the environment
-----------------------------------------------------

Running the program with only a profile name will output an eval()-able set of environment
variables for the assumed role credentials which can be added to the current session.

Example:

| $ aws-runas admin-profile
| export AWS_ACCESS_KEY_ID='xxxxxx'
| export AWS_SECRET_ACCESS_KEY='yyyyyy'
| export AWS_SESSION_TOKEN='zzzzz'


Or simply `eval $(aws-runas admin-profile)` to add these env vars in the current session.
With the addition of caching session token credentials, and the ability to automatically
refresh the credentials, eval-ing this output for assumed role credentials is no longer
necessary for most cases, but will be left as a feature of this tool for the foreseeable future.

Running command using a profile
-------------------------------

Running the program specifying a profile name and command will execute the command using the
profile credentials, automatically performing any configured assumeRole operation, or MFA token
gathering.

Example (run the command `aws s3 ls` using the profile `admin-profile`):

| $ aws-runas admin-profile aws s3 ls
| ... <s3 bucket listing here> ...

Running command using the default profile
-----------------------------------------

Running the program using the default profile is no different than using a custom profile,
simply use `default` as the profile name.

Contributing
============

The usual github model for forking the repo and creating a pull request is the preferred way to
contribute to this tool.  Bug fixes, enhancements, doc updates, translations are always welcomed.

Building from source
--------------------

A `Makefile` has been included in the repository to handle the steps of creating the package and
uploading it to pypi.  If you don't have the `make` utility installed, the contents of the Makefile
should be instructive (and simple) enough to execute manually.

The following targets are available in the Makefile:

* `package` - the default target, calls the setup.py script to create the package to upload to pypi.
* `upload` - depends on the `package` target, and uploads the generated package archive to pypi.
* `install` - use `pip` to install the package locally
* `clean` - clean up the artifacts left by the `package` step.
* `distclean` - depends on the `clean` target, and additionally cleans up misc. files.
