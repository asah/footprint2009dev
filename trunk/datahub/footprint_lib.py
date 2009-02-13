# Copyright 2009 Google Inc.  All Rights Reserved.
#

from datetime import datetime
import parse_footprint
import os
from pytz import timezone
import pytz

SEP = "\t"

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
  return nodes[0].firstChild.data


# Google Base uses ISO8601... in PST -- I kid you not:
# http://base.google.com/support/bin/answer.py?answer=78170&hl=en#Events%20and%20Activities
# and worse, you have to change an env var in python...
def cvtDateTimeToGoogleBase(datestr, timestr, tz):
  # datestr = YYYY-MM-DD
  # timestr = HH:MM:SS
  # tz = America/New_York
  #print "datestr="+datestr+" timestr="+timestr+" tz="+tz
  if (timestr == ""):
    ts = datetime.strptime(datestr, "%Y-%m-%d")
  else:
    if (tz == ""):
      tz = "UTC"
    origtz = timezone(tz)
    ts = datetime.strptime(datestr + " " + timestr, "%Y-%m-%d %H:%M:%S")
    ts = ts.replace(tzinfo=origtz)
    ts = ts.astimezone(timezone("PST8PDT"))
  # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00  (in PST)
  res = ts.strftime("%Y-%m-%dT%H:%M:%S")
  return res

def getBaseEventRequiredFields(opp, org):
  # title
  s = getTagValue(opp, "title")

  # description
  s += SEP
  s += getTagValue(opp, "description")

  # link
  s += SEP
  url = getTagValue(opp, "providerURL")
  if (url == ""):
    url = getTagValue(org, "providerURL")
  if (url == ""):
    url = getTagValue(org, "organizationURL")
  s += url

  # location.  note: avoid commas, so it works with CSV
  # (this is good enough for the geocoder)
  s += SEP
  s += getTagValue(opp, "city") + " "
  s += getTagValue(opp, "region") + " "
  s += getTagValue(opp, "postalCode")

  # event_time_range
  # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
  s += SEP
  startDate = getTagValue(opp, "startDate")
  startTime = getTagValue(opp, "startTime")
  endDate = getTagValue(opp, "endDate")
  endTime = getTagValue(opp, "endTime")
  tz = getTagValue(opp, "tz_olson_path")
  # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
  if (startDate == ""):
    s += ""
  elif (endDate == ""):
    s += cvtDateTimeToGoogleBase(startDate, startTime, tz)
  else:
    s += cvtDateTimeToGoogleBase(startDate, startTime, tz)
    s += "/"
    s += cvtDateTimeToGoogleBase(endDate, endTime, tz)

  return s


def convertToGoogleBaseEventsType(xmldoc):
  organizations = xmldoc.getElementsByTagName("Organization")
  known_orgs = {}
  for org in organizations:
    id = getTagValue(org, "organizationID")
    if (id != ""):
      known_orgs[id] = org
    
  s = "this is the header line\n"
  opportunities = xmldoc.getElementsByTagName("Opportunity")
  for opp in opportunities:
    id = getTagValue(opp, "opportunityID")
    if (id == ""):
      continue
    org_id = getTagValue(opp, "organizationID")
    if (org_id not in known_orgs):
      print "unknown org_id: " + org_id + ".  skipping opportunity " + id
      continue
    org = known_orgs[org_id]
    s += getBaseEventRequiredFields(opp, org)
    # event_type
    s += SEP
    s += "volunteering"
    s += "\n"
  return s


if __name__ == "__main__":
  sys = __import__('sys')
  fp = __import__('parse_footprint')
  xmldoc = fp.ParseFootprintXML(sys.argv[1])
  print convertToGoogleBaseEventsType(xmldoc)

#  for org in xmldoc.getElementsByTagName("Organization"):
#    for node in org.childNodes:
#      if node.firstChild != None:
#        print node.tagName + "=" + node.firstChild.data

