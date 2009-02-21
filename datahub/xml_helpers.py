from xml.dom import minidom
from xml.sax.saxutils import escape
import re

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
  s = escape(s).encode('UTF-8')
  s = re.sub(r'\n', r'\\n', s)
  return s

def validateXML(xmldoc, known_elnames):
  for node in xmldoc.childNodes:
    if (node.nodeType == node.ELEMENT_NODE and
        node.tagName not in known_elnames):
      print "unknown tagName '"+node.tagName+"'"
      # TODO: spellchecking...
    validateXML(node, known_elnames)

def simpleParser(s, known_elnames):
  try:
    xmldoc = minidom.parseString(s)
    validateXML(xmldoc, known_elnames)
    return xmldoc
  except ExpatError, ee:
    print "XML parsing error on line ", ee.lineno
    lines = s.split("\n")
    for i in range(ee.lineno - 3, ee.lineno + 3):
      if i >= 0 and i < len(lines):
        print "%6d %s" % (i+1, lines[i])
    exit(0)
