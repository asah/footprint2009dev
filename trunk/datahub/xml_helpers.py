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

#from xml.dom import pulldom
#from xml.parsers.expat pulldom

from xml.dom import minidom
from datetime import datetime
import xml.sax.saxutils
import xml.parsers.expat
import re
import unicodedata
import sys

# asah: I give up, allowing UTF-8 is just too hard without incurring
# crazy performance penalties
simple_chars = ''.join(map(chr, range(32,126)))
simple_chars_class = '[^\\n%s]' % re.escape(simple_chars)
simple_chars_re = re.compile(simple_chars_class)
def cleanString(s):
    #print "simple_chars_class=",simple_chars_class
    s = s.decode('ascii', 'replace')
    return simple_chars_re.sub('', s).encode('UTF-8')

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

progress_start_ts = datetime.now()
def printProgress(noun, progress, recno, maxrecs):
  maxrecs_str = ""
  if maxrecs > 0:
    maxrecs_str = " of " + str(maxrecs)
  if progress and recno > 0 and recno % 250 == 0:
    now = datetime.now()
    print now,": ",recno, noun, "processed" + maxrecs_str,
    secs_since_start = now - progress_start_ts
    secs_elapsed = 3600*24.0*secs_since_start.days + \
        1.0*secs_since_start.seconds + \
        secs_since_start.microseconds / 1000000.0
    rps = recno / secs_elapsed
    print "("+str(rps)+" recs/sec)"

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

def validateXML(xmldoc, known_elnames):
  for node in xmldoc.childNodes:
    if (node.nodeType == node.ELEMENT_NODE and
        node.tagName not in known_elnames):
      #print "unknown tagName '"+node.tagName+"'"
      pass
      # TODO: spellchecking...
    validateXML(node, known_elnames)

def simpleParser(s, known_elnames_list, progress):
  try:
    if known_elnames_list:
      known_elnames_dict = {}
      for item in known_elnames_list:
        known_elnames_dict[item] = True
    if progress:
      print datetime.now(),"parsing XML"
    xmldoc = minidom.parseString(s)
    # this stuff is in a try-block to avoid use-before-def on xmldoc
    if progress:
      print datetime.now(),"validating XML..."
    if known_elnames_list:
      validateXML(xmldoc, known_elnames_dict)
    if progress:
      print datetime.now(),"done."
    return xmldoc
  except xml.parsers.expat.ExpatError, ee:
    print datetime.now(),"XML parsing error on line ", ee.lineno,
    print ":", xml.parsers.expat.ErrorString(ee.code),
    print " (column ", ee.offset, ")"
    lines = s.split("\n")
    for i in range(ee.lineno - 3, ee.lineno + 3):
      if i >= 0 and i < len(lines):
        print "%6d %s" % (i+1, lines[i])
    print "writing string to xmlerror.out..."
    outfh = open("xmlerror.out","w+")
    outfh.write(s)
    outfh.close()
    sys.exit(0)

def prettyxml(doc, strip_header = False):
  s = doc.toxml("UTF-8")
  if strip_header:
    s = re.sub(r'<\?xml version="1.0" encoding="UTF-8"\?>', r'', s)
  s = re.sub(r'><', r'>\n<', s)
  # toprettyxml wasn't that pretty...
  return s
