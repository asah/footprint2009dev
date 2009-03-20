# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cgi
import datetime
import time
import os
import re
import urllib
import logging
import md5
import posting

from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from xml.dom import minidom

import api
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
  if args[api.PARAM_SORT] == "r":
    # newest
    return "modification_time"
  else:
    # "relevancy" is the Base default
    return "relevancy"

def base_restrict_str(key,val=None):
  res = '+[' + urllib.quote_plus(re.sub(r'_', r' ', key))
  if val != None:
    res += ':' + urllib.quote_plus(str(val))
  return res + ']'

# note: many of the XSS and injection-attack defenses are unnecessary
# given that the callers are also protecting us, but I figure better
# safe than sorry, and defense-in-depth.
def search(args, num_overfetch=200):
  """
  Params:
      num_overfetch: Number of records to fetch, which is different (larger)
        than the 'num' field in the search args.  The caller will fetch more
        records than the user requests, in order to perform de-duping here in
        the app.
  """

  logging.info(args);
  base_query = ""

  if api.PARAM_Q in args and args[api.PARAM_Q] != "":
    base_query += urllib.quote_plus(args[api.PARAM_Q])

  if api.PARAM_VOL_STARTDATE in args or api.PARAM_VOL_ENDDATE in args:
    startdate = None
    if api.PARAM_VOL_STARTDATE in args and args[api.PARAM_VOL_STARTDATE] != "":
      try:
        startdate = datetime.datetime.strptime(
                       args[api.PARAM_VOL_STARTDATE][:10], "%Y-%m-%d")
      except:
        logging.error("malformed start date: %s" % 
           args[api.PARAM_VOL_STARTDATE])
    if not startdate:
      # note: default vol_startdate is "tomorrow"
      # in base, event_date_range YYYY-MM-DDThh:mm:ss/YYYY-MM-DDThh:mm:ss
      # appending "Z" to the datetime string would mean UTC
      startdate = datetime.date.today() + datetime.timedelta(days=1)
      args[api.PARAM_VOL_STARTDATE] = startdate.strftime("%Y-%m-%d")

    enddate = None
    if api.PARAM_VOL_ENDDATE in args and args[api.PARAM_VOL_ENDDATE] != "":
      try:
        enddate = datetime.datetime.strptime(
                       args[api.PARAM_VOL_ENDDATE][:10], "%Y-%m-%d")
      except:
        logging.error("malformed end date: %s" % args[api.PARAM_VOL_ENDDATE])
    if not enddate:
      enddate = datetime.date(startdate.year, startdate.month, startdate.day)
      enddate = enddate + datetime.timedelta(days=1000)
      args[api.PARAM_VOL_ENDDATE] = enddate.strftime("%Y-%m-%d")
    daterangestr = '%s..%s' % (args[api.PARAM_VOL_STARTDATE], 
                       args[api.PARAM_VOL_ENDDATE])
    base_query += base_restrict_str("event_date_range", daterangestr)

  if api.PARAM_VOL_PROVIDER in args and args[api.PARAM_VOL_PROVIDER] != "":
    if re.match(r'[a-zA-Z0-9:/_. -]+', args[api.PARAM_VOL_PROVIDER]):
      base_query += base_restrict_str("feed_providername", 
                       args[api.PARAM_VOL_PROVIDER])
    else:
      # illegal providername
      # TODO: throw 500
      logging.error("illegal providername: " + args[api.PARAM_VOL_PROVIDER])

  # TODO: injection attack on sort
  if api.PARAM_SORT not in args:
    args[api.PARAM_SORT] = "r"

  # TODO: injection attacks in vol_loc
  if args[api.PARAM_VOL_LOC] != "":
    args[api.PARAM_VOL_DIST] = int(str(args[api.PARAM_VOL_DIST]))
    # TODO: looks like the default is 25 mi, check for value as a min here?
    """
    base_query += base_restrict_str("location", '@"%s" + %dmi' % \
                                      (args[api.PARAM_VOL_LOC],
                                       args[api.PARAM_VOL_DIST]))
    """
  if (args["lat"] != "" and args["long"] != "" 
       and args[api.PARAM_VOL_DIST] != ""):
    lat, lng = float(args["lat"]), float(args["long"])
    dist = float(args[api.PARAM_VOL_DIST])
    base_query += "[latitude%%3E%%3D%.2f]" % (lat+1000 - dist/69.1)
    base_query += "[latitude%%3C%%3D%.2f]" % (lat+1000 + dist/69.1)
    base_query += "[longitude%%3E%%3D%.2f]" % (lng+1000 - dist/50)
    base_query += "[longitude%%3C%%3D%.2f]" % (lng+1000 + dist/50)

  # Base URL for snippets search on Base.
  #   Docs: http://code.google.com/apis/base/docs/2.0/attrs-queries.html
  # TODO: injection attack on backend
  if "backend" not in args:
    args["backends"] = "http://www.google.com/base/feeds/snippets"

  cust_arg = make_base_arg("customer")
  if cust_arg not in args:
    args[cust_arg] = 5663714;
  base_query += base_restrict_str("customer_id", int(args[cust_arg]))

  #base_query += base_restrict_str("detailurl")

  if api.PARAM_START not in args:
    args[api.PARAM_START] = 1

  query_url = args["backends"]
  query_url += "?max-results=" + str(num_overfetch)
  query_url += "&start-index=" + str(args[api.PARAM_START])
  query_url += "&orderby=" + make_base_orderby_arg(args)
  query_url += "&content=" + "all"
  query_url += "&bq=" + base_query

  logging.info("calling Base: "+query_url)
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
    url = utils.GetXmlElementTextOrEmpty(entry, 'g:detailurl')
    # ID is the 'stable id' of the item generated by base.
    # Note that this is not the base url expressed as the Atom id element.
    id = utils.GetXmlElementTextOrEmpty(entry, 'g:id')
    # Base URL is the url of the item in base, expressed with the Atom id tag.
    base_url = utils.GetXmlElementTextOrEmpty(entry, 'id')
    snippet = utils.GetXmlElementTextOrEmpty(entry, 'content')
    title = utils.GetXmlElementTextOrEmpty(entry, 'title')
    location = utils.GetXmlElementTextOrEmpty(entry, 'g:location_string')
    res = searchresult.SearchResult(url, title, snippet, 
                                    location, id, base_url)
    # TODO: escape?
    res.provider = utils.GetXmlElementTextOrEmpty(entry, 'g:feed_providername')
    res.orig_idx = i+1
    res.latlong = ""
    latstr = utils.GetXmlElementTextOrEmpty(entry, 'g:latitude')
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
      logging.info('invalid date range: %s for %s' % (res.event_date_range,url))
    else:
      # first match is start date/time
      res.startdate = datetime.datetime.strptime(m[0], '%Y-%m-%dT%H:%M:%S')
      # last match is either end date/time or start/date time
      res.enddate = datetime.datetime.strptime(m[-1], '%Y-%m-%dT%H:%M:%S')
       
    # posting.py currently has an authoritative list of fields in "argnames"
    # that are available to submitted events which may later appear in GBase
    # so with a few exceptions we want those same fields to become
    # attributes of our result object
    except_names = ["title", "description"]
    for name in posting.argnames:
      if name not in except_names:
        # these attributes are likely to become part of the "g" namespace
        # http://base.google.com/support/bin/answer.py?answer=58085&hl=en
        setattr(res, name, utils.GetXmlElementTextOrEmpty(entry, "g:" + name))

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

  # OK, we've collected what we can from memcache. Now look up the rest.
  # Find the Google Base url from the datastore, then look that up in base.
  missing_ids = []
  for id in ids:
    if not id in results:
      missing_ids.append(id)

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
  args[api.PARAM_VOL_STARTDATE] = (datetime.date.today() +
                       datetime.timedelta(days=1)).strftime("%Y-%m-%d")
  tt = time.strptime(args[api.PARAM_VOL_STARTDATE], "%Y-%m-%d")
  args[api.PARAM_VOL_ENDDATE] = (datetime.date(tt.tm_year, 
          tt.tm_mon, tt.tm_mday) + datetime.timedelta(days=60))

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
