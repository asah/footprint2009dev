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
