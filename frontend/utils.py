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

def GetXmlElementTextNS(node, namespace, tagname):
  """Returns the text of the first node found with the given namespace/tagname.
  
  May return None if no node found."""
  child_nodes = node.getElementsByTagNameNS(namespace, tagname)
  if child_nodes:
    return GetXmlDomText(child_nodes[0])

def GetXmlElementText(node, tagname):
  """Returns the text of the first node found with the given tagname.
  
  May return None if no node found."""
  child_nodes = node.getElementsByTagName(tagname)
  if child_nodes:
    return GetXmlDomText(child_nodes[0])

def GetXmlElementTextOrEmpty(node, tagname):
  """Returns the text of the first node found with the given namespace/tagname.
  returns empty string if no node found."""
  res = GetXmlElementText(node, tagname)
  if res == None:
    return ""
  return res

def StringToInt(string):
  try:
    return int(string)
  except ValueError:
    return None
