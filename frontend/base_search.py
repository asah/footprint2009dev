# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi
import os
import urllib
import logging

from google.appengine.api import users
from google.appengine.api.urlfetch import fetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from xml.dom import minidom

## Use urlfetch instead of httplib
#gdata.service.http_request_handler = gdata.urlfetch

import geocode
import base_search
import searchresult
import utils

def BaseArg(x):
  return "base_" + x

# note: many of the XSS and injection-attack defenses are unnecessary
# given that the callers are also protecting us, but I figure better
# safe than sorry, and defense-in-depth.
def Search(args):
  base_query = ""

  # TODO: injection attack on q
  if "q" in args:
    base_query += ' '+args["q"]

  # TODO: injection attacks in vol_loc
  if args["vol_loc"] != "":
    args["vol_dist"] = int(str(args["vol_dist"]))
    base_query += ' [location: @"%s" + %dmi]' % (args["vol_loc"],args["vol_dist"])

  # Base URL for snipets search on Base.
  #   Docs: http://code.google.com/apis/base/docs/2.0/attrs-queries.html
  # TODO: injection attack on backend
  if "backend" not in args:
    args["backends"] = "http://www.google.com/base/feeds/snippets"

  if BaseArg("customer") not in args:
    args[BaseArg("customer")] = 5663714;
  base_query += ' [customer id: '+str(int(args[BaseArg("customer")]))+']'

  if "num" not in args:
    args["num"] = 10
  if "start" not in args:
    args["start"] = 1

  #for k in args: logging.info("arg["+str(k)+"]="+str(args[k]))
  url_params = urllib.urlencode({'max-results': args["num"],
				 'start-index': args["start"],
                                 'bq': base_query,
                                 })
  query_url = '%s?%s' % (args["backends"], url_params)

  result_set = searchresult.SearchResultSet(urllib.unquote(query_url),
                                            query_url,
                                            [])
  result_set.args = args
  fetch_result = fetch(query_url)
  if fetch_result.status_code != 200:
    return result_set

  dom = minidom.parseString(fetch_result.content)
  
  for i,entry in enumerate(dom.getElementsByTagName('entry')):
    url = entry.getElementsByTagName('link')[0].getAttribute('href')
    snippet = utils.GetXmlDomText(entry.getElementsByTagName('content')[0])
    title = utils.GetXmlDomText(entry.getElementsByTagName('title')[0])
    location_element = entry.getElementsByTagName('g:location_string')
    if location_element:
      location = utils.GetXmlDomText(location_element[0])
    else:
      location = None
    logging.info("title="+title+"  location="+str(location)+"  url="+url)
    res = searchresult.SearchResult(url, title, snippet, location)
    res.idx = i+1
    result_set.results.append(res)

  return result_set
