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

from xml.dom import minidom

def get_xml_dom_text(node):
  """Returns the text of the first node found with the given tagname.
  Returns None if no node found."""
  text = ''
  for child in node.childNodes:
    if child.nodeType == minidom.Node.TEXT_NODE:
      text += child.data
  return text

def get_xml_dom_text_ns(node, namespace, tagname):
  """Returns the text of the first node found with the given namespace/tagname.
  Returns None if no node found."""
  child_nodes = node.getElementsByTagNameNS(namespace, tagname)
  if child_nodes:
    return get_xml_dom_text(child_nodes[0])

def xml_elem_text(node, tagname, default=None):
  """Returns the text of the first node found with the given namespace/tagname.
  returns default if no node found."""
  child_nodes = node.getElementsByTagName(tagname)
  if child_nodes:
    return get_xml_dom_text(child_nodes[0])
  return default

def get_last_arg(request, argname, default):
  """Returns the last urlparam in an HTTP request-- this allows the
  later args to override earlier ones, which is easier for developers
  (vs. earlier ones taking precedence)."""
  values = request.get(argname, allow_multiple=True)
  if values:
    return values[len(values) - 1]
  return default
