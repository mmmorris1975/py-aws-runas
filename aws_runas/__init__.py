import os, time
import logging
import boto3
import argparse
import multiprocessing

from .session_token_provider import SessionTokenProvider

try:
  # Python 3
  from configparser import ConfigParser
except ImportError:
  # Python 2
  from ConfigParser import ConfigParser

__VERSION__ = '0.2.0-beta2'

def parse_cmdline():
  p = argparse.ArgumentParser(description='Create an environment for interacting with the AWS API using an assumed role')
  p.add_argument('-l', '--list-roles', help='list role ARNs you are able to assume', action='store_true')
  p.add_argument('-m', '--list-mfa', help='list the ARN of the MFA device associated with the account', action='store_true')
  p.add_argument('-v', '--verbose', help='print verbose/debug messages', action='store_const', const=logging.DEBUG, default=logging.INFO)
  p.add_argument('-V', '--version', help='print program version and exit', action='store_true')
  p.add_argument('profile', nargs='?', help='name of profile')
  p.add_argument('cmd', nargs=argparse.REMAINDER, help='command to execute using configured profile')

  return p.parse_args()

def get_user_roles(user_name, inline=True):
  r = []
  u = iam.User(user_name)

  if inline:
    r = get_inline_roles(u)
  else:
    r = get_attached_roles(u)

  return r

def get_group_roles(group_name, inline=True):
  r = []
  g = iam.Group(group_name)

  if inline:
    r = get_inline_roles(g)
  else:
    r = get_attached_roles(g)

  return r

def get_inline_roles(res):
  roles = []

  for p in res.policies.all():
    d = p.policy_document()
    roles += parse_policy_doc(d)

  return roles

def get_attached_roles(res):
  roles = []

  for p in res.attached_policies.all():
    d = iam.PolicyVersion(p.arn, p.default_version_id).document
    roles += parse_policy_doc(d)

  return roles

def parse_policy_doc(doc):
  stmts = []
  role_arns = []

  # AWS fail ... the 'Statement' part of the document could be a List or a Dict
  # and the embedded 'Resource' could be a String or List.  Happy parsing!
  if 'Action' in doc['Statement']:
    # Assume 'Statement' is a dict
    stmts.append(doc['Statement'])
  else:
    # Assume 'Statement' is a list
    stmts = doc['Statement']

  for s in stmts:
    if s['Action'] == 'sts:AssumeRole' and s['Effect'] == 'Allow':
      r = s['Resource']
      if len(r[0]) == 1:
        # Assume String (r[0] is a char)
        role_arns.append(r)
      else:
        # Assume List (r[0] is full ARN string)
        role_arns += r

  logging.debug("roles parsed from policy document: %s", role_arns)
  return role_arns

def parse_aws_config(profile):
  cfg_file = os.getenv('AWS_CONFIG_FILE', os.path.expanduser(os.path.join('~', '.aws', 'config')))
  cfg_profile = "profile " + profile
  logging.debug("CONFIG FILE: %s", cfg_file)

  p = ConfigParser()
  p.read(cfg_file)

  src_profile = p.get(cfg_profile, 'source_profile')
  role_arn = p.get(cfg_profile, 'role_arn')
  mfa_serial = p.get(src_profile, 'mfa_serial')

  return (src_profile, role_arn, mfa_serial)

def main():
  args = parse_cmdline()

  if args.version:
    print("VERSION: %s" % __VERSION__)
    exit(0)

  logging.basicConfig(level=args.verbose)

  # AWS lib gets very chatty, turn it down a bit
  logging.getLogger('botocore').setLevel(logging.WARNING)
  logging.getLogger('boto3').setLevel(logging.WARNING)

  ses = boto3.Session(profile_name=args.profile)

  if args.list_mfa:
    c = ses.client('iam')
    r = c.list_mfa_devices()

    for d in r.get('MFADevices'):
      print(d.get('SerialNumber'))
  elif args.list_roles:
    global iam
    iam = ses.resource('iam')

    roles = []
    tasks = []
    pool = multiprocessing.Pool()
    user = iam.CurrentUser()
    iam_user = iam.User(user.user_name)

    tasks.append(pool.apply_async(get_user_roles, (iam_user.user_name, True)))
    tasks.append(pool.apply_async(get_user_roles, (iam_user.user_name, False)))

    for g in iam_user.groups.all():
      tasks.append(pool.apply_async(get_group_roles, (g.group_name, True)))
      tasks.append(pool.apply_async(get_group_roles, (g.group_name, False)))

    pool.close()

    for t in tasks:
      for r in t.get():
        if r not in roles:
          roles.append(r)

    pool.join()

    print("Available role ARNs for %s (%s)" % (user.user_name, user.arn))
    roles.sort()
    for r in roles:
      print("  %s" % (r,))
  else:
    (src_profile, role_arn, mfa_serial) = parse_aws_config(args.profile)
    p = SessionTokenProvider(profile=src_profile, mfa_serial=mfa_serial)
    res = p.get_credentials()

    creds = res['Credentials']
    tok_ses = boto3.Session( aws_access_key_id=creds['AccessKeyId'], aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken'])
    tok_sts = tok_ses.client('sts')

    # This becomes much less important to cache, unless we want to really focus on compatibility with awscli AssumeRole cred cache
    ses_name = "AWS-RUNAS-%s-%d" % (os.getenv("USER", "__"), time.time())
    res = tok_sts.assume_role(RoleArn=role_arn, RoleSessionName=ses_name)
    ar_creds = res['Credentials']

    os.environ['AWS_ACCESS_KEY_ID'] = ar_creds['AccessKeyId']
    os.environ['AWS_SECRET_ACCESS_KEY'] = ar_creds['SecretAccessKey']

    if ar_creds['SessionToken']:
      os.environ['AWS_SESSION_TOKEN']  = ar_creds['SessionToken']
      os.environ['AWS_SECURITY_TOKEN'] = ar_creds['SessionToken'] # Backwards compatibility

    if len(args.cmd) == 0:
      # profile name only, output the keys and tokens as env vars
      logging.debug("no command detected, outputting eval()-able role credentials")
      for i in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN'):
        if os.name == 'nt':
          print("set %s='%s'" % (i, os.getenv(i)))
        else:
          print("export %s='%s'" % (i, os.getenv(i)))
    else:
      # role name and command to run
      logging.debug("detected command, will run command using assumed role")
      logging.debug("CMD: %s", args.cmd)
      os.execvp(args.cmd[0], args.cmd)
