# Copyright 2009 Google Inc.  All Rights Reserved.
#
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from xml.dom import minidom
import xml.sax.saxutils
import re
import sys

DEFAULT_TEST_BACKEND_TYPE = 'localdynamic'
DEFAULT_TEST_URL = 'http://localhost:8088/api/search'
DEFAULT_RESPONSE_TYPES = 'rss'
LOCAL_STATIC_URL = 'http://localhost:8080/test/sampleData.xml'
CURRENT_STATIC_XML = 'sampleData0.1.xml'

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
  TestNumResults(webApp, apiUrl, responseType)
  return True

def RetrieveRawData(fullUri):
  result = urlfetch.fetch(fullUri)
  return result.content
  
def ParseRSS(data):
  result = []
  
  xmldoc = minidom.parseString(data)
  items = xmldoc.getElementsByTagName('item')
  for item in items:
    result.append(getTagValue(item, 'title'))
  
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
    webApp.response.out.write('<p class="result fail">Fail. <span>Requested ' + str(requestCount) + ', received ' + str(len(opps)) + '</p>')
    result = False
  #except:
  #  webApp.response.out.write('<p class="result fail">ParseRawData failed. Unable to parse response.</p>')

  
  return result