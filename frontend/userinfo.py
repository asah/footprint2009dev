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
from facebook import Facebook

import models

class Error(Exception): pass
class NotLoggedInError(Error): pass
class ThirdPartyError(Error): pass

USERINFO_CACHE_TIME = 120  # seconds

# Keys specific to Footprint
FRIENDCONNECT_KEY = '02962301966004179520'
FACEBOOK_KEY = 'df68a40a4a90d4495ed03f920f16c333'
FACEBOOK_SECRET = 'b063a345dd9f0f9c6d3baad86dd5ae8a'

def get_cookie(cookie_name):
  if 'HTTP_COOKIE' in os.environ:
    cookies = os.environ['HTTP_COOKIE']
    cookies = cookies.split('; ')
    for cookie in cookies:
      cookie = cookie.split('=')
      if cookie[0] == cookie_name:
        return cookie[1]

def get_user(request):
  for cls in (TestUser, FriendConnectUser, FacebookUser):
    cookie = cls.get_cookie()
    if cookie:
      key = 'cookie:' + cookie
      user = memcache.get(key)
      if not user:
        try:
          user = cls(request)
          memcache.set(key, user, time = USERINFO_CACHE_TIME)
        except logging.exception:
          # This hides all errors from the Facebook client library
          # TODO(doll): Hand back an error message to the user
          return None
      return user


class User(object):
  """The User info for a user related to a currently logged in session.."""

  def __init__(self, account_type, user_id, display_name, thumbnail_url):
    self.account_type = account_type
    self.user_id = user_id
    self.display_name = display_name
    self.thumbnail_url = thumbnail_url
    self.user_info = None
    self.friends = None
    self.total_friends = None

  @staticmethod
  def get_current_user(self):
    raise NotImplementedError

  def get_user_info(self):
    if not self.user_info:
      self.user_info = models.UserInfo.get_or_insert_user(self.account_type,
                                                          self.user_id)
    return self.user_info

  def load_friends(self):
    key = 'friends:' + self.account_type + ":" + self.user_id
    friends = memcache.get(key)
    if not friends:
      friends = self.get_friends_by_url();
      memcache.set(key, friends, time = USERINFO_CACHE_TIME)
    return friends

  def get_friends_by_url(self):
    raise NotImplementedError

  @classmethod
  def is_logged_in(cls):
    cookie = cls.get_cookie()
    return not not cookie


class FriendConnectUser(User):
  """A friendconnect user."""

  BASE_URL = 'http://www.google.com/friendconnect/api/people/'

  USER_INFO_URL = BASE_URL + '@viewer/@self?fcauth=%s'
  FRIEND_URL = BASE_URL + '@viewer/@friends?fcauth=%s'

  def __init__(self, request):
    """Creates a friendconnect user from the current env, or raises error."""
    self.fc_user_info = self.get_fc_user_info()
    super(FriendConnectUser, self).__init__(
        models.UserInfo.FRIENDCONNECT,
        self.fc_user_info['entry']['id'],
        self.fc_user_info['entry']['displayName'],
        self.fc_user_info['entry']['thumbnailUrl'])

  def get_friends_by_url(self):
    friend_cookie = self.get_cookie()
    if not friend_cookie:
      raise NotLoggedInError()

    self.friends = []

    url = self.FRIEND_URL % friend_cookie
    result = urlfetch.fetch(url)
    if result.status_code == 200:
      friend_info = simplejson.load(StringIO(result.content))
      self.total_friends = friend_info['totalResults']

      for friend_object in friend_info['entry']:
        friend = User(
            models.UserInfo.FRIENDCONNECT,
            friend_object['id'],
            friend_object['displayName'],
            friend_object['thumbnailUrl'])
        self.friends.append(friend)

    return self.friends

  @classmethod
  def get_cookie(cls):
    return get_cookie('fcauth' + FRIENDCONNECT_KEY)

  @classmethod
  def get_fc_user_info(cls):
    friend_cookie = cls.get_cookie()
    if not friend_cookie:
      raise NotLoggedInError()
      return

    url = cls.USER_INFO_URL % friend_cookie
    result = urlfetch.fetch(url)

    if result.status_code == 200:
      user_info = simplejson.load(StringIO(result.content))
      return user_info
    else:
      raise ThirdPartyError()


class FacebookUser(User):
  def __init__(self, request):
    self.facebook = Facebook(FACEBOOK_KEY, FACEBOOK_SECRET)
    if not self.facebook.check_connect_session(request):
      raise NotLoggedInError()

    info = self.facebook.users.getInfo([self.facebook.uid],
        ['name', 'pic_square_with_logo'])[0]

    super(FacebookUser, self).__init__(
        models.UserInfo.FACEBOOK,
        self.facebook.uid,
        info['name'],
        info['pic_square_with_logo'])

  def get_friends_by_url(self):
    if not self.facebook:
      raise NotLoggedInError()

    self.friends = []

    friend_ids = self.facebook.friends.getAppUsers()
    self.total_friends = len(friend_ids)

    friend_objects = self.facebook.users.getInfo([friend_ids[0:20]],
        ['name', 'pic_square_with_logo'])
    for friend_object in friend_objects:
      friend = User(
          models.UserInfo.FACEBOOK,
          `friend_object['uid']`,
          friend_object['name'],
          friend_object['pic_square_with_logo'])
      self.friends.append(friend)

    return self.friends

  @classmethod
  def get_cookie(cls):
    return get_cookie(FACEBOOK_KEY)


class TestUser(User):
  """A really simple user example."""

  def __init__(self, request):
    """Creates a user, or raises error."""
    cookie = self.get_cookie()
    if not (cookie):
      raise NotLoggedInError()
    super(TestUser, self).__init__(
        models.UserInfo.TEST,
        cookie,
        cookie,
        'images/Event-Selected-Star.png')

  @classmethod
  def get_cookie(cls):
    return get_cookie('footprinttest')
