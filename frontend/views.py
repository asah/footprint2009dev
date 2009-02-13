# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import urlfetch

import geocode
import search

from django.utils import simplejson
from StringIO import StringIO

TEMPLATE_DIR = 'templates/'
MAIN_PAGE_TEMPLATE = 'main_page.html'
SEARCH_RESULTS_TEMPLATE = 'search_results.html'
SEARCH_RESULTS_RSS_TEMPLATE = 'search_results.rss'
SNIPPETS_LIST_TEMPLATE = 'snippets_list.html'
SNIPPETS_LIST_RSS_TEMPLATE = 'snippets_list.rss'
WORK_WITH_OTHERS_TEMPLATE = 'work_with_others.html'

def RenderTemplate(template_filename, template_values):
  path = os.path.join(os.path.dirname(__file__),
                      TEMPLATE_DIR + template_filename)
  return template.render(path, template_values)


class MainPageView(webapp.RequestHandler):
  def get(self):
    template_values = []
    self.response.out.write(RenderTemplate(MAIN_PAGE_TEMPLATE,
                                           template_values))


class SearchView(webapp.RequestHandler):
  def get(self):
    query = self.request.get('q')
    location = self.request.get('loc')
    output = self.request.get('output')

    result_set = search.Search(query, location)

   ### point = geocode.Geocode(location)

    template_values = {
        'query_url_encoded': result_set.query_url_encoded,
        'query_url_unencoded': result_set.query_url_unencoded,
        'results': result_set.results,
        'keywords': query,
        'location': location,
        'currentPage' : 'SEARCH'
      }

    if output == "rss":
      self.response.out.write(RenderTemplate(SEARCH_RESULTS_RSS_TEMPLATE,
                                             template_values))
    else:
      # html output
      self.response.out.write(RenderTemplate(SEARCH_RESULTS_TEMPLATE,
                                             template_values))

class FriendsView(webapp.RequestHandler):
  def get(self):
    userInfo = self.getUserInfo()
    userId = ""
    if userInfo:
      #we are logged in
      userId = userInfo['entry']['id']
      displayName = userInfo['entry']['displayName']
      thumbnailUrl = userInfo['entry']['thumbnailUrl']

    template_values = {
        'currentPage' : 'FRIENDS',
        'userId': userId
      }

    self.response.out.write(RenderTemplate(WORK_WITH_OTHERS_TEMPLATE,
                                           template_values))

  def getUserInfo(self):
    friendCookie = self.getFriendCookie()
    if friendCookie:
      url = 'http://www.google.com/friendconnect/api/people/@viewer/@self?fcauth=' + friendCookie;
      result = urlfetch.fetch(url)
      if result.status_code == 200:
        return simplejson.load(StringIO(result.content))

  def getFriendCookie(self):
    if 'HTTP_COOKIE' in os.environ:
      cookies = os.environ['HTTP_COOKIE']
      cookies = cookies.split('; ')
      for cookie in cookies:
        cookie = cookie.split('=')
        if cookie[0] == '_ps_auth02962301966004179520':
          return cookie[1]
