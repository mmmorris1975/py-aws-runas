import os, time
import json, datetime
import boto3

class SessionTokenProvider:
  CACHE_DIR = os.path.expanduser(os.path.join('~', '.aws'))
  DT_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

  def __init__(self, profile, mfa_serial):
    self.profile = profile
    self.mfa_serial = mfa_serial
    self.cache_file = os.path.join(self.CACHE_DIR, ".aws_session_token_" + profile)

  def _update_cache(self, data):
    f = open(self.cache_file, 'w')

    try:
      json.dump(data, f, default=self._fixup_aws_res)
    finally:
      if f:
        f.close()

  def _fixup_aws_res(self, obj):
    if isinstance(obj, datetime.datetime):
      return obj.strftime(self.DT_FORMAT)
    else:
      return obj

  def _fetch_cache_token(self):
    expired = True
    f = open(self.cache_file, 'r')

    try:
      tok = json.load(f)
      exp_time = datetime.datetime.strptime(tok['Credentials']['Expiration'], self.DT_FORMAT)
      expired = time.mktime(exp_time.utctimetuple()) < time.mktime(datetime.datetime.utcnow().utctimetuple())
    finally:
      if f:
        f.close()

    return (tok, expired)

  def _fetch_fresh_token(self):
    mfa_token = input("Enter MFA Code: ")

    ses = boto3.Session(profile_name=self.profile)
    sts = ses.client('sts')
    res = sts.get_session_token(SerialNumber=self.mfa_serial, TokenCode=mfa_token)
    self._update_cache(res)

    return res

  def get_credentials(self):
    expired = True
    if os.path.isfile(self.cache_file):
      (res, expired) = self._fetch_cache_token()

    if expired:
      res = self._fetch_fresh_token()

    return res
