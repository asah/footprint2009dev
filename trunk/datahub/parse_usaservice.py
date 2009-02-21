# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.parsers.expat import ExpatError
from xml.dom import minidom
import xml_helpers
import parse_footprint
import re

def Parse(s, maxrecs):
  xmldoc = xml_helpers.simpleParser(s, known_elnames)

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<feedID>usaservice.org</feedID>'
  s += '<providerID>101</providerID>'
  s += '<providerName>usaservice.org</providerName>'
  s += '<providerURL>http://www.usaservice.org/</providerURL>'
  s += '<description>%s</description>' % (xml_helpers.getTagValue(xmldoc, "description"))
  # TODO: capture ts -- use now?!
  s += '<createdDateTime>2009-01-01T11:11:11</createdDateTime>'
  s += '</FeedInfo>'

  # hardcoded: Organization
  s += '<Organizations>'
  s += '<Organization>'
  s += '<organizationID>0</organizationID>'
  s += '<nationalEIN>0</nationalEIN>'
  s += '<guidestarID>0</guidestarID>'
  s += '<name></name>'
  s += '<missionStatement></missionStatement>'
  s += '<description></description>'
  s += '<location><city>Berkeley</city><region>CA</region><postalCode>94704</postalCode></location>'
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
    s += '<detailURL>%s</detailURL>' % (xml_helpers.getTagValue(item, "link"))
    s += '<description>%s</description>' % (xml_helpers.getTagValue(item, "description"))
    s += '<lastUpdated>%s</lastUpdated>' % (xml_helpers.getTagValue(item, "pubDate"))
    dbevents = item.getElementsByTagName("db:event")
    if (dbevents.length != 1):
      print "parse_usaservice: only 1 db:event supported."
      return None
    dbevent = dbevents[0]
    s += '<abstract>%s</abstract>' % (xml_helpers.getTagValue(item, "abstract"))
    # hardcoded: volunteersNeeded
    s += '<volunteersNeeded>-8888</volunteersNeeded>'
    s += '<contactName>%s</contactName>' % xml_helpers.getTagValue(item, "db:host")
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
    type = xml_helpers.getTagValue(item, "db:eventType")
    s += '<categoryTags><categoryTag>%s</categoryTag></categoryTags>' % (type)
    s += '</VolunteerOpportunity>'
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'

  s = re.sub(r'><([^/])', r'>\n<\1', s)
  #print s
  xmldoc = parse_footprint.Parse(s, maxrecs)
  return xmldoc

known_elnames = {
  'channel': 1,
  'db:abstract': 1,
  'db:address': 1,
  'db:attendee_count': 1,
  'db:categories': 1,
  'db:city': 1,
  'db:country': 1,
  'db:county': 1,
  'db:dateTime': 1,
  'db:event': 1,
  'db:eventType': 1,
  'db:guest_total': 1,
  'db:host': 1,
  'db:latitude': 1,
  'db:length': 1,
  'db:longitude': 1,
  'db:rsvp': 1,
  'db:scheduledTime': 1,
  'db:state': 1,
  'db:street': 1,
  'db:title': 1,
  'db:venue_name': 1,
  'db:zipcode': 1,
  'description': 1,
  'docs': 1,
  'guid': 1,
  'item': 1,
  'language': 1,
  'link': 1,
  'pubDate': 1,
  'rss': 1,
  'title': 1,
  }

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
