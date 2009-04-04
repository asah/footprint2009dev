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

import re
import urlparse
import datetime
import time
import math
import hashlib
import logging

from google.appengine.api import memcache
from xml.sax.saxutils import escape

import api
from fastpageviews import pagecount

def getRFCdatetime(when = None):
  # GAE server localtime appears to be UTC and timezone %Z
  # is an empty string so to satisfy RFC date format
  # requirements in output=rss we append the offset in hours
  # from UTC for our local time (now, UTC) i.e. +0000 hours
  # ref: http://feedvalidator.org/docs/error/InvalidRFC2822Date.html
  # ref: http://www.feedvalidator.org to check feed validity
  # eg, Tue, 10 Feb 2009 17:04:28 +0000
  if not when:
     when = time.gmtime();
  return time.strftime("%a, %d %b %Y %H:%M:%S", when) + " +0000"

class SearchResult(object):
  def __init__(self, url, title, snippet, location, id, base_url):
    # TODO: Consider using kwargs or something to make this more generic.
    self.url = url
    self.title = title
    self.snippet = snippet
    self.location = location
    self.id = id
    self.base_url = base_url
    # app engine does not currently support the escapejs filter in templates
    # so we have to do it our selves for now
    self.js_escaped_title = self.js_escape(title)
    self.js_escaped_snippet = self.js_escape(snippet)

    # TODO: find out why this is not unique
    self.xml_url = escape(url) + "#" + self.id # hack to avoid guid duplicates

    parsed_url = urlparse.urlparse(url)
    self.url_short = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)

    # user's expressed interest, models.InterestTypeProperty
    self.interest = None
    # stats from other users.
    self.interest_count = 0

    # TODO: real quality score
    self.quality_score = 0.1

    # TODO: real pageviews
    self.pageviews = 0

    self.pubDate = getRFCdatetime()

  def js_escape(self, string):
    # TODO: This escape method is overly agressive and is messing some snippets
    # up.  We only need to escape single and double quotes.
    return re.escape(string)

class SearchResultSet(object):
  """Contains a list of SearchResult objects.

  Attributes:
    results: List of SearchResults.  Required during initialization.
    merged_results: This is populated after a call to dedup().  It will
      contain the original results, after merging of duplicate entries.
    clipped_results: This is populated after a call to clip_merged_results.
      It will contain the merged_results, clamped to a start-index and
      max-length (the 'start' and 'num' query parameters).
    query_url_encoded: URL query used to retrieve data from backend.
      For debugging.
    query_url_unencoded: urllib.unquote'd version of the above.
    total_merged_results: Number of merged results after a dedup()
      operation.
  """
  def __init__(self, query_url_unencoded, query_url_encoded, results):
    self.query_url_unencoded = query_url_unencoded
    self.query_url_encoded = escape(query_url_encoded)
    self.results = results
    self.total_merged_results = 0
    self.merged_results = []
    self.pubDate = getRFCdatetime()
    self.lastBuildDate = self.pubDate

  def apply_post_search_filters(self, args):
    if (api.PARAM_VOL_STARTDAYOFWEEK in args 
         and args[api.PARAM_VOL_STARTDAYOFWEEK] != ""):
      # we are going to filter by day of week
      for i,res in enumerate(self.results):
        dow = str(res.startdate.strftime("%w"))
        if args[api.PARAM_VOL_STARTDAYOFWEEK].find(dow) < 0:
          del self.results[i]

  def clip_merged_results(self, start, num):
    """Extract just the slice of merged results from start to start+num.
    No need for bounds-checking -- python list slicing does that
    automatically."""
    self.clipped_results = self.merged_results[start:start+num]

  def track_views(self):
    logging.info(str(datetime.datetime.now())+" track_views: start")
    for i, primary_res in enumerate(self.clipped_results):
      primary_res.merged_pageviews = pagecount.IncrPageCount(
        primary_res.merge_key, 1)
      primary_res.pageviews = pagecount.IncrPageCount(primary_res.id, 1)
      for j, res in enumerate(primary_res.merged_list):
        res.pageviews = pagecount.IncrPageCount(res.id, 1)
    logging.info(str(datetime.datetime.now())+" track_views: end")

  def dedup(self):
    """modify in place, merged by title and snippet."""

    def safe_str(s):
      """private helper function for dedup()"""
      return_val = ""
      try:
        return_val = str(s)
      except ValueError:
        for i, c in enumerate(s):
          try:
            safe_char = str(c)
            return_val += safe_char
          except ValueError:
            continue # discard
      return return_val

    def assign_merge_keys():
      """private helper function for dedup()"""
      for i,res in enumerate(self.results):
        res.merge_key = hashlib.md5(safe_str(res.title) +
                                    safe_str(res.snippet) +
                                    safe_str(res.location)).hexdigest()
        # we will be sorting & de-duping the merged results
        # by start date so we need an epoch time
        res.t_startdate = res.startdate.timetuple()
        # month_day used by django
        res.month_day = (time.strftime("%B", res.t_startdate) + " " +
                         str(int(time.strftime("%d", res.t_startdate))))
        # this is for the list of any results merged with this one
        res.merged_list = []
        res.merged_debug = []

    def compare_merged_dates(a, b):
      """private helper function for dedup()"""
      if (a.t_startdate > b.t_startdate): return 1
      elif (a.t_startdate < b.t_startdate): return -1
      else: return 0

    def merge_result(res):
      """private helper function for dedup()"""
      merged = False
      for i, primary_result in enumerate(self.merged_results):
        if primary_result.merge_key == res.merge_key:
          # merge it
          listed = False
          for n, merged_result in enumerate(self.merged_results[i].merged_list):
            # do we already have this date + url?
            if (merged_result.t_startdate == self.merged_results[i].t_startdate
                and merged_result.url == self.merged_results[i].url):
              listed = True
              break
          if not listed:
            self.merged_results[i].merged_list.append(res)
            self.merged_results[i].merged_debug.append(res.location + ":" +
                res.startdate.strftime("%Y-%m-%d"))
          merged = True
          break
      if not merged:
        self.merged_results.append(res)

    def compute_more_less():
      """Now we are making something for the django template to display
      for the merged list we only show the unique locations and dates
      but we also use the url if it is unique too
      for more than 2 extras we will offer "more" and "less"
      we will be showing the unique dates as "Month Date"."""
      for i,res in enumerate(self.merged_results):
        res.idx = i + 1
        if len(res.merged_list) > 1:
          res.merged_list.sort(cmp=compare_merged_dates)
          location_was = res.location
          need_more = False
          res.less_list = []
          if len(res.merged_list) > 2:
            need_more = True
            more_id = "more_" + str(res.idx)
            res.more_id = more_id
            res.more_list = []

          more = 0
          res.have_more = True
          for n,merged_result in enumerate(res.merged_list):
            def make_linkable(text, merged_result, res):
              if merged_result.url != res.url:
                return '<a href="' + merged_result.url + '">' + text + '</a>'
              else:
                return text
  
            entry = ""
            if merged_result.location != location_was:
              location_was = merged_result.location
              entry += ('<br/>'
               + make_linkable(merged_result.location, merged_result, res)
               + ' on ')
            elif more > 0:
              entry += ', '
  
            entry += make_linkable(merged_result.month_day, merged_result, res)
            if more < 3:
              res.less_list.append(entry)
            else:
              res.more_list.append(entry)
  
            more += 1

    # dedup() main code
    assign_merge_keys()
    for i,res in enumerate(self.results):
      merge_result(res)
    compute_more_less()
    self.total_merged_results = len(self.merged_results)

