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
import time

from google.appengine.api import memcache
from xml.sax.saxutils import escape

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
    
    self.xml_url = escape(url)

    parsed_url = urlparse.urlparse(url)
    self.url_short = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)

    # user's expressed interest, models.InterestTypeProperty
    self.interest = None
    # stats from other users.
    self.interest_count = 0
    
  def js_escape(self, string):
    # TODO: This escape method is overly agressive and is messing some snippets
    # up.  We only need to escape single and double quotes.
    return re.escape(string)

class SearchResultSet(object):
  def __init__(self, query_url_unencoded, query_url_encoded, results):
    self.query_url_unencoded = query_url_unencoded
    self.query_url_encoded = escape(query_url_encoded)
    self.results = results

  def apply_post_search_filters(self, args):
    if "DoW" in args and len(args["DoW"]) > 0:
      # we are going to filter by day of week
      for i,res in enumerate(self.results):
        dow = str(res.startdate.strftime("%w"))
        if args["DoW"].find(dow) < 0:
          del self.results[i]

    if "ampm" in args and (args["ampm"] == "am" or args["ampm"] == "pm"):
      # we are going to filter by am|pm
      for i,res in enumerate(self.results):
        # assumes we have 24 hour data
        hr = int(res.startdate.strftime("%H"))
        if ((hr < 12 and args["ampm"] == "pm") 
             or (hr >= 12 and args["ampm"] == "am")):
          del self.results[i]

  def dedup(self):
    # we are going to make another list of results merged by title and snippet
    
    def safe_str(s):
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

    self.merged_results = []
    for i,res in enumerate(self.results):
      # first we assign all our results a merge_key
      res.merge_key = (safe_str(res.title)
          + safe_str(res.snippet) + safe_str(res.location))
      # we will be sorting & de-duping the merged results
      # by start date so we need an epoch time
      res.t_startdate = res.startdate.timetuple()
      # this is for the list of any results merged with this one
      res.merged_list = []
      res.merged_debug = []

    def merge_result(set, res):
      merged = False
      for i, primary_result in enumerate(set):
        if primary_result.merge_key == res.merge_key:
          merged = True
          listed = False
          for n, merged_result in enumerate(set[i].merged_list):
            # do we already have this date + url?
            if (merged_result.t_startdate==set[i].t_startdate 
                 and merged_result.url==set[i].url):
              listed = True
              break

          if not listed:
            set[i].merged_list.append(res)
            set[i].merged_debug.append(
                res.location + ":" + res.startdate.strftime("%Y-%m-%d"))
          break
      if not merged:
        set.append(res)

    for i,res in enumerate(self.results):
      res.month_day = (time.strftime("%B", res.t_startdate)
         + " " + str(int(time.strftime("%d", res.t_startdate))))
      merge_result(self.merged_results, res)

    def compare_merged_dates(a, b):
      if (a.t_startdate > b.t_startdate): return 1
      elif (a.t_startdate < b.t_startdate): return -1
      else: return 0

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
          # now we are making something for the django template to display
          # for the merged list we only show the unique locations and dates
          # but we also use the url if it is unique too
          # for more than 2 extras we will offer "more" and "less"
          # we will be showing the unique dates as "Month Date"

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
  
