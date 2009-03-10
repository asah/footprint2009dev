# Copyright 2009 Google Inc.  All Rights Reserved.
#
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from xml.dom import minidom
import xml.sax.saxutils
import re
import sys

DEFAULT_TEST_URL = 'http://footprint2009dev.appspot.com/api/search'
DEFAULT_RESPONSE_TYPES = 'rss'
LOCAL_STATIC_URL = 'http://localhost:8080/test/sampleData.xml'
CURRENT_STATIC_XML = 'sampleData0.1.xml'

class ApiResult(object):
  def __init__(self, title, description, url):
    self.title = title
    self.description = description
    self.url = url

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
  
  TestNumResults(webApp, apiUrl, responseType)
  TestQueryTerm(webApp, apiUrl, responseType)
  return True

def RetrieveRawData(fullUri):
  result = urlfetch.fetch(fullUri)
  return result.content
  
def ParseRSS(data):
  result = []
  
  xmldoc = minidom.parseString(data)
  items = xmldoc.getElementsByTagName('item')
  for item in items:
    result.append(ApiResult(getTagValue(item, 'title'), getTagValue(item, 'description'), getTagValue(item, 'link')))
  
  return result
  
def ParseXML(data):
  return []

def ParseRawData(data, responseType):
  if responseType == 'rss':
    return ParseRSS(data)
  elif responseType == 'xml':
    return ParseXML(data)
    
  return []

def TestNumResults(webApp, apiUrl, responseType):
  result = True;
  requestCount = 7
  
  webApp.response.out.write('<p class="test">TestNumResults running...</p>')
  # quick test to see if the api returns the requested number of results
  fullUri = MakeUri(apiUrl, responseType, ["num=" + str(requestCount)])
  webApp.response.out.write('<p class="uri">' + fullUri + '</p>')
  
  try:
    data = RetrieveRawData(fullUri)
  except:
    webApp.response.out.write('<p class="result fail">RetrieveRawData failed.</p>')
    return False
  
  #try:
  opps = ParseRawData(data, responseType)
  if (len(opps) == requestCount):
    webApp.response.out.write('<p class="result success">Passed</p>')
  else:
    webApp.response.out.write('<p class="result fail">Fail. <span>Requested ' + str(requestCount) + ', received ' + str(len(opps)) + '</span></p>')
    result = False
  #except:
  #  webApp.response.out.write('<p class="result fail">ParseRawData failed. Unable to parse response.</p>')
  
  return result

def TestQueryTerm(webApp, apiUrl, responseType):
  result = True
  term = 'walk'
  
  webApp.response.out.write('<p class="test">TestQueryTerm running...</p>')
  # quick test to see if the api returns the requested number of results
  fullUri = MakeUri(apiUrl, responseType, ["q=" + str(term)])
  webApp.response.out.write('<p class="uri">' + fullUri + '</p>')
  
  try:
    data = RetrieveRawData(fullUri)
  except:
    webApp.response.out.write('<p class="result fail">RetrieveRawData failed.</p>')
    return False
  
  #try:
  opps = ParseRawData(data, responseType)
  for opp in opps:
    if re.search(term, opp.title, re.I) == None and re.search(term, opp.description, re.I) == None:
      webApp.response.out.write('<p class="result amplification">Did not find search term <strong>' + term + '</strong> in item ' + opp.title + ': ' + opp.description)
      result = False
    
  if result:
    webApp.response.out.write('<p class="result success">Passed</p>')
  else:
    webApp.response.out.write('<p class="result fail">Fail. <span>One or more items did not match search term <strong>' + term + '</strong></span></p>')
    result = False
  #except:
  #  webApp.response.out.write('<p class="result fail">ParseRawData failed. Unable to parse response.</p>')
  
  return result