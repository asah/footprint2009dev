# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi
import datetime
import time
import os
import re
import urllib
import logging
import md5

# TODO: remove me

from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from xml.dom import minidom

## Use urlfetch instead of httplib
#gdata.service.http_request_handler = gdata.urlfetch

import geocode
import models
import searchresult
import utils

RESULT_CACHE_TIME = 900 # seconds
RESULT_CACHE_KEY = 'searchresult:'

# Date format pattern used in date ranges.
DATE_FORMAT_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

def make_base_arg(x):
  return "base_" + x

def make_base_orderby_arg(args):
  # TODO: implement other scenarios for orderby
  return "relevancy"
  if args["sort"] == "r":
    # newest
    return "modification_time"
  else:
    # "relevancy" is the Base default
    return "relevancy"

# note: many of the XSS and injection-attack defenses are unnecessary
# given that the callers are also protecting us, but I figure better
# safe than sorry, and defense-in-depth.
def search(args):
  logging.info(args);
  base_query = ""

  # TODO: injection attack on q
  if "q" in args:
    base_query += ' ' + args["q"]

  # TODO: injection attack on vol_startdate
  if "vol_startdate" not in args:
    # note: default vol_startdate is "tomorrow"
    # in base, event_date_range YYYY-MM-DDThh:mm:ss/YYYY-MM-DDThh:mm:ss
    # appending "Z" to the datetime string would mean UTC
    args["vol_startdate"] = (datetime.date.today() 
                    + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

  if "vol_stopdate" not in args:
    tt = time.strptime(args["vol_startdate"], "%Y-%m-%d")
    args["vol_stopdate"] = (datetime.date(tt.tm_year, tt.tm_mon, tt.tm_mday) 
                    + datetime.timedelta(days=1000))

  base_query += ' [event_date_range: %s..%s]' % (args["vol_startdate"], 
  args["vol_stopdate"])

  # TODO: injection attack on sort
  if "sort" not in args:
    args["sort"] = "r"

  # TODO: injection attacks in vol_loc
  if args["vol_loc"] != "":
    args["vol_dist"] = int(str(args["vol_dist"]))
    # TODO: looks like the default is 25 mi, check for value as a min here?
    base_query += ' [location: @"%s" + %dmi]' % (args["vol_loc"], 
    args["vol_dist"])

  # Base URL for snippets search on Base.
  #   Docs: http://code.google.com/apis/base/docs/2.0/attrs-queries.html
  # TODO: injection attack on backend
  if "backend" not in args:
    args["backends"] = "http://www.google.com/base/feeds/snippets"

  if make_base_arg("customer") not in args:
    args[make_base_arg("customer")] = 5663714;
  base_query += (' [customer id: '
           + str(int(args[make_base_arg("customer")])) + ']')

  base_query += ' [detailurl][event_date_range]'

  if "num" not in args:
    args["num"] = 10

  if "start" not in args:
    args["start"] = 1

  if "base_num" not in args:
    args["base_num"] = 200

  #for k in args: logging.info("arg["+str(k)+"]="+str(args[k]))
  #url_params = urllib.urlencode({'max-results': args["num"],
  url_params = urllib.urlencode({'max-results': args["base_num"],
                                 'start-index': args["start"],
                                 'bq': base_query,
                                 'content': 'geocodes,attributes,meta',
                                 'orderby': make_base_orderby_arg(args),
                                 })
  query_url = '%s?%s' % (args["backends"], url_params)

  return query(query_url, args, False)

def hash_md5(s):
  it = md5.new()
  it.update(s)
  return it.digest()

def query(query_url, args, cache):
  result_set = searchresult.SearchResultSet(urllib.unquote(query_url),
                                            query_url,
                                            [])
  result_set.query_url = query_url
  result_set.args = args

  # TODO: consider moving this to search.py, i.e. not Base specific.
  # TODO: query param (& add to spec) for defeating the cache (incl FastNet)
  # I (mblain) suggest using "zx", which is used at Google for most services.
  # note: key cannot exceed 250 bytes
  memcache_key = hash_md5('query:' + query_url)
  result_content = memcache.get(memcache_key)
  if not result_content:
    fetch_result = urlfetch.fetch(query_url)
    if fetch_result.status_code != 200:
      return result_set
    result_content = fetch_result.content
    if cache:
      memcache.set(memcache_key, result_content, time=RESULT_CACHE_TIME)

  dom = minidom.parseString(result_content)

  elems = dom.getElementsByTagName('entry')
  for i,entry in enumerate(elems):
    # Note: using entry.getElementsByTagName('link')[0] isn't very stable;
    # consider iterating through them for the one where rel='alternate' or
    # whatever the right thing is.
    #urltag = entry.getElementsByTagName('link')[0].getAttribute('href')
    url = utils.GetXmlElementTextOrEmpty(entry, 'g:detailurl')
    # ID is the 'stable id' of the item generated by base.
    # Note that this is not the base url expressed as the Atom id element.
    id = utils.GetXmlElementTextOrEmpty(entry, 'g:id')
    # Base URL is the url of the item in base, expressed with the Atom id tag.
    base_url = utils.GetXmlElementTextOrEmpty(entry, 'id')
    snippet = utils.GetXmlElementTextOrEmpty(entry, 'content')
    title = utils.GetXmlElementTextOrEmpty(entry, 'title')
    location = utils.GetXmlElementTextOrEmpty(entry, 'g:location_string')
    #logging.info("title="+title+"  location="+str(location)+"  url="+url)
    #logging.info("title="+title+"  location="+str(location))
    res = searchresult.SearchResult(url, title, snippet, 
                                    location, id, base_url)
    # TODO: escape?
    res.provider = utils.GetXmlElementTextOrEmpty(entry, 'g:feed_providername')
    res.orig_idx = i+1
    res.latlong = ""
    #logging.info(re.sub(r'><', r'>\n<',entry.toxml()))
    latstr = utils.GetXmlElementTextOrEmpty(entry, 'g:latitude')
    logging.info(latstr)
    longstr = utils.GetXmlElementTextOrEmpty(entry, 'g:longitude')
    if latstr and longstr and latstr != "" and longstr != "":
      res.latlong = latstr + "," + longstr

    # TODO: remove-- working around a DB bug where all latlongs are the same
    if "geocode_responses" in args:
      res.latlong = geocode.geocode(location, 
            args["geocode_responses"]!="nocache" )

    # res.event_date_range follows one of these two formats:
    #     <start_date>T<start_time> <end_date>T<end_time>
    #     <date>T<time>
    res.event_date_range = utils.GetXmlElementTextOrEmpty(entry, 
            'g:event_date_range')
    m = DATE_FORMAT_PATTERN.findall(res.event_date_range)
    if not m:
      # TODO(oansaldi): should we accept an event with an invalid date range?
      logging.info('invalid date range: %s for %s' % (res.event_date_range, url))
    else:
      # first match is start date/time
      res.startdate = datetime.datetime.strptime(m[0], '%Y-%m-%dT%H:%M:%S')
      # last match is either end date/time or start/date time
      res.enddate = datetime.datetime.strptime(m[-1], '%Y-%m-%dT%H:%M:%S')

    result_set.results.append(res)
    if cache and res.id:
      key = RESULT_CACHE_KEY + res.id
      memcache.set(key, res, time=RESULT_CACHE_TIME)

  return result_set

def get_from_ids(ids):
  """Return a result set containing multiple results for multiple ids.

  Args:
    ids: Iterable of stable IDs of volunteer opportunities.

  Returns:
    searchresult.SearchResultSet with just the entries in ids.
  """

  result_set = searchresult.SearchResultSet('', '', [])

  # First get all that we can from memcache
  results = {}
  try:
    results = memcache.get(ids, RESULT_CACHE_KEY)
  except Exception:
    pass  # Memcache is busted. Oh well.
  for (id, result) in results:
    result_set.results.append(result)

  #logging.debug("Got these: %s", results.keys())

  # OK, we've collected what we can from memcache. Now look up the rest.
  # Find the Google Base url from the datastore, then look that up in base.
  missing_ids = []
  for id in ids:
    if not id in results:
      missing_ids.append(id)

  #logging.debug("About to get these: %s", missing_ids)
  datastore_results = models.get_by_ids(models.VolunteerOpportunity, 
      missing_ids)

  datastore_missing_ids = []
  for id in ids:
    if not id in datastore_results:
      datastore_missing_ids.append(id)
  if datastore_missing_ids:
    logging.warning('Could not find entry in datastore for ids: %s' %
                    datastore_missing_ids)

  # Bogus args for search. TODO: Remove these, why are they needed above?
  args = {}
  args["vol_startdate"] = (datetime.date.today() + 
                       datetime.timedelta(days=1)).strftime("%Y-%m-%d")
  tt = time.strptime(args["vol_startdate"], "%Y-%m-%d")
  args["vol_stopdate"] = (datetime.date(tt.tm_year, tt.tm_mon, tt.tm_mday) +
                      datetime.timedelta(days=60))

  # TODO(mblain): Figure out how to pull in multiple base entries in one call.
  for (id, volunteer_opportunity_entity) in datastore_results.iteritems():
    if not volunteer_opportunity_entity.base_url:
      logging.warning('Could not find base_url in datastore for id: %s' % id)
      continue
    temp_results = query(volunteer_opportunity_entity.base_url, args, True)
    if not temp_results.results:
      # The base URL may have changed from under us. Oh well.
      # TODO: "info" is not defined so this logging line breaks.
      # logging.warning('Did not get results from base. id: %s base_url: %s '
      #                 'Last update: %s Previous failure: %s' %
      #                 (id, info.base_url, info.last_base_url_update,
      #                  info.last_base_url_update_failure))
      volunteer_opportunity_entity.base_url_failure_count += 1
      volunteer_opportunity_entity.last_base_url_update_failure = \
          datetime.datetime.now()
      volunteer_opportunity_entity.put()
      continue
    if temp_results.results[0].id != id:
      logging.error('First result is not expected result. '
                    'Expected: %s Found: %s. len(results): %s' %
                    (id, temp_results.results[0].id, len(results)))
      # Not sure if we should touch the VolunteerOpportunity or not.
      continue
    result_set.results.append(temp_results.results[0])

  return result_set
