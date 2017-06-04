# AWS RUNAS
A command to provide a friendly way to do an AWS STS assumeRole operation so you can perform AWS API actions
using a particular set of permissions.

## Requirements
  - Tested on python 2.7 and python 3
  - boto3 python library (`pip install -r requirements.txt` if necessary)

## Usage
```
usage: aws-runas [-h] [-l] [-v] [role] ...

Create an environment for interacting with the AWS API using an assumed role

positional arguments:
  role              name of role to assume
  cmd               command to execute using assumed role

optional arguments:
  -h, --help        show this help message and exit
  -l, --list-roles  list roles you are able to assume, updates cached roles
  -v, --verbose     print verbose/debug messages
```

### Listing available roles
Use the `-l` option to see the list of roles your IAM account is authorized to
assume.  It will also generate, or update, a cache of this information to avoid
the AWS API overhead everytime the command is run.

### Generating credentials
Running the program simply with a role name will output an eval()-able set of
environment variable which can be added to the current session.

Example:
```
$ aws-runas admin-role
export AWS_ACCESS_KEY_ID='xxxxxx'
export AWS_SECRET_ACCESS_KEY='yyyyyy'
export AWS_SESSION_TOKEN='zzzzz'
```

Or simply `eval $(aws-runas admin-role)` to add these env vars in the current session

### Running command using assumed role
Running the program specifying a role name and command will assume the given role (provided
you have authority to do so), and then execute the command under the context of the assumed
role

Example (run the command `aws s3 ls` using the assume role `admin-role`):
```
$ aws-runas admin-role aws s3 ls
... <s3 bucket listing here> ...
```
