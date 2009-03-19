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
from xml.dom import minidom
import xml.sax.saxutils
import re
import sys
import logging

DEFAULT_TEST_URL = 'http://footprint2009dev.appspot.com/api/search'
DEFAULT_RESPONSE_TYPES = 'rss'
LOCAL_STATIC_URL = 'http://localhost:8080/test/sampleData.xml'
CURRENT_STATIC_XML = 'sampleData0.1.xml'

class ApiResult(object):
  def __init__(self, id, title, description, url, provider, latlong):
    self.id = id
    self.title = title
    self.description = description
    self.url = url
    self.provider = provider
    self.latlong = latlong

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

def getTagValue(entity, tag):
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

def GetTestText():
  return 'Hello, World'

def SafeGet(handler, name, default):
  value = handler.request.get(name) or default
  return value

def MakeUri(apiUrl, responseType, options):
  result = apiUrl + '?output=' + responseType
  for option in options:
    result = result + '&' + option
    
  return result

def RunTests(webApp, testType, apiUrl, responseType):
  webApp.response.out.write('<h2>running all test for response type: <em>' + responseType + '</em>')

  
  result_set = GetResultSet(webApp, apiUrl, responseType, ["num=7"])
  TestNumResults(webApp, result_set, 7)
  
  result_set = GetResultSet(webApp, apiUrl, responseType, ["q=hospital", "provider=HandsOn%20Network"])
  TestQueryTerm(webApp, result_set, "hospital")
  TestProvider(webApp, result_set, "HandsOn Network")
  
  result_set1 = GetResultSet(webApp, apiUrl, responseType, ["num=10", "start=1"])
  result_set2 = GetResultSet(webApp, apiUrl, responseType, ["num=10", "start=5"])
  TestStart(webApp, result_set1, result_set2, 1, 5, 10)
  
  return True

def RetrieveRawData(fullUri):
  result = urlfetch.fetch(fullUri)
  return result.content
  
def ParseRSS(data):
  result = []
  
  xmldoc = minidom.parseString(data)
  items = xmldoc.getElementsByTagName('item')
  for item in items:
    api_result = (ApiResult(getTagValue(item, 'fp:id'), getTagValue(item, 'title'),
                            getTagValue(item, 'description'), getTagValue(item, 'link'),
                            getTagValue(item, 'fp:provider'), getTagValue(item, 'fp:latlong')))
    result.append(api_result)
    
  return result
  
def ParseXML(data):
  return []

def ParseRawData(data, responseType):
  if responseType == 'rss':
    return ParseRSS(data)
  elif responseType == 'xml':
    return ParseXML(data)
    
  return []

def GetResultSet(webApp, apiUrl, responseType, arg_list):
  fullUri = MakeUri(apiUrl, responseType, arg_list)
  webApp.response.out.write('<p class="uri">Fetching result set for following tests</p>')
  webApp.response.out.write('<p class="uri">URI: ' + fullUri + '</p>')
  
  try:
    data = RetrieveRawData(fullUri)
  except:
    webApp.response.out.write('<p class="result fail">RetrieveRawData failed.</p>')
    return False
  
  try:
    opps = ParseRawData(data, responseType)
    return opps
  except:
    webApp.response.out.write('<p class="result fail">ParseRawData failed. Unable to parse response.</p>')
  
  return None
  
def TestNumResults(webApp, result_set, expected_count):
  result = True
  
  webApp.response.out.write('<p class="test">TestNumResults running...</p>')
  if (len(result_set) == expected_count):
    webApp.response.out.write('<p class="result success">Passed</p>')
  else:
    webApp.response.out.write('<p class="result fail">Fail. <span>Requested ' + str(expected_count) + ', received ' + str(len(result_set)) + '</span></p>')
    result = False
  
  return result

def TestQueryTerm(webApp, result_set, term):
  result = True

  webApp.response.out.write('<p class="test">TestQueryTerm running...</p>')
  for opp in result_set:
    if re.search(term, opp.title, re.I) == None and re.search(term, opp.description, re.I) == None:
      webApp.response.out.write('<p class="result amplification">Did not find search term <strong>' + term + '</strong> in item ' + opp.title + ': ' + opp.description + '</p>')
      result = False
    
  if result:
    webApp.response.out.write('<p class="result success">Passed</p>')
  else:
    webApp.response.out.write('<p class="result fail">Fail. <span>One or more items did not match search term <strong>' + term + '</strong></span></p>')
    result = False
  
  return result

def TestProvider(webApp, result_set, provider):
  result = True

  webApp.response.out.write('<p class="test">TestProvider running...</p>')
  for opp in result_set:
    if re.search(provider, opp.provider, re.I) == None:
      webApp.response.out.write('<p class="result amplification">Wrong provider <strong>' + opp.provider + '</strong> found in item <em>' + opp.title + '</em></p>')
      result = False
    
  if result:
    webApp.response.out.write('<p class="result success">Passed</p>')
  else:
    webApp.response.out.write('<p class="result fail">Fail. <span>One or more items did not match provider <strong>' + provider + '</strong></span></p>')
    result = False
  
  return result

def TestStart(webApp, result_set1, result_set2, start1, start2, num_items):
  """
    Tests two result sets to ensure that the API 'start' parameter is
    valid. Assumes:
      result_set1 and result_set2 must overlap (i.e. (start2 - start1) < num_items)
      start1 < start2
      
    Simply tests to make sure that result_set1[start2] = result_set2[start1]
    and continues testing through the end of the items that should overlap
  """
  result = True
  
  logging.info(result_set1)
  logging.info(result_set2)

  webApp.response.out.write('<p class="test">TestStart running...</p>')
  for i in range(start2, num_items):
    opp1 = result_set1[i]
    opp2 = result_set2[start1 + (i - start2 - 1)]
    if (opp1.title != opp2.title):
      webApp.response.out.write('<p class="result amplification">List items different, <em>' + opp1.title + '</em> != <em>' + opp2.title + '</em></p>')
      result = False
    
  if result:
    webApp.response.out.write('<p class="result success">Passed</p>')
  else:
    webApp.response.out.write('<p class="result fail">Fail. <span>Start param returned non-overlapping results</p>')
    result = False
  
  return result