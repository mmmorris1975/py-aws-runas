import os, time
import logging
import json, datetime
import boto3
import argparse
import multiprocessing
import botocore.session

from botocore.exceptions import ProfileNotFound

__VERSION__ = '0.1.2'

# cribbed from the awscli assumerole.py customization module
class JSONFileCache(object):

  CACHE_DIR = os.path.expanduser(os.path.join('~', '.aws', 'cli', 'cache'))

  def __init__(self, working_dir=CACHE_DIR):
    self._working_dir = working_dir

  def __contains__(self, cache_key):
    actual_key = self._convert_cache_key(cache_key)
    return os.path.isfile(actual_key)

  def __getitem__(self, cache_key):
    actual_key = self._convert_cache_key(cache_key)

    try:
      with open(actual_key) as f:
        return json.load(f)
    except (OSError, ValueError, IOError):
      raise KeyError(cache_key)

  def __setitem__(self, cache_key, value):
    full_key = self._convert_cache_key(cache_key)

    try:
      file_content = json.dumps(value, default=self._json_encoder)
    except (TypeError, ValueError):
      raise ValueError("Value cannot be cached, must be "
                       "JSON serializable: %s" % value)

    if not os.path.isdir(self._working_dir):
      os.makedirs(self._working_dir)

    with os.fdopen(os.open(full_key, os.O_WRONLY | os.O_CREAT, 0o600), 'w') as f:
      f.truncate()
      f.write(file_content)

  def _json_encoder(self, obj):
    if isinstance(obj, datetime.datetime):
      return obj.isoformat()
    else:
      return obj

  def _convert_cache_key(self, cache_key):
    full_path = os.path.join(self._working_dir, cache_key + '.json')
    return full_path

def parse_cmdline():
  p = argparse.ArgumentParser(description='Create an environment for interacting with the AWS API using an assumed role')
  p.add_argument('-l', '--list-roles', help='list role ARNs you are able to assume', action='store_true')
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

def inject_assume_role_provider_cache(session):
  # Add ability to use a json file based credential cache for assumed role creds
  # Inspired by the awscli assumerole customization
  try:
    cred_chain = session.get_component('credential_provider')
  except ProfileNotFound:
    logging.warning("Profile not found, will not use credential cache")
    return

  provider = cred_chain.get_provider('assume-role')
  provider.cache = JSONFileCache()

def main():
  args = parse_cmdline()

  if args.version:
    print("VERSION: %s" % __VERSION__)
    exit(0)

  logging.basicConfig(level=args.verbose)

  # AWS lib gets very chatty, turn it down a bit
  logging.getLogger('botocore').setLevel(logging.WARNING)
  logging.getLogger('boto3').setLevel(logging.WARNING)

  if args.list_roles:
    global iam
    iam = boto3.resource('iam')

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
    s = botocore.session.get_session()
    sess = boto3.Session(profile_name=args.profile, botocore_session=s) # Does assumeRole for us
    inject_assume_role_provider_cache(s)
    c = sess.get_credentials() # MFA auth happens here, if necessary

    os.environ['AWS_ACCESS_KEY_ID'] = c.access_key
    os.environ['AWS_SECRET_ACCESS_KEY'] = c.secret_key

    if c.token:
      os.environ['AWS_SESSION_TOKEN']  = c.token
      os.environ['AWS_SECURITY_TOKEN'] = c.token # Backwards compatibility

    if len(args.cmd) == 0:
      # profile name only, output the keys and tokens as env vars
      logging.debug("no command detected, outputting eval()-able role credentials")
      for i in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN'):
        print("export %s='%s'" % (i, os.getenv(i)))
    else:
      # role name and command to run
      logging.debug("detected command, will run command using assumed role")
      logging.debug("CMD: %s", args.cmd)
      os.execvp(args.cmd[0], args.cmd)
