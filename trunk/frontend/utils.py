# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom

def GetXmlDomText(dom):
  text = ''
  for child in dom.childNodes:
    if child.nodeType == minidom.Node.TEXT_NODE:
      text += child.data
  return text