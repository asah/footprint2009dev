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
version = (re.findall(r'<xs:schema version="(.+?)"', s))[0]
s = re.sub(r'(\r?\n|\r)', r'', s)
s = re.sub(r'<[?]xml.+?>', r'', s)
s = re.sub(r'</?xs:schema.*?>', r'', s)
s = re.sub(r'<code>(.+?)</code>', r'<a href="#\1"><code>\1</code></a>', s)
s = re.sub(r'<pcode>(.+?)</pcode>', r'<code>\1</code>', s)
s = re.sub(r'<(/?(code|p|a|br|b).*?)>', r'&&\1@@', s)
s = re.sub(r'<', r'', s)
s = re.sub(r'/?>', r'', s)

#blockquoting
s = re.sub(r'/xs:(all|sequence)', r'</blockquote>', s)
#Change element to selement for distinguishing multiple entries later on
s = re.sub(r'xs:sequence(.+?)xs:element', r'xs:sequence\1xs:selement', s)
#blockquoting
s = re.sub(r'xs:(all|sequence)', r'<blockquote>', s)

#Named types
s = re.sub(r'xs:(simple|complex)Type name="(.+?)"(.+?)/xs:(simple|complex)Type', r'<div class="namedType"><div class="entryName"><a name="\2">\2 (\1 type)</a></div>\3</div>', s)

#Extension
s = re.sub(r'xs:extension\s+?base="(xs:)?(.+?)"(.+?)/xs:extension', r'<div class="info">derived from: \2</div>\3', s)

#restriction
s = re.sub(r'xs:restriction\s+?base="(xs:)?(.+?)"(.+?)/xs:restriction', r'<div class="info">derived from: \2</div>\3', s)

#attribute entries
s = re.sub(r'/xs:attribute', r'</blockquote></div>\n', s)
s = re.sub(r'\s*xs:attribute name="(.+?)"', r'<div class="entry"><blockquote><div class="entryName"><a name="\1">\1 (attribute)</a></div>\n', s)

#element entries
s = re.sub(r'/xs:element', r'</div>\n', s)
s = re.sub(r'\s*xs:selement name="(.+?)"(.+?)', r'<div class="entry repeated"><div class="entryName"><a name="\1">\1 (repeated element)</a></div>\n', s)
s = re.sub(r'\s*xs:element name="(.+?)"(.+?)', r'<div class="entry"><div class="entryName"><a name="\1">\1 (element)</a></div>\n', s)

#documentation
s = re.sub(r'xs:annotation\s+xs:documentation\s+!\[CDATA\[\s*(.+?)\s*\]\]\s+/xs:documentation\s+/xs:annotation', r'<div class="doc-text">\1</div>', s)

#Little stuff in entries
s = re.sub(r'use="(.+?)"', r'<span class="info">use is \1</span><br/>', s)
s = re.sub(r'default=""', r'<span class="info">default value: <code>(empty string)</code></span><br/>', s)
s = re.sub(r'default="(.+?)"', r'<span class="info">default value: <code>\1</code></span><br/>', s)
s = re.sub(r'fixed="(.+?)"', r'<span class="info">fixed value: <code>\1</code></span><br/>', s)
s = re.sub(r'xs:enumeration value="(.+?)"', r'<span class="info">allowed value: <code>\1</code></span><br/>', s)
s = re.sub(r'xs:pattern value="(.+?)"', r'<span class="info">must match (regular expression): <code>\1</code></span><br/>', s)
s = re.sub(r'type="(xs:)?(.+?)"', r'<span class="info">datatype: \2</span><br/>', s)
s = re.sub(r'minOccurs="0"', r'<span class="info">required: optional.</span><br/>', s)
s = re.sub(r'minOccurs="([0-9]+)"', r'<span class="info">required: at least \1 times</span><br/>', s)
s = re.sub(r'maxOccurs="1"', r'<span class="info">Multiple not allowed</span><br/>', s)
s = re.sub(r'maxOccurs="unbounded"', r'\n', s)

#putting in links
s = re.sub(r'(datatype|derived from): (locationType|dateTimeDurationType|yesNoEnum|sexRestrictedEnum|dateTimeOlsonDefaultPacific|timeOlson|dateTimeNoTZ|timeNoTZ)', r'\1: <a href="#\2"><code>\2</code></a>\n', s)
s = re.sub(r'(datatype|derived from): (string)', r'\1: <a href="http://www.w3schools.com/Schema/schema_dtypes_string.asp"><code>\2</code></a>\n', s)
s = re.sub(r'(datatype|derived from): (dateTime|date|time|duration)', r'\1: <a href="http://www.w3schools.com/Schema/schema_dtypes_date.asp"><code>\2</code></a>\n', s)
s = re.sub(r'(datatype|derived from): (integer|decimal)', r'\1: <a href="http://www.w3schools.com/Schema/schema_dtypes_numeric.asp"><code>\2</code></a>\n', s)

#Drop stuff we don't care about
s = re.sub(r'/?xs:(simpleContent|complexType)', r'', s)

#clean-up
s = re.sub(r'&&', r'<', s)
s = re.sub(r'@@', r'>', s)
s = re.sub(r'\s*<br/>', r'<br/>\n', s)


print "<html>"
print "<head>"
print "<title>Footprint XML Specification Version",version,"</title>"
#print '<LINK REL="StyleSheet" HREF="spec.css" TYPE="text/css"/>'
print "<style>"
f = open('spec.css')
print f.read()
print "</style>"
print "</head>"
print "<body>"
print '<div class="titleText">Footprint XML Specification Version',version,'</div><br>'
print s
print "</body></html>"
