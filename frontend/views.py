# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi
import os

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import geocode
import search

TEMPLATE_DIR = 'html/'
MAIN_PAGE_TEMPLATE = 'main_page.html'
SEARCH_RESULTS_TEMPLATE = 'search_results.html'
SNIPPETS_LIST_TEMPLATE = 'snippets_list.html'

#class Greeting(db.Model):
#  author = db.UserProperty()
#  content = db.StringProperty(multiline=True)
#  date = db.DateTimeProperty(auto_now_add=True)


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

    result_set = search.Search(query, location)

    point = geocode.Geocode(query)

    template_values = {
        'query_url_encoded': result_set.query_url_encoded,
        'query_url_unencoded': result_set.query_url_unencoded,
        'results': result_set.results,
        'keywords': query,
        'location': location,
      }

    self.response.out.write(RenderTemplate(SEARCH_RESULTS_TEMPLATE,
                                           template_values))
