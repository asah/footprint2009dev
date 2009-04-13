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
      res = args[api.PARAM_VOL_LOC]
    else:
      res = geocode.geocode(args[api.PARAM_VOL_LOC])
    if res != "":
      args["lat"], args["long"] = res.split(",")
      # don't break on spurious whitespace
      args["lat"] = args["lat"].strip()
      args["long"] = args["long"].strip()
    if api.PARAM_VOL_DIST not in args:
      args[api.PARAM_VOL_DIST] = 25
  else:
    args[api.PARAM_VOL_LOC] = args[api.PARAM_VOL_DIST] = ""

  result_set = base_search.search(args)
  scoring.score_results_set(result_set, args)
  result_set.dedup()
  return result_set
