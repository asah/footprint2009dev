# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi
import os
import urllib

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import urlfetch

import geocode
import search
import urls
import utils


TEMPLATE_DIR = 'templates/'
MAIN_PAGE_TEMPLATE = 'main_page.html'
SEARCH_RESULTS_TEMPLATE = 'search_results.html'
SEARCH_RESULTS_RSS_TEMPLATE = 'search_results.rss'
SNIPPETS_LIST_TEMPLATE = 'snippets_list.html'
SNIPPETS_LIST_RSS_TEMPLATE = 'snippets_list.rss'
WORK_WITH_OTHERS_TEMPLATE = 'work_with_others.html'

DEFAULT_NUM_RESULTS = 10


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

    start_index = utils.StringToInt(self.request.get('start')) or 1
    if start_index < 1:
      start_index = 1
    num_results_requested = DEFAULT_NUM_RESULTS
    is_first_page = (start_index <= num_results_requested)

    # TODO(paul): need to determine total # of results

    output = self.request.get('output')

    result_set = search.Search(query, location,
                               start_index, num_results_requested)

    # TODO(paul): Fix this.  It needs to use total num results.
    is_last_page = (len(result_set.results) < num_results_requested)

    def BuildSearchUrl(start_index):
      return ('%s?%s' %
          (urls.URL_SEARCH, urllib.urlencode({'q': query,
                                              'loc': location,
                                              'start': start_index })))

    prev_page_url = BuildSearchUrl(start_index - DEFAULT_NUM_RESULTS)
    next_page_url = BuildSearchUrl(start_index + DEFAULT_NUM_RESULTS)
  
    userInfo = utils.GetUserInfo()
    userId = ""
    userDisplayName = ""
    if userInfo:
      userId = userInfo['entry']['id']
      userDisplayName = userInfo['entry']['displayName']

    template_values = {
        'result_set': result_set,
        'keywords': query,
        'location': location,
        'currentPage' : 'SEARCH',
        'userId' : userId,
        'userDisplayName' : userDisplayName,
        'is_first_page': is_first_page,
        'is_last_page': is_last_page,
        'prev_page_url': prev_page_url,
        'next_page_url': next_page_url,
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
    userInfo = utils.GetUserInfo()
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
