#!/usr/bin/python
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

# TODO: remove silly dependency on dapper.net-- thought I'd need
# it for the full scrape, but ended up not going that way.

"""open source load testing tool for footprint."""

import sys
import os
import urllib
import urlparse
import re
import thread
import time
from datetime import datetime
import socket
import random

DEFAULT_TIMEOUT = 10
socket.setdefaulttimeout(DEFAULT_TIMEOUT)

# set to a lower number if you have problems
CONCURRENT_PAGE_FETCHERS = 30

CONCURRENT_STATIC_FETCHERS = 10
STATIC_CONTENT_HITRATE = 80

START_TS = datetime.now()
def delta_secs(ts1, ts2):
  delta_ts = ts2 - ts1
  return 3600*24.0*delta_ts.days + \
      1.0*delta_ts.seconds + \
      delta_ts.microseconds / 1000000.0

def perfstats(queries):
  secs_elapsed = delta_secs(START_TS, datetime.now())
  qps = queries / secs_elapsed
  return (secs_elapsed, qps)

RESULTS = []
RESULTS_lock = thread.allocate_lock()

def append_results(res):
  RESULTS_lock.acquire()
  RESULTS.append(res)
  RESULTS_lock.release()

REQUEST_TYPES = {}
CACHE_HITRATE = {}
REQUEST_FREQ = []
def register_request_type(name, func, freq=10, cache_hitrate="50%"):
  """setup a test case.  Default to positive hitrate so we get warm vs. 
  cold cache stats.  Freq is the relative frequency for this type of
  request-- larger numbers = larger percentage for the blended results."""
  REQUEST_TYPES[name] = func
  CACHE_HITRATE[name] = int(re.sub(r'%', '', str(cache_hitrate).strip()))
  for i in range(freq):
    REQUEST_FREQ.append(name)

#BASE_URL = "http://footprint2009dev.appspot.com/"
BASE_URL = "http://footprint-loadtest.appspot.com/"

def disable_caching(url):
  """footprint-specific method to disable caching."""
  if url.find("?") > 0:
    # note: ?& is harmless
    return url + "&cache=0"
  else:
    return url + "?cache=0"

URLS_SEEN = {}
def make_request(cached, url):
  """actually make HTTP request."""
  if not cached:
    url = disable_caching(url)
  if url not in URLS_SEEN:
    seen_url = re.sub(re.compile("^"+BASE_URL), '/', url)
    print "fetching "+seen_url
    URLS_SEEN[url] = True
  try:
    infh = urllib.urlopen(url)
    content = infh.read()
  except:
    print "error reading "+url
    content = ""
  return content

def search_url(base, loc="Chicago,IL", keyword="park"):
  """construct FP search URL, defaulting to [park] near [Chicago,IL]"""
  if BASE_URL[-1] == '/' and base[0] == '/':
    url = BASE_URL+base[1:]
  else:
    url = BASE_URL+base
  if loc and loc != "":
    url += "&vol_loc="+loc
  if keyword and keyword != "":
    url += "&q="+keyword
  return url

def error_request(name, cached=False):
  """requests for 404 junk on the site.  Here mostly to prove that
  the framework does catch errors."""
  make_request(cached, BASE_URL+"foo")
register_request_type("error", error_request, freq=5)

def static_url():
  """all static requests are roughly equivalent."""
  return BASE_URL+"images/background-gradient.png"

def fp_find_embedded_objects(base_url, content):
  """cheesy little HTML parser, which also approximates browser caching
  of items on both / and /ui_snippets."""
  objs = []
  # strip newlines/etc. used in formatting
  content = re.sub(r'\s+', ' ', content)
  # one HTML element per line
  content = re.sub(r'>', '>\n', content)
  for line in content.split('\n'):
    #print "found line: "+line
    match = re.search(r'<(?:img[^>]+src|script[^>]+src|link[^>]+href)\s*=\s*(.+)',
                      line)
    if match:
      match2 = re.search(r'^["\'](.+?)["\']', match.group(1))
      url = match2.group(1)
      url = re.sub(r'[.][.]/images/', 'images/', url)
      url = urlparse.urljoin(base_url, url)
      #print "found url: "+url+"\n  on base: "+base_url
      if url not in objs:
        objs.append(url)
  return objs

static_content_request_queue = []
static_content_request_lock = thread.allocate_lock()

def fetch_static_content(base_url, content):
  """find the embedded JS/CSS/images and request them."""
  urls = fp_find_embedded_objects(base_url, content)
  static_content_request_lock.acquire()
  static_content_request_queue.extend(urls)
  static_content_request_lock.release()

def static_fetcher_main():
  """thread for fetching static content."""
  while True:
    if len(static_content_request_queue) == 0:
      time.sleep(1)
      continue
    static_content_request_lock.acquire()
    url = static_content_request_queue.pop(0)
    static_content_request_lock.release()
    cached = (random.randint(0, 99) < STATIC_CONTENT_HITRATE)
    make_request(cached, url)

