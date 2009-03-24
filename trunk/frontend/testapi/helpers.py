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

from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from xml.dom import minidom
import xml.sax.saxutils
import re
import sys
import logging
import md5
from urllib import urlencode

DEFAULT_TEST_URL = 'http://footprint2009dev.appspot.com/api/volopps'
DEFAULT_RESPONSE_TYPES = 'rss'
LOCAL_STATIC_URL = 'http://localhost:8080/test/sampleData.xml'
CURRENT_STATIC_XML = 'sampleData0.1.xml'
ALL_TEST_TYPES = 'num, query, provider, start' #'query, num, start, provider'

class ApiResult(object):
  def __init__(self, id, title, description, url, provider, latlong):
    self.id = id
    self.title = title
    self.description = description
    self.url = url
    self.provider = provider
    self.latlong = latlong
    logging.info(latlong)

class ApiTesting(object):
  def __init__(self, wsfi_app):
    self.web_app = wsfi_app
    self.num_failures = 0
    
  def Output(self, html):
    self.web_app.response.out.write(html)
    
  def getNodeData(entity):
    if (entity.firstChild == None):
      return ""
    if (entity.firstChild.data == None):
      return ""
    
    s = entity.firstChild.data
    s = xml.sax.saxutils.escape(s).encode('UTF-8')
    s = re.sub(r'\n', r'\\n', s)
    return s
    
  def getChildrenByTagName(elem, name):
    temp = []
    for child in elem.childNodes:
      if child.nodeType == child.ELEMENT_NODE and child.nodeName == name:
        temp.append(child)
        
    return temp
  
  def getTagValue(self, entity, tag):
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
    s = nodes[0].firstChild.data
    s = xml.sax.saxutils.escape(s).encode('UTF-8')
    s = re.sub(r'\n', r'\\n', s)
    return s
  
  def SafeGet(handler, name, default):
    value = handler.request.get(name) or default
    return value
  
  def MakeUri(self, options):
    result = self.api_url + '?output=' + self.response_type
    result = result + '&' + urlencode(options)
      
    return result
  
  def AssertValidResultSet(self, result_set):
    if result_set is None or result_set == False:
      self.num_failures = self.num_failures + 1
    else:
      if len(result_set) == 0:
        self.num_failures = self.num_failures + 1
      else:
        return True

    self.Output('<p class="result fail">Fail. The result set is empty.</p>')      
    return False
  
  def RunTest(self, test_type):
    self.Output('<p class="test">Running test <em>' + test_type + '</em> for response type <em>' + self.response_type + '</em></p>')
    test_func = getattr(self, 'Test_' + test_type.strip(), None)
    if callable(test_func):
      test_func()
    else:
      self.Output('<p class="result fail">No such test <strong>' + test_type + '</strong> in suite.')
      
    return True
  
  def RunTests(self, testType, apiUrl, responseType):
    self.api_url = apiUrl
    self.response_type = responseType
    
    if testType == 'all':
      testType = ALL_TEST_TYPES
    
    test_types = testType.split(',')
    for test_type in test_types:
      self.RunTest(test_type)

    return True
  
  def hash_md5(self, s):
    it = md5.new()
    it.update(s)
    return it.digest()

  def RetrieveRawData(self, fullUri):
    memcache_key = self.hash_md5('api_test_data:' + fullUri)
    result_content = memcache.get(memcache_key)
    if not result_content:
      fetch_result = urlfetch.fetch(fullUri)
      if fetch_result.status_code != 200:
        return None
      result_content = fetch_result.content
      memcache.set(memcache_key, result_content, time=300)

    return result_content
    
  def ParseRSS(self, data):
    result = []
    
    xmldoc = minidom.parseString(data)
    items = xmldoc.getElementsByTagName('item')
    for item in items:
      api_result = (ApiResult(self.getTagValue(item, 'fp:id'), self.getTagValue(item, 'title'),
                              self.getTagValue(item, 'description'), self.getTagValue(item, 'link'),
                              self.getTagValue(item, 'fp:provider'), self.getTagValue(item, 'fp:latlong')))
      result.append(api_result)
      
    return result
    
  def ParseXML(data):
    return []
  
  def ParseRawData(self, data):
    if self.response_type == 'rss':
      return self.ParseRSS(data)
    elif self.response_type == 'xml':
      return self.ParseXML(data)
      
    return []
  
  def GetResultSet(self, arg_list):
    full_uri = self.MakeUri(arg_list)
    self.Output('<p class="uri">Fetching result set for following tests</p>')
    self.Output('<p class="uri">URI: ' + full_uri + '</p>')
    
    #try:
    data = self.RetrieveRawData(full_uri)
    #except:
      #self.Output('<p class="result fail">RetrieveRawData failed.</p>')
      #return False
    
    try:
      opps = self.ParseRawData(data)
      return opps
    except:
      self.Output('<p class="result fail">ParseRawData failed. Unable to parse response.</p>')
    
    return None
    
  def Test_num(self):
    result = True
    expected_count = 7
    
    result_set = self.GetResultSet({'num':expected_count})
    if not self.AssertValidResultSet(result_set):
      return False
    
    if (len(result_set) == expected_count):
      self.Output('<p class="result success">Passed</p>')
    else:
      self.Output('<p class="result fail">Fail. <span>Requested ' + str(expected_count) + ', received ' + str(len(result_set)) + '</span></p>')
      result = False
    
    return result
  
  def Test_query(self):
    result = True
    term = "hospital"
    provider = "HandsOn Network"
  
    result_set = self.GetResultSet({'q':term, 'provider':provider})
    if not self.AssertValidResultSet(result_set):
      return False

    for opp in result_set:
      if re.search(term, opp.title, re.I) == None and re.search(term, opp.description, re.I) == None:
        self.Output('<p class="result amplification">Did not find search term <strong>' + term + '</strong> in item ' + opp.title + ': ' + opp.description + '</p>')
        result = False
      
    if result:
      self.Output('<p class="result success">Passed</p>')
    else:
      self.Output('<p class="result fail">Fail. <span>One or more items did not match search term <strong>' + term + '</strong></span></p>')
      result = False
    
    return result
  
  def Test_provider(self):
    result = True
    term = "hospital"
    provider = "HandsOn Network"
  
    result_set = self.GetResultSet({'q':term, 'provider':provider})
    if not self.AssertValidResultSet(result_set):
      return False

    for opp in result_set:
      if re.search(provider, opp.provider, re.I) == None:
        self.Output('<p class="result amplification">Wrong provider <strong>' + opp.provider + '</strong> found in item <em>' + opp.title + '</em></p>')
        result = False
      
    if result:
      self.Output('<p class="result success">Passed</p>')
    else:
      self.Output('<p class="result fail">Fail. <span>One or more items did not match provider <strong>' + provider + '</strong></span></p>')
      result = False
    
    return result
  
  def Test_start(self):
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
    
    result_set1 = self.GetResultSet({'num': num_items, 'start': start1})
    result_set2 = self.GetResultSet({'num': num_items, 'start': start2})
    if not self.AssertValidResultSet(result_set1) or not self.AssertValidResultSet(result_set2):
      return False

    for i in range(start2, num_items):
      opp1 = result_set1[i]
      opp2 = result_set2[start1 + (i - start2)]
      if (opp1.title != opp2.title):
        self.Output('<p class="result amplification">List items different, <em>' + opp1.title + '</em> != <em>' + opp2.title + '</em></p>')
        result = False
      
    if result:
      self.Output('<p class="result success">Passed</p>')
    else:
      self.Output('<p class="result fail">Fail. <span>Start param returned non-overlapping results</p>')
      result = False
    
    return result