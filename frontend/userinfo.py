#!/usr/bin/python2.5
# Copyright 2009 Google Inc.  All Rights Reserved.
#

"""User Info module (userinfo).

This file contains the base class for the userinfo classes.
It also contains (at least for now) subclasses for different login types."""

__author__ = 'matthew.blain@google.com'

import logging
import os

from django.utils import simplejson
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from StringIO import StringIO


import models

class Error(Exception): pass
class NotLoggedInError(Error): pass

USERINFO_CACHE_TIME = 120  # seconds

def get_cookie(cookie_name):
  if 'HTTP_COOKIE' in os.environ:
    cookies = os.environ['HTTP_COOKIE']
    cookies = cookies.split('; ')
    for cookie in cookies:
      cookie = cookie.split('=')
      if cookie[0] == cookie_name:
        return cookie[1]

def get_user():
  for cls in (TestUser, FriendConnectUser):
    if cls.get_cookie():
      return cls()

class User(object):
  """The User info for a user related to a currently logged in session.."""

  def __init__(self, account_type, user_id):
    self.account_type = account_type
    self.user_id = user_id
    self.user_info = None

  @staticmethod
  def get_current_user(self):
    raise NotImplementedError

  def get_user_info(self):
    if not self.user_info:
      self.user_info = models.UserInfo.get_or_insert_user(self.account_type,
                                                          self.user_id)
    return self.user_info

  def get_display_name(self):
    raise NotImplementedError

  def get_thumbnail_url(self):
    raise NotImplementedError

  @classmethod
  def is_logged_in(cls):
    cookie = cls.get_cookie()
    return not not cookie


class FriendConnectUser(User):
  """A friendconnect user."""

  USER_INFO_URL = \
      'http://www.google.com/friendconnect/api/people/@viewer/@self?fcauth=%s'

  def __init__(self):
    """Creates a friendconnect user from the current env, or raises error."""
    self.fc_user_info = self.get_fc_user_info()
    if not (self.fc_user_info):
      raise NotLoggedInError()
    super(FriendConnectUser, self).__init__(models.UserInfo.FRIENDCONNECT,
                                            self.get_user_id())

  def get_user_id(self):
    # warning: may be called during __init__.
    return self.fc_user_info['entry']['id']

  def get_display_name(self):
    return self.fc_user_info['entry']['displayName']

  def get_thumbnail_url(self):
    return self.fc_user_info['entry']['thumbnailUrl']

  @classmethod
  def get_cookie(cls):
    return get_cookie('_ps_auth02962301966004179520')

  @classmethod
  def get_fc_user_info(cls):
    friend_cookie = cls.get_cookie()
    if not friend_cookie:
      return None

    key = "friendconnect:" + friend_cookie
    user_info = memcache.get(key)
    if not user_info:
      url = cls.USER_INFO_URL % friend_cookie
      logging.warning(url)
      result = urlfetch.fetch(url)
      if result.status_code == 200:
        user_info = simplejson.load(StringIO(result.content))
        memcache.set(key, user_info, time = USERINFO_CACHE_TIME)
    return user_info

class TestUser(User):
  """A really simple user example."""

  def __init__(self):
    """Creates a , or raises error."""
    user_id = self.get_cookie()
    if not (user_id):
      raise NotLoggedInError()
    super(TestUser, self).__init__(models.UserInfo.TEST, user_id)

  def get_user_id(self):
    # warning: may be called during __init__.
    return self.get_cookie()

  def get_display_name(self):
    return self.get_cookie()

  def get_thumbnail_url(self):
    return '/images/yahoo.gif'

  @classmethod
  def get_cookie(cls):
    return get_cookie('footprinttest')

