# Copyright 2009 Google Inc.  All Rights Reserved.
#

import os


from xml.dom import minidom

def GetXmlDomText(node):
  text = ''
  for child in node.childNodes:
    if child.nodeType == minidom.Node.TEXT_NODE:
      text += child.data
  return text

def GetXmlElementText(node, namespace, tagname):
  """Returns the text of the first node found with the given namespace/tagname.
  
  May return None if no node found."""
  child_nodes = node.getElementsByTagNameNS(namespace, tagname)
  if child_nodes:
    return GetXmlDomText(child_nodes[0])

def StringToInt(string):
  try:
    return int(string)
  except ValueError:
    return None
