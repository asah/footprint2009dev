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

# Google base namespace, typically xmlns:g='http://base.google.com/ns/1.0'
XMLNS_BASE='http://base.google.com/ns/1.0'
# Atom namespace, typically xmlns='http://www.w3.org/2005/Atom'
XMLNS_ATOM='http://www.w3.org/2005/Atom'

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
  base_query = ""

  # TODO: injection attack on q
  if "q" in args:
    base_query += ' ' + args["q"]

  # TODO: injection attack on startDate
  if "startDate" not in args:
    # note: default startDate is "tomorrow"
    # in base, event_date_range YYYY-MM-DDThh:mm:ss/YYYY-MM-DDThh:mm:ss
    # appending "Z" to the datetime string would mean UTC
    args["startDate"] = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

  if "stopDate" not in args:
    tt = time.strptime(args["startDate"], "%Y-%m-%d")
    args["stopDate"] = datetime.date(tt.tm_year, tt.tm_mon, tt.tm_mday) + datetime.timedelta(days=60)

  base_query += ' [event_date_range: %s..%s]' % (args["startDate"], args["stopDate"])

  # TODO: injection attack on sort
  if "sort" not in args:
    args["sort"] = "r"

  # TODO: injection attacks in vol_loc
  if args["vol_loc"] != "":
    args["vol_dist"] = int(str(args["vol_dist"]))
    # TODO: looks like the default is 25 mi, should we check for some value as a min here?
    base_query += ' [location: @"%s" + %dmi]' % (args["vol_loc"], args["vol_dist"])

  # Base URL for snippets search on Base.
  #   Docs: http://code.google.com/apis/base/docs/2.0/attrs-queries.html
  # TODO: injection attack on backend
  if "backend" not in args:
    args["backends"] = "http://www.google.com/base/feeds/snippets"

  if make_base_arg("customer") not in args:
    args[make_base_arg("customer")] = 5663714;
  base_query += ' [customer id: '+str(int(args[make_base_arg("customer")]))+']'

  base_query += ' [detailurl][event_date_range]'

  if "num" not in args:
    args["num"] = 10

  if "start" not in args:
    args["start"] = 1

  #for k in args: logging.info("arg["+str(k)+"]="+str(args[k]))
  #url_params = urllib.urlencode({'max-results': args["num"],
  url_params = urllib.urlencode({'max-results': 200,
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
  result_set.args = args

  # TODO: consider removing this-- urlfetch() already has a good cache.
  # (avoids cache overflow).  If we still want it, then move to
  # search.py, i.e. not Base specific.
  # TODO: query param (& add to spec) for defeating the cache (incl FastNet)
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
  total_results = float(len(elems))
  t0 = time.mktime(time.strptime(args["startDate"], "%Y-%m-%d"))
  for i,entry in enumerate(elems):
    # Note: using entry.getElementsByTagName('link')[0] isn't very stable;
    # consider iterating through them for the one where rel='alternate' or
    # whatever the right thing is.
    #urltag = entry.getElementsByTagName('link')[0].getAttribute('href')
    url = utils.GetXmlElementText(entry, XMLNS_BASE, 'detailurl')
    # ID is the 'stable id' of the item generated by base.
    # Note that this is not the base url expressed as the Atom id element.
    id = utils.GetXmlElementText(entry, XMLNS_BASE, 'id')
    # Base URL is the url of the item in base, expressed with the Atom id tag.
    base_url = utils.GetXmlElementText(entry, XMLNS_ATOM, 'id')
    snippet = utils.GetXmlElementText(entry, XMLNS_ATOM, 'content')
    title = utils.GetXmlElementText(entry, XMLNS_ATOM, 'title')
    location = utils.GetXmlElementText(entry, XMLNS_BASE, 'location_string')
    #logging.info("title="+title+"  location="+str(location)+"  url="+url)
    #logging.info("title="+title+"  location="+str(location))
    res = searchresult.SearchResult(url, title, snippet, location, id, base_url)
    # TODO: escape?
    res.provider = utils.GetXmlElementText(entry, XMLNS_BASE, 'feed_providername')
    res.orig_idx = i+1
    res.latlong = ""
    #logging.info(re.sub(r'><', r'>\n<',entry.toxml()))
    latstr = utils.GetXmlElementText(entry, XMLNS_BASE, 'latitude')
    longstr = utils.GetXmlElementText(entry, XMLNS_BASE, 'longitude')
    if latstr and longstr and latstr != "" and longstr != "":
      res.latlong = latstr + "," + longstr

    #lat_element = utils.GetXmlElementText(entry, XMLNS_BASE, 'latitude')
    #long_element = utils.GetXmlElementText(entry, XMLNS_BASE, 'longitude')
    #if lat_element and lat_element != "" and long_element and long_element != "":
    #  res.latlong = lat_element + "," + long_element

    # TODO: remove-- this is working around a DB bug where all the latlongs are the same
    if "geocode_responses" in args:
      res.latlong = geocode.geocode(location, args["geocode_responses"]!="nocache" )

    res.event_date_range = utils.GetXmlElementText(entry, XMLNS_BASE, 'event_date_range')
    res.startdate = re.sub(r'[T ].+$', r'', res.event_date_range)
    # todo: start time, etc.
    # score results
    res.score_by_base_rank = (total_results - i)/total_results 
    res.score = res.score_by_base_rank
    
    t1 = time.mktime(time.strptime(res.startdate[:10], "%Y-%m-%d"))
    if t1 == t0:
      res.date_dist_multiplier = 1.0
    elif t1 < t0:
      res.date_dist_multiplier = .0001
    else:
      res.date_dist_multiplier = 1/((t1 - t0)/(24 * 3600))

    if (("lat" not in args) or args["lat"] == "" or
        ("long" not in args) or args["long"] == "" or
         res.latlong == ""):
      #logging.info("qloc=%s,%s - listing=%s" % (args["lat"], args["long"], res.latlong))
      res.geo_dist_multiplier = 0.5
    else:
      # TODO: grr... something's wrong in the DB and we're getting same geocodes for everything
      lat, long = res.latlong.split(",")
      latdist = float(lat) - float(args["lat"])
      longdist = float(long) - float(args["long"])
      # keep one value to right of decimal
      delta_dist = latdist*latdist + longdist * longdist
      #logging.info("qloc=%s,%s - listing=%s,%s - dist=%s,%s - delta = %g" %
      #             (args["lat"], args["long"], lat, long, latdist, longdist, delta_dist))
      # reasonably local
      if delta_dist > 0.025:
        delta_dist = 0.9 + delta_dist
      else:
        delta_dist = delta_dist / (0.025 / 0.9)
      if delta_dist > 0.999:
        delta_dist = 0.999
      res.geo_dist_multiplier = 1.0 - delta_dist

    score_notes = ""
    res.score = res.score_by_base_rank
    score_notes += "  GBase relevance score: " + str(res.score_by_base_rank)

    res.score *= res.date_dist_multiplier
    score_notes += "  date dist multiplier: " + str(res.date_dist_multiplier)

    res.score *= res.geo_dist_multiplier
    score_notes += "  geo dist multiplier: " + str(res.geo_dist_multiplier)

    res.scorestr = "%.4g" % (res.score)
    res.score_notes = score_notes
    result_set.results.append(res)
    if cache and res.id:
      key = "searchresult:" + res.id
      memcache.set(key, res, time=RESULT_CACHE_TIME)
      # Datastore updates are expensive and space-consuming, so only add them
      # if a user expresses interest in an opportunity--e.g. elsewhere.

  def compare_scores(x,y):
    diff = y.score - x.score
    if (diff > 0): return 1
    if (diff < 0): return -1
    return 0

  result_set.results.sort(cmp=compare_scores)
  for i,res in enumerate(result_set.results):
    res.idx = i+1

  return result_set

def get_from_id(id):
  """Return a searchresult from the stable ID."""
  key = 'searchresult:' + id
  try:
    search_result = memcache.get(key)
    if search_result:
      return search_result
  except Exception:
    search_result = None
  
  # Now things get more complex: We need to find the base entry from the
  # datastore, then look that up in base, then return that info.
  key = 'id:' + id
  info = models.VolunteerOpportunity.get_by_key_name(key)
  if not info:
    logging.warning('Could not find entry in datastore for id: %s' % id)
    return None
  if not info.base_url:
    logging.warning('Could not find base_url in datastore for id: %s' % id)
    return None
  result_set = query(info.base_url, None, True)
  if not result_set.results:
    # The base URL may have changed from under us. Oh well.
    logging.warning('Did not get results from base. id: %s base_url: %s '
                    'Last update: %s Previous failure: %s' %
                    (id, info.base_url, info.last_base_url_update, 
                     info.last_base_url_update_failure))
    info.base_url_failure_count += 1
    info.last_base_url_update_failure = datetime.datetime.now()
    info.put()
    return None
  
  if (result_set.results[0].id != id):
    logging.error('First result is not expected result. '
                  'Expected: %s Found: %s. len(results): %s' %
                  (id, result_set.results[0].id, len(results)))
    # Not sure if we should touch the VolunteerOpportunity or not.
    return None
  
  return result_set.results[0]
  
def get_from_ids(ids):
  """Return a result set containing multiple results for multiple ids."""
  result_set = searchresult.SearchResultSet('', '', [])
  for id in ids:
    result = get_from_id(id)
    if result:
      result_set.results.append(result)
  return result_set
