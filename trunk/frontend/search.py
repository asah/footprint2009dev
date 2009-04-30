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

"""
high-level routines for querying backend datastores and processing the results.
"""

import calendar
import datetime
import hashlib
import logging
import re

from google.appengine.api import memcache

import api
import base_search
import geocode
import scoring

CACHE_TIME = 24*60*60  # seconds

# args is expected to be a list of args
# and any path info is supposed to be homogenized into this,
# e.g. /listing/56_foo should be resolved into [('id',56)]
# by convention, repeated args are ignored, LAST ONE wins.
def search(args):
  """run a search against the backend specified by the 'backend' arg.
  Returns a result set that's been (a) de-dup'd ("merged") and (b) truncated
  to the appropriate number of results ("clipped").  Impression tracking
  happens here as well."""
  
  # TODO(paul): Create a QueryParams object to handle validation.
  #     Validation should be lazy, so that (for example) here
  #     only 'num' and 'start' are validated, since we don't
  #     yet need the rest.  QueryParams can have a function to
  #     create a normalized string, for the memcache key.
  # pylint: disable-msg=C0321
  num = 10
  if api.PARAM_NUM in args:
    num = int(args[api.PARAM_NUM])
    if num < 1: num = 1
    if num > 999: num = 999
  args[api.PARAM_NUM] = num

  start_index = 1
  if api.PARAM_START in args:
    start_index = int(args[api.PARAM_START])
    if start_index < 1: start_index = 1
    if start_index > 1000-num: start_index = 1000-num
  args[api.PARAM_START] = start_index

  overfetch_ratio = 2.0
  if api.PARAM_OVERFETCH_RATIO in args:
    overfetch_ratio = float(args[api.PARAM_OVERFETCH_RATIO])
    if overfetch_ratio < 1.0: overfetch_ratio = 1.0
    if overfetch_ratio > 10.0: overfetch_ratio = 10.0
  args[api.PARAM_OVERFETCH_RATIO] = overfetch_ratio

  use_cache = True
  if api.PARAM_CACHE in args and args[api.PARAM_CACHE] == '0':
    use_cache = False
    logging.info('Not using search cache')

  if api.PARAM_TIMEPERIOD in args:
    period = args[api.PARAM_TIMEPERIOD]
    # No need to pass thru, just convert period to discrete date args.
    del args[api.PARAM_TIMEPERIOD]
    range = None
    today = datetime.date.today()
    if period == 'today':
      range = (today, today)
    elif period == 'this_weekend':
      days_to_sat = 5 - today.weekday()
      delta = datetime.timedelta(days=days_to_sat);
      this_saturday = today + delta
      this_sunday = this_saturday + datetime.timedelta(days=1)
      range = (this_saturday, this_sunday)
    elif period == 'this_week':
      days_to_mon = 0 - today.weekday()
      delta = datetime.timedelta(days=days_to_mon);
      this_monday = today + delta
      this_sunday = this_monday + datetime.timedelta(days=6)
      range = (this_monday, this_sunday)
    elif period == 'this_month':
      days_to_first = 1 - today.day
      delta = datetime.timedelta(days=days_to_first)
      first_of_month = today + delta
      days_to_month_end = calendar.monthrange(today.year, today.month)[1] - 1
      delta = datetime.timedelta(days=days_to_month_end)
      last_of_month = first_of_month + delta
      range = (first_of_month, last_of_month)

    
    if range:
      start_date = range[0].strftime("%Y-%m-%d")
      end_date = range[1].strftime("%Y-%m-%d")
      args[api.PARAM_VOL_STARTDATE] = start_date
      args[api.PARAM_VOL_ENDDATE] = end_date
      logging.info(start_date + '...' + end_date)

  # TODO: query param (& add to spec) for defeating the cache (incl FastNet)
  # I (mblain) suggest using "zx", which is used at Google for most services.

  # TODO: Should construct our own normalized query string instead of
  # using the browser's querystring.

  args_array = [str(key)+'='+str(value) for (key, value) in args.items()]
  args_array.sort()
  normalized_query_string = str('&'.join(args_array))

  result_set = None
  memcache_key = hashlib.md5('search:' + normalized_query_string).hexdigest()
  if use_cache:
    # note: key cannot exceed 250 bytes
    result_set = memcache.get(memcache_key)
    if result_set:
      logging.info('in cache: "' + normalized_query_string + '"')
    else:
      logging.info('not in cache: "' + normalized_query_string + '"')

  if not result_set:
    result_set = fetch_result_set(args)
    memcache.set(memcache_key, result_set, time=CACHE_TIME)

  result_set.clip_merged_results(args[api.PARAM_START], args[api.PARAM_NUM])
  result_set.track_views()
  return result_set


def fetch_result_set(args):
  """Validate the search parameters, and perform the search."""
  if api.PARAM_Q not in args:
    args[api.PARAM_Q] = ""

  # api.PARAM_OUTPUT is only used by callers (the view)
  #   (though I can imagine some output formats dictating which fields are
  #    retrieved from the backend...)
  #
  #if args[api.PARAM_OUTPUT] not in ['html', 'tsv', 'csv', 'json', 'rss', 
  #  'rssdesc', 'xml', 'snippets_list']
  #
  # TODO: csv list of fields
  #if args[api.PARAM_FIELDS] not in ['all', 'rss']:

  # TODO: process dbg -- currently, anything goes...

  # RESERVED: v
  # RESERVED: sort
  # RESERVED: type

  args["lat"] = args["long"] = ""
  if api.PARAM_VOL_LOC in args:
    if re.match(r'[0-9.-]+\s*,\s*[0-9.-]+', args[api.PARAM_VOL_LOC]):
      args["lat"], args["long"] = args[api.PARAM_VOL_LOC].split(",")
      zoom = 5
    elif re.match(r'[0-9.-]+\s*,\s*[0-9.-]+,\s*[0-9]+',
                  args[api.PARAM_VOL_LOC]):
      args["lat"], args["long"], zoom = args[api.PARAM_VOL_LOC].split(",")
    else:
      res = geocode.geocode(args[api.PARAM_VOL_LOC])
      if res != "":
        args["lat"], args["long"], zoom = res.split(",")
    args["lat"] = args["lat"].strip()
    args["long"] = args["long"].strip()
    if api.PARAM_VOL_DIST not in args:
      zoom = int(zoom)
      if zoom == 1: # country
        args[api.PARAM_VOL_DIST] = 500
      elif zoom == 2: # region
        args[api.PARAM_VOL_DIST] = 300
      elif zoom == 3: # county
        args[api.PARAM_VOL_DIST] = 100
      elif zoom == 4 or zoom == 0: # city/town
        args[api.PARAM_VOL_DIST] = 50
      elif zoom == 5: # postal code
        args[api.PARAM_VOL_DIST] = 25
      elif zoom > 5: # street or level
        args[api.PARAM_VOL_DIST] = 10
  else:
    args[api.PARAM_VOL_LOC] = args[api.PARAM_VOL_DIST] = ""

  result_set = base_search.search(args)
  scoring.score_results_set(result_set, args)
  result_set.dedup()
  return result_set
