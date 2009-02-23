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


def Search(query, location, start_index, num_results):
  location_param = '[location: @"%s" + 5mi]' % location
#  link_param = '[link: idealist]'
  link_param = ''
  base_query = 'volunteer %s %s %s' % (query, location_param, link_param)

  if not start_index:
    start_index = 1

  url_params = urllib.urlencode({'max-results': num_results,
                                 'bq': base_query,
                                 'start-index': start_index })
  query_url = '%s?%s' % (BASE_SNIPPETS_URL, url_params)

  result_set = searchresult.SearchResultSet(urllib.unquote(query_url),
                                            query_url,
                                            [])
  fetch_result = fetch(query_url)
  if fetch_result.status_code != 200:
    return result_set

  dom = minidom.parseString(fetch_result.content)

  for entry in dom.getElementsByTagName('entry'):
    url = entry.getElementsByTagName('link')[0].getAttribute('href')
    snippet = utils.GetXmlDomText(entry.getElementsByTagName('content')[0])
    title = utils.GetXmlDomText(entry.getElementsByTagName('title')[0])
    location_element = entry.getElementsByTagName('g:location')
    if location_element:
      location = utils.GetXmlDomText(location_element[0])
    else:
      location = None
    result_set.results.append(searchresult.SearchResult(url, title, snippet,
                                                        location))

  return result_set
