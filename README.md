# AWS RUNAS
A command to provide a friendly way to do an AWS STS assumeRole operation so you can perform AWS API actions
using a particular set of permissions.  Includes integration with roles requiring MFA authentication!  Works
off of profile names configured in the AWS SDK configuration file.

Just like the awscli, this utility will cache the assumed role credentials.  If using MFA, when the credentials
expire you will be prompted to re-enter the MFA token value to refresh the credentials.  If MFA is not requred
for the assumed role, the credentials should refresh automatically.

See the following for more information on AWS SDK configuration files:
  - http://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html
  - https://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration
  - https://boto3.readthedocs.io/en/latest/guide/configuration.html#aws-config-file

## Requirements
  - Tested on python 2.7 and python 3
  - boto3 python library, version 1.3.1 or higher (`pip install -r requirements.txt` if necessary)

## Installation
Other than ensuring python and the boto3 library are available, this program is self-contained and stays inside
of the python standard library. It can be copied anywhere you need it.

## Usage
```
usage: aws-runas [-h] [-l] [-v] [profile] ...

Create an environment for interacting with the AWS API using an assumed role

positional arguments:
  profile           name of profile
  cmd               command to execute using configured profile

optional arguments:
  -h, --help        show this help message and exit
  -l, --list-roles  list role ARNs you are able to assume
  -v, --verbose     print verbose/debug messages
```

### Listing available roles
Use the `-l` option to see the list of role ARNs your IAM account is authorized to assume.
May be helpful for setting up your AWS config file.

### Generating credentials
Running the program with only a profile name will output an eval()-able set of
environment variable which can be added to the current session.

Example:
```
$ aws-runas admin-profile
export AWS_ACCESS_KEY_ID='xxxxxx'
export AWS_SECRET_ACCESS_KEY='yyyyyy'
export AWS_SESSION_TOKEN='zzzzz'
```

Or simply `eval $(aws-runas admin-profile)` to add these env vars in the current session

### Running command using a profile
Running the program specifying a profile name and command will execute the command using the
profile credentials, automatically performing any configured assumeRole operation, or MFA token
gathering.

Example (run the command `aws s3 ls` using the profile `admin-profile`):
```
$ aws-runas admin-profile aws s3 ls
... <s3 bucket listing here> ...
```

### Running command using the default profile
Running the program using the default profile is no different than using a custom profile,
simply use `default` as the profile name.
