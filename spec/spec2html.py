#!/usr/bin/python
#
# didn't use generateDS because it required a slew of packages to be installed,
# like pulling on a sweater.

from xml.dom import minidom
import sys
import os
import re

def prefix(s, tag, str):
  return s.sub(tag, str+tag, s)

s = sys.stdin.read()
s = re.sub(r'(\r?\n|\r)', r'', s)
s = re.sub(r'<[?]xml.+?>', r'', s)
s = re.sub(r'</xs:schema.*?>', r'', s)
s = re.sub(r'<(/?(code|p|a|br).*?)>', r'QQ\1EE', s)
s = re.sub(r'</?xs:(complexType)>', r'', s)
s = re.sub(r'</?xs:(restriction).*?>', r'', s)
s = re.sub(r'<', r'', s)
s = re.sub(r'>', r'', s)
s = re.sub(r'/?xs:annotation', r'', s)
s = re.sub(r'/xs:(simple|complex)Type', r'<br/>', s)
s = re.sub(r'xs:((simple|complex)Type) name="(.+?)"', r'<a name="\3"><h3>\3 (\1)</h3></a>\n', s)
s = re.sub(r'xs:restriction base="(xs:)?(.+?)"', r'derived from: <code>\2</code><br/>', s)
s = re.sub(r'xs:enumeration value="(.+?)"/', r'allowed value: <code>\1</code><br/>', s)
s = re.sub(r'/xs:all', r'</blockquote>', s)
s = re.sub(r'xs:all', r'<blockquote>', s)
s = re.sub(r'/xs:attribute', r'', s)
s = re.sub(r'\s*xs:attribute name="(.+?)"', r'<a name="\1"><h3>\1 (attribute)</h3></a>\n', s)
s = re.sub(r'/xs:sequence', r'', s)
s = re.sub(r'xs:sequence.+?xs:element', r'xs:selement', s)
s = re.sub(r'xs:pattern value="(.+?)"/', r'must match (regular expression): <code>\1</code><br/>', s)
s = re.sub(r'/xs:element', r'<br/>', s)
s = re.sub(r'\s*xs:selement name="(.+?)"', r'<a name="\1"><h3>\1 (repeated element)</h3></a>\n', s)
s = re.sub(r'\s*xs:element name="(.+?)"', r'<a name="\1"><h3>\1 (element)</h3></a>\n', s)
s = re.sub(r'type="(xs:)?(.+?)"', r'datatype: \2<br/>', s)
s = re.sub(r'minOccurs="0"', r'required: optional.<br/>', s)
s = re.sub(r'minOccurs="([0-9]+)"', r'required: at least \1 times<br/>', s)
s = re.sub(r'maxOccurs="unbounded"', r'\n', s)
#s = re.sub(r'/xs:documentation', r'</i>', s)
#s = re.sub(r'xs:documentation', r'<i>', s)
s = re.sub(r'/xs:documentation', r'</i>', s)
s = re.sub(r'xs:documentation\s*', r'<br/><i style="font-size:80%">', s)
s = re.sub(r'!\[CDATA\[\s*', r'', s)
s = re.sub(r'\]\]', r'', s)
s = re.sub(r'QQ', r'<', s)
s = re.sub(r'EE', r'>', s)
s = re.sub(r'\s*<br/>', r'<br/>\n', s)


print "<html><body>"
print "<style>"
print "body {"
print "    font-family: sans-serif;"
print "    font-size: 100%;"
print "    margin: 0;"
print "    padding: 0;"
print "}"
print "</style>"
print "<h1>Footprint XML Specification</h1>"
print s
print "</body></html>"