def homepage_request(name, cached=False):
  """request to FP homepage."""
  content = make_request(cached, BASE_URL)
  content += make_request(cached, search_url("/ui_snippets?", keyword=""))
  return content
register_request_type("homepage", homepage_request)

def initial_serp_request(name, cached=False):
  content = make_request(cached, search_url("/search#"))
  content += make_request(cached, search_url("/ui_snippets?"))
  return content
# don't expect much caching-- use 10% hitrate so we can see warm vs. cold stats
register_request_type("initial_serp", initial_serp_request, cache_hitrate="10%")

def nextpage_serp_request(name, cached=False):
  # statistically, nextpage is page 2
  # 50% hitrate due to the overfetch algorithm
  make_request(cached, search_url("/ui_snippets?start=11"))
  # we expect next-page static content to be 100% cacheable
  # so don't return content
  return ""
# nextpage is relatively rare, but this includes all pagination requests
register_request_type("nextpage", nextpage_serp_request, freq=5)

def api_request(name, cached=False):
  # API calls are probably more likely to ask for more results and/or paginate
  make_request(cached, search_url("/api/volopps?num=20&key=testkey"))
  # API requests don't create static content requests
  return ""
# until we have more apps, API calls will be rare
register_request_type("api", api_request, freq=2)

def setup_tests():
  request_type_counts = {}
  for name in REQUEST_FREQ:
    if name in request_type_counts:
      request_type_counts[name] += 1.0
    else:
      request_type_counts[name] = 1.0
  print "CONCURRENT_PAGE_FETCHERS: %d" % CONCURRENT_PAGE_FETCHERS
  print "CONCURRENT_STATIC_FETCHERS: %d" % CONCURRENT_STATIC_FETCHERS
  print "STATIC_CONTENT_HITRATE: %d%%" % STATIC_CONTENT_HITRATE
  print "request type breakdown:"
  for name, cnt in request_type_counts.iteritems():
    print "  %4.1f%% - %4d%% cache hitrate - %s" % \
        (100.0*cnt/float(len(REQUEST_FREQ)), CACHE_HITRATE[name], name)

RUNNING = True
def run_tests():
  # give the threading system a chance to startup
  while RUNNING:
    testname = REQUEST_FREQ[random.randint(0, len(REQUEST_FREQ)-1)]
    func = REQUEST_TYPES[testname]
    ts1 = datetime.now()
    cached = (random.randint(0, 99) < CACHE_HITRATE[testname])
    content = func(testname, cached)
    elapsed = delta_secs(ts1, datetime.now())
    # don't count static content towards latency--
    # too hard to model CSS/JS execution costs, HTTP pipelining
    # and parallel fetching.  But we do want to create load on the
    # servers
    if content and content != "":
      fetch_static_content(BASE_URL, content)
    if cached:
      result_name = testname + " (warm cache)"
    else:
      result_name = testname + " (cold cache)"
    append_results([result_name, elapsed])

setup_tests()
for i in range(CONCURRENT_PAGE_FETCHERS):
  thread.start_new_thread(run_tests, ())

for i in range(CONCURRENT_STATIC_FETCHERS):
  thread.start_new_thread(static_fetcher_main, ())

while True:
  time.sleep(2)
  current_max = len(RESULTS)
  total_secs_elapsed, total_qps = perfstats(current_max)
  print " %4.1f: %4.1f queries/sec (avg across workload)" % \
      (total_secs_elapsed, total_qps)
  sum_elapsed_time = {}
  counts = {}
  for i in range(0, current_max-1):
    name, elapsed_time = RESULTS[i]
    if name in sum_elapsed_time:
      sum_elapsed_time[name] += elapsed_time
      counts[name] += 1
    else:
      sum_elapsed_time[name] = elapsed_time
      counts[name] = 1
  for name in sorted(sum_elapsed_time):
    print "  %4d requests, %6dms avg latency for %s" % \
        (counts[name], int(1000*sum_elapsed_time[name]/counts[name]), name)

#from optparse import OptionParser
#if __name__ == "__main__":
#  parser = OptionParser("usage: %prog [options]...")
#  parser.set_defaults(metros=False)
#  parser.set_defaults(load_cache=True)
#  parser.add_option("--metros", action="store_true", dest="metros")
#  parser.add_option("--load_cache", action="store_true", dest="load_cache")
#  parser.add_option("--noload_cache", action="store_false", dest="load_cache")
#  (options, args) = parser.parse_args(sys.argv[1:])
#  if options.metros:
#    crawl_metros()
#  read_metros()
#  if options.load_cache:
#    load_cache()
#  else:
#    try:
#      os.unlink(CACHE_FN)
#    except:
#      print name
#  num_cached_pages = len(pages)
#
#  outstr = ""
#  for url in metros:
#    thread.start_new_thread(crawl_metro_page, (url+"vol/", ""))
#
#  print_status()
#  sys.exit(0)