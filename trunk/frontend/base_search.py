# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi
import os
import urllib

from google.appengine.api import users
from google.appengine.api.urlfetch import fetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from xml.dom import minidom

#import gdata.service
#import gdata.urlfetch
## Use urlfetch instead of httplib
#gdata.service.http_request_handler = gdata.urlfetch

import geocode
import base_search
import searchresult
import utils

# Base URL for snipets search on Base.
#   Docs: http://code.google.com/apis/base/docs/2.0/attrs-queries.html
BASE_SNIPPETS_URL = 'http://www.google.com/base/feeds/snippets'

def Search(query, location):
  location_param = '[location: @"%s" + 5mi]' % location
#  link_param = '[link: idealist]'
  link_param = ''
  base_query = 'volunteer %s %s' % (location_param, link_param)

  url_params = urllib.urlencode({'max-results': '10',
                                 'bq': base_query })
  query_url = '%s?%s' % (BASE_SNIPPETS_URL, url_params)

  fetch_result = fetch(query_url)
  if fetch_result.status_code != 200:
    return None

  dom = minidom.parseString(fetch_result.content)

  results = []
  for entry in dom.getElementsByTagName('entry'):
    url = entry.getElementsByTagName('link')[0].getAttribute('href')
    snippet = utils.GetXmlDomText(entry.getElementsByTagName('content')[0])
    title = utils.GetXmlDomText(entry.getElementsByTagName('title')[0])
    results.append(searchresult.SearchResult(url, title, snippet))

  return searchresult.SearchResultSet(urllib.unquote(query_url),
                                      query_url,
                                      results)