# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom
import xml_helpers
import parse_footprint
import re
from datetime import datetime

import dateutil.parser

def Parse(s, maxrecs, progress):
  # TODO: progress
  known_elnames = [ 'channel', 'db:abstract', 'db:address', 'db:attendee_count', 'db:categories', 'db:city', 'db:country', 'db:county', 'db:dateTime', 'db:event', 'db:eventType', 'db:guest_total', 'db:host', 'db:latitude', 'db:length', 'db:longitude', 'db:rsvp', 'db:scheduledTime', 'db:state', 'db:street', 'db:title', 'db:venue_name', 'db:zipcode', 'description', 'docs', 'guid', 'item', 'language', 'link', 'pubDate', 'rss', 'title', ]
  xmldoc = xml_helpers.simpleParser(s, known_elnames)

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<providerID>101</providerID>'
  s += '<providerName>usaservice.org</providerName>'
  s += '<feedID>usaservice.org</feedID>'
  s += '<createdDateTime>2008-12-30T14:30:10.5</createdDateTime>' # TODO: get/create real feed date
  s += '<providerURL>http://www.usaservice.org/</providerURL>'
  s += '<description>%s</description>' % (xml_helpers.getTagValue(xmldoc, "description"))
  # TODO: capture ts -- use now?!
  s += '</FeedInfo>'

  # hardcoded: Organization
  s += '<Organizations>'
  s += '<Organization>'
  s += '<organizationID>0</organizationID>'
  s += '<nationalEIN></nationalEIN>'
  s += '<name></name>'
  s += '<missionStatement></missionStatement>'
  s += '<description></description>'
  s += '<location><city></city><region></region><postalCode></postalCode></location>'
  s += '<organizationURL></organizationURL>'
  s += '<donateURL></donateURL>'
  s += '<logoURL></logoURL>'
  s += '<detailURL></detailURL>'
  s += '</Organization>'
  s += '</Organizations>'
    
  s += '<VolunteerOpportunities>'
  items = xmldoc.getElementsByTagName("item")
  if (maxrecs > items.length):
    maxrecs = items.length
  for item in items[0:maxrecs-1]:
    # unmapped: db:rsvp  (seems to be same as link, but with #rsvp at end of url?)
    # unmapped: db:host  (no equivalent?)
    # unmapped: db:county  (seems to be empty)
    # unmapped: attendee_count
    # unmapped: guest_total
    # unmapped: db:title   (dup of title, above)
    s += '<VolunteerOpportunity>'
    s += '<volunteerOpportunityID>%s</volunteerOpportunityID>' % (xml_helpers.getTagValue(item, "guid"))
    # hardcoded: sponsoringOrganizationID
    s += '<sponsoringOrganizationID>0</sponsoringOrganizationID>'
    # hardcoded: volunteerHubOrganizationID
    s += '<volunteerHubOrganizationID>0</volunteerHubOrganizationID>'
    s += '<title>%s</title>' % (xml_helpers.getTagValue(item, "title"))
    s += '<abstract>%s</abstract>' % (xml_helpers.getTagValue(item, "abstract"))
    s += '<volunteersNeeded>-8888</volunteersNeeded>'

    dbscheduledTimes = item.getElementsByTagName("db:scheduledTime")
    if (dbscheduledTimes.length != 1):
      print "parse_usaservice: only 1 db:scheduledTime supported."
      return None
    dbscheduledTime = dbscheduledTimes[0]
    s += '<dateTimeDurations><dateTimeDuration>'
    length = xml_helpers.getTagValue(dbscheduledTime, "db:length")
    if length == "" or length == "-1":
      s += '<openEnded>Yes</openEnded>'
      s += '<duration></duration>'
    else:
      s += '<openEnded>No</openEnded>'
      s += '<duration>P%dH</duration>' % (int(int(length) / 60))
    # hardcoded: commitmentHoursPerWeek
    s += '<commitmentHoursPerWeek>0</commitmentHoursPerWeek>'
    date,time = xml_helpers.getTagValue(dbscheduledTime, "db:dateTime").split(" ")
    s += '<startDate>%s</startDate>' % (date)
    # TODO: timezone???
    s += '<startTime>%s</startTime>' % (time)
    s += '</dateTimeDuration></dateTimeDurations>'

    dbaddresses = item.getElementsByTagName("db:address")
    if (dbaddresses.length != 1):
      print "parse_usaservice: only 1 db:address supported."
      return None
    dbaddress = dbaddresses[0]
    s += '<locations><location>'
    s += '<name>%s</name>' % (xml_helpers.getTagValue(item, "db:venue_name"))
    s += '<streetAddress1>%s</streetAddress1>' % (xml_helpers.getTagValue(dbaddress, "db:street"))
    s += '<city>%s</city>' % (xml_helpers.getTagValue(dbaddress, "db:city"))
    s += '<region>%s</region>' % (xml_helpers.getTagValue(dbaddress, "db:state"))
    s += '<country>%s</country>' % (xml_helpers.getTagValue(dbaddress, "db:country"))
    s += '<postalCode>%s</postalCode>' % (xml_helpers.getTagValue(dbaddress, "db:zipcode"))
    s += '<latitude>%s</latitude>' % (xml_helpers.getTagValue(dbaddress, "db:latitude"))
    s += '<longitude>%s</longitude>' % (xml_helpers.getTagValue(dbaddress, "db:longitude"))
    s += '</location></locations>'

    type = xml_helpers.getTagValue(item, "db:eventType")
    s += '<categoryTags><categoryTag>%s</categoryTag></categoryTags>' % (type)

    s += '<contactName>%s</contactName>' % xml_helpers.getTagValue(item, "db:host")
    s += '<detailURL>%s</detailURL>' % (xml_helpers.getTagValue(item, "link"))
    s += '<description>%s</description>' % (xml_helpers.getTagValue(item, "description"))
    pubdate = xml_helpers.getTagValue(item, "pubDate")
    if re.search("[0-9][0-9] [A-Z][a-z][a-z] [0-9][0-9][0-9][0-9]", pubdate):
      # TODO: parse() is ignoring timzone...
      ts = dateutil.parser.parse(pubdate)
      pubdate = ts.strftime("%Y-%m-%dT%H:%M:%S")
    s += '<lastUpdated>%s</lastUpdated>' % (pubdate)

    s += '</VolunteerOpportunity>'
    
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'

  #s = re.sub(r'><([^/])', r'>\n<\1', s)
  #print s
  xmldoc = parse_footprint.Parse(s, maxrecs, progress)
  return xmldoc

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
