# Copyright 2009 Google Inc.  All Rights Reserved.
#

from datetime import datetime
import parse_footprint
import os
from pytz import timezone
import pytz

FIELDSEP = "\t"
RECORDSEP = "\n"

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
  if (datestr == ""):
    return ""
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

csv_repeated_fields = ['categories','audiences',]
direct_map_fields = ['opportunityID','organizationID','abstract','volunteersSlots','volunteersFilled','volunteersStillNeeded','minimumAge','sexRestrictedTo','skills','contactName','contactPhone','contactEmail','providerURL','language','lastUpdated','expires',]
organization_fields = ['nationalEIN','guidestarID','name','missionStatement','description','phone','fax','email','organizationURL','logoURL','providerURL',]
def value(n):
  if (n.firstChild != None):
    return n.firstChild.data.replace(",", "")
  else:
    return ""

def flattenFieldToCSV(field):
  #print field
  return ",".join(filter(lambda x: x != "", map(value, field.childNodes)))

debug = False
printhead = False
def outputField(name, value):
  global printhead
  if printhead == True:
    return name
  if debug:
    if (len(value) > 70):
      value = value[0:67] + "..."
    return name.rjust(22) + " : " + value
  return value

def outputLocationField(node, mapped_name):
  # note: avoid commas, so it works with CSV
  # (this is good enough for the geocoder)
  loc = getTagValue(node, "city") + " "
  loc += getTagValue(node, "region") + " " 
  loc += getTagValue(node, "postalCode")
  return outputField(mapped_name, loc)


def outputTagValue(node, fieldname):
  return outputField(fieldname, getTagValue(node, fieldname))

def getDirectMappedField(opp, org):
  s = FIELDSEP
  paid = getTagValue(opp, "paid")
  if (paid == "" or paid.lower()[0] != "y"):
    paid = "n"
  else:
    paid = "y"
  s += outputField("paid", paid)
  for field in direct_map_fields:
    s += FIELDSEP
    s += outputTagValue(opp, field)
  for field in organization_fields:
    s += FIELDSEP
    s += outputTagValue(org, field)
  for field in csv_repeated_fields:
    s += FIELDSEP
    l = opp.getElementsByTagName(field)
    if (l.length > 0):
      s += outputField(field,flattenFieldToCSV(l[0]))
    else:
      s += ""
  # orgLocation
  s += FIELDSEP
  l = opp.getElementsByTagName(field)
  if (l.length > 0):
    s += outputLocationField(l[0], "orgLocation")
  else:
    s += outputField("orgLocation", "")
  return s

# these are fields that exist in other Base schemas-- for the sake of
# possible syndication, we try to make ourselves look like other Base
# feeds.  Since we're talking about a small overlap, these fields are
# populated *as well as* direct mapping of the footprint XML fields.
#
# gender - The gender of the individual.
# quantity - Number. Indicate a value of 0 for out-of-stock items.
# job_function - The function of the employment position., e.g. Product Manager
# employer - The company providing employment.
# publish_date - The date the job was published.
# 
def getBaseOtherFields(opp, org):
  s = FIELDSEP
  # gender
  s += outputTagValue(opp, "sexRestritedTo")
  # quantity
  s += FIELDSEP
  s += outputTagValue(opp, "volunteersStillNeeded")
  # employer
  s += FIELDSEP
  s += outputTagValue(org, "name")
  # publish_date
  # TODO: what tz is lastUpdated?
  s += FIELDSEP
  pubdate = getTagValue(opp, "lastUpdated")
  tz = ""
  if (pubdate == ""):
    startDate = getTagValue(opp, "startDate")
    startTime = getTagValue(opp, "startTime")
    tz = getTagValue(opp, "tzOlsonPath")
    pubdate = cvtDateTimeToGoogleBase(startDate, startTime, tz)
  s += outputField("publish_date", pubdate)
  # expiration_date, in PST
  s += FIELDSEP
  expires = getTagValue(opp, "expires")
  # TODO: what tz is expires?
  expires = cvtDateTimeToGoogleBase(expires, "", tz)
  s += outputField("expires", expires)
  return s

def getBaseEventRequiredFields(opp, org):
  s = ""

  # title
  s += outputTagValue(opp, "title")
  s += FIELDSEP

  # description
  s += outputTagValue(opp, "description")

  # link
  s += FIELDSEP
  url = getTagValue(opp, "providerURL")
  if (url == ""):
    url = getTagValue(org, "providerURL")
  if (url == ""):
    url = getTagValue(org, "organizationURL")
  s += outputField("link", url)

  # event_type
  s += FIELDSEP
  s += outputField("event_type", "volunteering")

  return s


def convertToGoogleBaseEventsType(xmldoc):
  s = ""
  global printhead, debug
  recno = 0

  printhead = True
  s += getBaseEventRequiredFields(xmldoc, xmldoc)
  s += getBaseOtherFields(xmldoc, xmldoc)
  s += getDirectMappedField(xmldoc, xmldoc)
  printhead = False

  organizations = xmldoc.getElementsByTagName("Organization")
  known_orgs = {}
  for org in organizations:
    id = getTagValue(org, "organizationID")
    if (id != ""):
      known_orgs[id] = org
    
  opportunities = xmldoc.getElementsByTagName("Opportunity")
  for opp in opportunities:
    id = getTagValue(opp, "opportunityID")
    if (id == ""):
      print "no opportunityID"
      continue
    org_id = getTagValue(opp, "organizationID")
    if (org_id not in known_orgs):
      print "unknown org_id: " + org_id + ".  skipping opportunity " + id
      continue
    org = known_orgs[org_id]
    opp_locations = opp.getElementsByTagName("location")
    opp_times = opp.getElementsByTagName("dateTimeDuration")
    for opptime in opp_times:
      # event_time_range
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
      startDate = getTagValue(opptime, "startDate")
      startTime = getTagValue(opptime, "startTime")
      endDate = getTagValue(opptime, "endDate")
      endTime = getTagValue(opptime, "endTime")
      tz = getTagValue(opptime, "tzOlsonPath")
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
      if (startDate == ""):
        startend = ""
      elif (endDate == ""):
        startend = cvtDateTimeToGoogleBase(startDate, startTime, tz)
      else:
        startend = cvtDateTimeToGoogleBase(startDate, startTime, tz)
        startend += "/"
        startend += cvtDateTimeToGoogleBase(endDate, endTime, tz)
      for opploc in opp_locations:
        recno = recno + 1
        if debug:
          s += "--- record %s\n" % (i)
        s += RECORDSEP
        s += outputLocationField(opploc, "location") + FIELDSEP
        s += outputField("event_time_range", startend) + FIELDSEP
        s += getBaseEventRequiredFields(opp, org)
        s += getBaseOtherFields(opp, org)
        s += getDirectMappedField(opp, org)
  return s


if __name__ == "__main__":
  sys = __import__('sys')
  fp = __import__('parse_footprint')
  #debug = True
  #FIELDSEP = "\n"
  xmldoc = fp.ParseFootprintXML(sys.argv[1])
  print convertToGoogleBaseEventsType(xmldoc)

