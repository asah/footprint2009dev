# Copyright 2009 Google Inc.  All Rights Reserved.
#

import os

from google.appengine.api import urlfetch

from xml.dom import minidom
from django.utils import simplejson
from StringIO import StringIO

def GetXmlDomText(dom):
  text = ''
  for child in dom.childNodes:
    if child.nodeType == minidom.Node.TEXT_NODE:
      text += child.data
  return text


def GetUserInfo():
  friendCookie = GetFriendCookie()
  if friendCookie:
    url = 'http://www.google.com/friendconnect/api/people/@viewer/@self?fcauth=' + friendCookie;
    result = urlfetch.fetch(url)
    if result.status_code == 200:
      return simplejson.load(StringIO(result.content))


def GetFriendCookie():
  if 'HTTP_COOKIE' in os.environ:
    cookies = os.environ['HTTP_COOKIE']
    cookies = cookies.split('; ')
    for cookie in cookies:
      cookie = cookie.split('=')
      if cookie[0] == '_ps_auth02962301966004179520':
        return cookie[1]


def StringToInt(string):
  try:
    return int(string)
  except ValueError:
    return None