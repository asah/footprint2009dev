#!/usr/bin/python
# Copyright 2009 Google Inc.  All Rights Reserved.
#

import hashlib
from datetime import datetime
import parse_footprint
import os
from pytz import timezone
import pytz

FIELDSEP = "\t"
RECORDSEP = "\n"

fieldtypes = {
  "title":"builtin", "description":"builtin", "link":"builtin", "event_type":"builtin", "quantity":"builtin", "expiration_date":"builtin","image_link":"builtin","event_date_range":"builtin","id":"builtin",
  "paid":"boolean","openended":"boolean",
  'providerID':'integer','feed_providerID':'integer','feedID':'integer','opportunityID':'integer','organizationID':'integer','sponsoringOrganizationID':'integer','volunteerHubOrganizationID':'integer','volunteersSlots':'integer','volunteersFilled':'integer','volunteersNeeded':'integer','minimumAge':'integer','org_nationalEIN':'integer','org_guidestarID':'integer',"commitmentHoursPerWeek":'integer',
  'providerURL':'URL','org_organizationURL':'URL','org_logoURL':'URL','org_providerURL':'URL','feed_providerURL':'URL',
  'lastUpdated':'dateTime','expires':'dateTime','feed_createdDateTime':'dateTime',
  "orgLocation":"location","location":"location",
  "duration":"string","abstract":"string","sexRestrictedTo":"string","skills":"string","contactName":"string","contactPhone":"string","contactEmail":"string","language":"string",'org_name':"string",'org_missionStatement':"string",'org_description':"string",'org_phone':"string",'org_fax':"string",'org_email':"string",'categories':"string",'audiences':"string","commitmentHoursPerWeek":"string","employer":"string","feed_providerName":"string","feed_description":"string",
}



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
direct_map_fields = ['opportunityID','organizationID','abstract','volunteersSlots','volunteersFilled','volunteersNeeded','minimumAge','sexRestrictedTo','skills','contactName','contactPhone','contactEmail','providerURL','language','lastUpdated','expires',]
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
    if (name not in fieldtypes):
      print "no type for field: " + name
      print fieldtypes[name]
    elif (fieldtypes[name] == "builtin"):
      return name
    else:
      return "c:"+name+":"+fieldtypes[name]
  if debug:
    if (len(value) > 70):
      value = value[0:67] + "..."
    return name.rjust(22) + " : " + value
  return value

def computeLocationField(node):
  # note: avoid commas, so it works with CSV
  # (this is good enough for the geocoder)
  loc = getTagValue(node, "city") + " "
  loc += getTagValue(node, "region") + " " 
  loc += getTagValue(node, "postalCode")
  return loc

def outputLocationField(node, mapped_name):
  return outputField(mapped_name, computeLocationField(node))


def outputTagValue(node, fieldname):
  return outputField(fieldname, getTagValue(node, fieldname))

def outputTagValueRenamed(node, xmlname, fieldname):
  return outputField(fieldname, getTagValue(node, xmlname))

def computeStableId(opp, org, locstr, openended, duration,
                    commitmentHoursPerWeek, startend):
  eid = getTagValue(org, "nationalEIN");
  if (eid == ""):
    # support informal "organizations" that lack EINs
    eid = getTagValue(org, "organizationURL")
  # TODO: if two providers have same listing, good odds the
  # locations will be slightly different...
  loc = locstr

  # TODO: if two providers have same listing, the time info
  # is unlikely to be exactly the same, incl. missing fields
  timestr = openended + duration + commitmentHoursPerWeek + startend
  return hashlib.md5(eid + loc + timestr).hexdigest()

def getDirectMappedField(opp, org):
  s = ""
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
    s += outputField("org_"+field, getTagValue(org, field))
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
def getBaseOtherFields(opp, org):
  s = outputField("quantity", getTagValue(opp, "volunteersNeeded"))
  s += FIELDSEP + outputField("employer", getTagValue(org, "name"))
  # TODO: publish_date?
  expires = getTagValue(opp, "expires")
  # TODO: what tz is expires?
  expires = cvtDateTimeToGoogleBase(expires, "", "UTC")
  s += FIELDSEP + outputField("expiration_date", expires)
  return s

def getBaseEventRequiredFields(opp, org):
  s = outputTagValue(opp, "title")
  s += FIELDSEP + outputTagValue(opp, "description")
  s += FIELDSEP + outputField("link", "http://change.gov/")
  s += FIELDSEP + outputField("image_link", getTagValue(org, "logoURL"))
  s += FIELDSEP + outputField("event_type", "volunteering")
  return s

def getFeedFields(feedinfo):
  s = outputTagValue(feedinfo, "feedID")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "providerID", "feed_providerID")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "providerName", "feed_providerName")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "providerURL", "feed_providerURL")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "description", "feed_description")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "createdDateTime", "feed_createdDateTime")
  return s

