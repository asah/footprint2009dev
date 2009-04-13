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
core classes for testing the API.
"""

from google.appengine.api import urlfetch
from google.appengine.api import memcache
from xml.dom import minidom
import xml.sax.saxutils
import re
import hashlib
import random
import math
from urllib import urlencode

DEFAULT_TEST_URL = 'http://footprint2009dev.appspot.com/api/volopps'
DEFAULT_RESPONSE_TYPES = 'rss'
LOCAL_STATIC_URL = 'http://localhost:8080/test/sampleData.xml'
CURRENT_STATIC_XML = 'sampleData0.1.xml'
#'query, num, start, provider'
ALL_TEST_TYPES = 'num, query, provider, start, geo'


class ApiResult(object):
  """result object used for testing."""
  def __init__(self, item_id, title, description, url, provider, latlong):
    self.item_id = item_id
    self.title = title
    self.description = description
    self.url = url
    self.provider = provider
    self.latlong = latlong

def get_node_data(entity):
  """returns the value of a DOM node with some escaping, substituting
  "" (empty string) if no child/value is found."""
  if (entity.firstChild == None):
    return ""
  if (entity.firstChild.data == None):
    return ""
  nodestr = entity.firstChild.data
  nodestr = xml.sax.saxutils.escape(nodestr).encode('UTF-8')
  nodestr = re.sub(r'\n', r'\\n', nodestr)
  return nodestr
    
def get_children_by_tagname(elem, name):
  """returns a list of children nodes whose name matches."""
  # TODO: use list comprehension?
  temp = []
  for child in elem.childNodes:
    if child.nodeType == child.ELEMENT_NODE and child.nodeName == name:
      temp.append(child)
  return temp
  

def get_tag_value(entity, tag):
  """within entity, find th first child with the given tagname, then
  return its value, processed to UTF-8 and with newlines escaped."""
  #print "----------------------------------------"
  nodes = entity.getElementsByTagName(tag)
  #print "nodes: "
  #print nodes
  if (nodes.length == 0):
    return ""
  #print nodes[0]
  if (nodes[0] == None):
    return ""
  if (nodes[0].firstChild == None):
    return ""
  if (nodes[0].firstChild.data == None):
    return ""
  #print nodes[0].firstChild.data
  outstr = nodes[0].firstChild.data
  outstr = xml.sax.saxutils.escape(outstr).encode('UTF-8')
  outstr = re.sub(r'\n', r'\\n', outstr)
  return outstr

def parse_rss(data):
  """convert an RSS response to an ApiResult."""
  result = []
  xmldoc = minidom.parseString(data)
  items = xmldoc.getElementsByTagName('item')
  for item in items:
    api_result = (ApiResult(
        get_tag_value(item, 'fp:id'),
        get_tag_value(item, 'title'),
        get_tag_value(item, 'description'), 
        get_tag_value(item, 'link'),
        get_tag_value(item, 'fp:provider'),
        get_tag_value(item, 'fp:latlong')))
    result.append(api_result)
  return result

def random_item(items):
  """pick a random item from a list.  TODO: is there a more concise
  way to do this in python?"""
  num_items = len(items)
  if num_items == 1:
    return items[0]
  else:
    return items[random.randrange(0, num_items - 1)]
    
def retrieve_raw_data(full_uri):
  """call urlfetch and cache the results in memcache."""
  memcache_key = hashlib.md5('api_test_data:' + full_uri).hexdigest()
  result_content = memcache.get(memcache_key)
  if not result_content:
    fetch_result = urlfetch.fetch(full_uri)
    if fetch_result.status_code != 200:
      return None
    result_content = fetch_result.content
    # memcache.set(memcache_key, result_content, time=300)
  return result_content
  
def in_location(opp, loc, radius):
  """is given opportunity within the radius of loc?"""
  loc_arr = loc.split(',')
  opp_arr = opp.latlong.split(',')
  
  loc_lat = math.radians(float(loc_arr[0].strip()))
  loc_lng = math.radians(float(loc_arr[1].strip()))
  opp_lat = math.radians(float(opp_arr[0].strip()))
  opp_lng = math.radians(float(opp_arr[1].strip()))
  
  dlng = opp_lng - loc_lng
  dlat = opp_lat - loc_lat #lat_2 - lat_1
  # TODO: rename a_val and c_val to human-readable (named for pylint)
  a_val = (math.sin(dlat / 2))**2 + \
          (math.sin(dlng / 2))**2 * math.cos(loc_lat) * math.cos(opp_lat)
  c_val = 2 * math.asin(min(1, math.sqrt(a_val)))
  dist = 3956 * c_val
  return (dist <= radius)
  
class ApiTesting(object):
  """class to hold testing methods."""
  def __init__(self, wsfi_app):
    self.web_app = wsfi_app
    self.num_failures = 0
    self.api_url = None
    self.response_type = None
    
  def fail(self):
    """report test failure."""
    self.web_app.response.set_status(500)
    
  def output(self, html):
    """macro: output some HTML."""
    self.web_app.response.out.write(html)
    
  def make_uri(self, options):
    """generate an API call given args."""
    result = self.api_url + '?output=' + self.response_type + '&'
    result += urlencode(options)
    return result
  
  def assert_valid_results(self, result_set):
    """require that the results are valid (returns true/false)."""
    if result_set is None or result_set == False:
      self.num_failures = self.num_failures + 1
      self.fail()
    else:
      if len(result_set) == 0:
        self.num_failures = self.num_failures + 1
        self.fail()
      else:
        return True

    self.output('<p class="result fail">Fail. The result set is empty.</p>')
    self.fail()
    return False
  
  def parse_raw_data(self, data):
    """wrapper for parse_TYPE()."""
    if self.response_type == 'rss':
      return parse_rss(data)
    elif self.response_type == 'xml':
      # TODO: implement: return self.parse_xml(data)
      return []
    return []
  
  def run_test(self, test_type):
    """run one test."""
    self.output('<p class="test">Running test <em>' + test_type +
                '</em> for response type <em>' + self.response_type +
                '</em></p>')
    test_func = getattr(self, 'test_' + test_type.strip(), None)
    if callable(test_func):
      test_func()
    else:
      self.output('<p class="result fail">No such test <strong>' +
                  test_type + '</strong> in suite.')
      
    return True
  
  def run_tests(self, test_type, api_url, response_type):
    """run multiple tests (comma-separated)."""
    self.api_url = api_url
    self.response_type = response_type
    
    if test_type == 'all':
      test_type = ALL_TEST_TYPES
    
    test_types = test_type.split(',')
    for test_type in test_types:
      self.run_test(test_type)

    return True
  
  def get_result_set(self, arg_list):
    """macro for forming and making a request and parsing the results."""
    full_uri = self.make_uri(arg_list)
    self.output('<p class="uri">Fetching result set for following tests</p>')
    self.output('<p class="uri">URI: ' + full_uri + '</p>')
    
    #try:
    data = retrieve_raw_data(full_uri)
    #except:
      #self.output('<p class="result fail">retrieve_raw_data failed.</p>')
      #return False
    
    try:
      opps = self.parse_raw_data(data)
      return opps
    except:
      self.output('<p class="result fail">parse_raw_data failed. ' +
                  'Unable to parse response.</p>')
    
    return None
  
  def test_num(self):
    """test whether the result set has a given number of results."""
    result = True
    expected_count = int(random_item(['7', '14', '21', '28', '57']))
    
    result_set = self.get_result_set({'num':expected_count})
    if not self.assert_valid_results(result_set):
      return False
    
    if (len(result_set) == expected_count):
      self.output('<p class="result success">Passed</p>')
    else:
      self.output('<p class="result fail">Fail. <span>Requested ' +
                  str(expected_count) + ', received ' + str(len(result_set))+
                  '</span></p>')
      result = False
    
    return result
  
  def test_query(self):
    """run a hardcoded test query (q=)."""
    result = True
    term = random_item(["hospital", "walk", "help", "read", "children",
                        "mercy"])
  
    result_set = self.get_result_set({'q':term})
    if not self.assert_valid_results(result_set):
      return False

    for opp in result_set:
      if (not re.search(term, opp.title, re.I) and
          not re.search(term, opp.description, re.I)):
        self.output('<p class="result amplification">Did not find search term '+
                    '<strong>' + term + '</strong> in item ' + opp.title +
                    ': ' + opp.description + '</p>')
        result = False
      
    if result:
      self.output('<p class="result success">Passed</p>')
    else:
      self.output('<p class="result fail">Fail. <span>One or more items did '+
                  'not match search term <strong>' + term +
                  '</strong></span></p>')
      result = False
    
    return result
  
  def test_geo(self):
    """run a query and check the geo results."""
    result = True
    loc = random_item(["37.8524741,-122.273895", "33.41502,-111.82298",
                       "33.76145285137889,-84.38941955566406",
                       "29.759956,-95.362534"])
    radius = random_item(["10", "20", "30", "50"])
  
    result_set = self.get_result_set({'vol_loc':loc, 'vol_dist':radius,
                                      'num':20})
    if not self.assert_valid_results(result_set):
      return False

    for opp in result_set:
      if (not in_location(opp, loc, radius)):
        self.output(
          '<p class="result amplification">Item outside location/distance '+
          '<strong>' + opp.id + ': ' + opp.title + '</strong> ' + 
          opp.latlong + '</p>')
        result = False
      
    if result:
      self.output('<p class="result success">Passed</p>')
    else:
      self.output('<p class="result fail">Fail. <span>One or more items did '+
                  'not fall in the requested location/distance <strong>' + 
                  '</strong></span></p>')
      result = False
    
    return result
  
  def test_provider(self):
    """run a hardcoded test query (&provider=)."""
    result = True
    term = "hospital"
    provider = "HandsOn Network"
  
    result_set = self.get_result_set({'q':term, 'provider':provider})
    if not self.assert_valid_results(result_set):
      return False

    for opp in result_set:
      if re.search(provider, opp.provider, re.I) == None:
        self.output('<p class="result amplification">Wrong provider '+
                    '<strong>' + opp.provider + '</strong> found in item '+
                    '<em>' + opp.title + '</em></p>')
        result = False
      
    if result:
      self.output('<p class="result success">Passed</p>')
    else:
      self.output('<p class="result fail">Fail. <span>One or more items '+
                  'did not match provider <strong>' + provider + '</strong>'+
                  '</span></p>')
      result = False
    
    return result
  
  def test_start(self):
    """
      Tests two result sets to ensure that the API 'start' parameter is
      valid. Assumes:
        result_set1 and result_set2 must overlap (i.e. (start2 - start1) < num_items)
        start1 < start2
        
      Simply tests to make sure that result_set1[start2] = result_set2[start1]
      and continues testing through the end of the items that should overlap
    """
    result = True
    start1 = 1
    start2 = 5
    num_items = 10
    
    result_set1 = self.get_result_set({'num': num_items, 'start': start1})
    result_set2 = self.get_result_set({'num': num_items, 'start': start2})
    if (not self.assert_valid_results(result_set1) or
        not self.assert_valid_results(result_set2)):
      return False

    for i in range(start2, num_items):
      opp1 = result_set1[i]
      opp2 = result_set2[start1 + (i - start2)]
      if (opp1.title != opp2.title):
        self.output('<p class="result amplification">List items different, '+
                    '<em>' + opp1.title + '</em> != <em>' + opp2.title +
                    '</em></p>')
        result = False
      
    if result:
      self.output('<p class="result success">Passed</p>')
    else:
      self.output('<p class="result fail">Fail. <span>Start param returned '+
                  'non-overlapping results</p>')
      result = False
    
    return result