def convertToGoogleBaseEventsType(xmldoc, do_printhead):
  s = ""
  recno = 0
  global debug

  feedinfos = xmldoc.getElementsByTagName("FeedInfo")
  if (feedinfos.length != 1):
    print "bad FeedInfo: should only be one section"
    exit
  feedinfo = feedinfos[0]

  if do_printhead:
    global printhead
    printhead = True
    s += outputField("id", "")
    s += FIELDSEP + getFeedFields(feedinfo)
    s += FIELDSEP + getBaseEventRequiredFields(xmldoc, xmldoc)
    s += FIELDSEP + getBaseOtherFields(xmldoc, xmldoc)
    s += FIELDSEP + getDirectMappedField(xmldoc, xmldoc)
    s += FIELDSEP + outputField("location", "")
    s += FIELDSEP + outputField("openended", "")
    s += FIELDSEP + outputField("duration", "")
    s += FIELDSEP + outputField("commitmentHoursPerWeek", "")
    s += FIELDSEP + outputField("event_date_range", "")
    s += RECORDSEP
    printhead = False

  organizations = xmldoc.getElementsByTagName("Organization")
  known_orgs = {}
  for org in organizations:
    id = getTagValue(org, "organizationID")
    if (id != ""):
      known_orgs[id] = org
    
  opportunities = xmldoc.getElementsByTagName("VolunteerOpportunity")
  for opp in opportunities:
    id = getTagValue(opp, "volunteerOpportunityID")
    if (id == ""):
      print "no opportunityID"
      continue
    org_id = getTagValue(opp, "sponsoringOrganizationID")
    if (org_id not in known_orgs):
      print "unknown org_id: " + org_id + ".  skipping opportunity " + id
      continue
    org = known_orgs[org_id]
    opp_locations = opp.getElementsByTagName("location")
    opp_times = opp.getElementsByTagName("dateTimeDuration")
    for opptime in opp_times:
      openended = getTagValue(opptime, "openEnded")
      # event_date_range
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
      startDate = getTagValue(opptime, "startDate")
      startTime = getTagValue(opptime, "startTime")
      endDate = getTagValue(opptime, "endDate")
      endTime = getTagValue(opptime, "endTime")
      tz = getTagValue(opptime, "tzOlsonPath")
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
      if (startDate == ""):
        startDate = "1971-01-01"
        startTime = "00:00:00"
      startend = cvtDateTimeToGoogleBase(startDate, startTime, tz)
      if (endDate != ""):
        startend += "/"
        startend += cvtDateTimeToGoogleBase(endDate, endTime, tz)
      for opploc in opp_locations:
        recno = recno + 1
        if debug:
          s += "--- record %s\n" % (recno)
        locstr = computeLocationField(opploc)
        duration = getTagValue(opptime, "duration")
        commitmentHoursPerWeek = getTagValue(opptime, "commitmentHoursPerWeek")
        locstr = computeLocationField(opploc)
        id = computeStableId(opp, org, locstr, openended, duration,
                             commitmentHoursPerWeek, startend)
        s += outputField("id", id)
        s += FIELDSEP + getFeedFields(feedinfo)
        s += FIELDSEP + getBaseEventRequiredFields(opp, org)
        s += FIELDSEP + getBaseOtherFields(opp, org)
        s += FIELDSEP + getDirectMappedField(opp, org)
        s += FIELDSEP + outputField("location", locstr)
        s += FIELDSEP + outputField("openended", openended)
        s += FIELDSEP + outputField("duration", duration)
        s += FIELDSEP + outputField("commitmentHoursPerWeek", commitmentHoursPerWeek)
        s += FIELDSEP + outputField("event_date_range", startend)
        s += RECORDSEP
  return s

def ftpActivity():
  print ".",

def ftpToBase(ftpinfo, s):
  ftplib = __import__('ftplib')
  StringIO = __import__('StringIO')
  fh = StringIO.StringIO(s)
  host = 'uploads.google.com'
  (user,passwd) = ftpinfo.split(":")
  print "connecting to " + host + " as user " + user + "..."
  ftp = ftplib.FTP(host)
  print ftp.getwelcome()
  ftp.login(user, passwd)
  ftp.storbinary("STOR footprint1.txt", fh, 8192)
  ftp.quit()

from optparse import OptionParser
if __name__ == "__main__":
  sys = __import__('sys')
  parser = OptionParser("usage: %prog [options] sample_data.xml ...")
  parser.set_defaults(debug=False)
  parser.add_option("-d", "--dbg", action="store_true", dest="debug")
  parser.add_option("--ftpinfo", dest="ftpinfo")
  parser.add_option("--fs", "--fieldsep", action="store", dest="fs")
  parser.add_option("--rs", "--recordsep", action="store", dest="rs")
  (options, args) = parser.parse_args(sys.argv[1:])
  if (len(args) == 0):
    parser.print_help()
    exit
  if options.fs != None:
    FIELDSEP = options.fs
  if options.rs != None:
    RECORDSEP = options.rs
  if (options.debug):
    debug = True
    FIELDSEP = "\n"
  do_printhead = True
  s = ""
  for f in args:
    xmldoc = parse_footprint.ParseFootprintXML(f)
    s += convertToGoogleBaseEventsType(xmldoc, do_printhead)
    do_printhead = False   # only print the first time
  if (options.ftpinfo):
    # 'mockingbird', 'ftp2mockingbird')
    ftpToBase(options.ftpinfo, s)
  else:
    print s,

