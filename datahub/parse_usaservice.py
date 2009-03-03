# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom
import xml_helpers
import re
from datetime import datetime

import dateutil.parser

def Parse(instr, maxrecs, progress):
  # TODO: progress
  known_elnames = [ 'channel', 'db:abstract', 'db:address', 'db:attendee_count', 'db:categories', 'db:city', 'db:country', 'db:county', 'db:dateTime', 'db:event', 'db:eventType', 'db:guest_total', 'db:host', 'db:latitude', 'db:length', 'db:longitude', 'db:rsvp', 'db:scheduledTime', 'db:state', 'db:street', 'db:title', 'db:venue_name', 'db:zipcode', 'description', 'docs', 'guid', 'item', 'language', 'link', 'pubDate', 'rss', 'title', ]

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
  s += '<description>Syndicated events</description>'
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

  instr = re.sub(r'<(/?db):', r'<\1_', instr)
  for i,line in enumerate(instr.splitlines()):
    if (maxrecs>0 and i>maxrecs):
      break
    if progress and i>0 and i%100==0:
      print datetime.now(),": ",i,"opps processed of",maxrecs
    item = xml_helpers.simpleParser(line, known_elnames, progress=False)

    # unmapped: db_rsvp  (seems to be same as link, but with #rsvp at end of url?)
    # unmapped: db_host  (no equivalent?)
    # unmapped: db_county  (seems to be empty)
    # unmapped: attendee_count
    # unmapped: guest_total
    # unmapped: db_title   (dup of title, above)
    s += '<VolunteerOpportunity>'
    s += '<volunteerOpportunityID>%s</volunteerOpportunityID>' % (xml_helpers.getTagValue(item, "guid"))
    # hardcoded: sponsoringOrganizationID
    s += '<sponsoringOrganizationID>0</sponsoringOrganizationID>'
    # hardcoded: volunteerHubOrganizationID
    s += '<volunteerHubOrganizationID>0</volunteerHubOrganizationID>'
    s += '<title>%s</title>' % (xml_helpers.getTagValue(item, "title"))
    s += '<abstract>%s</abstract>' % (xml_helpers.getTagValue(item, "abstract"))
    s += '<volunteersNeeded>-8888</volunteersNeeded>'

    dbscheduledTimes = item.getElementsByTagName("db_scheduledTime")
    if (dbscheduledTimes.length != 1):
      print datetime.now(),"parse_usaservice: only 1 db_scheduledTime supported."
      return None
    dbscheduledTime = dbscheduledTimes[0]
    s += '<dateTimeDurations><dateTimeDuration>'
    length = xml_helpers.getTagValue(dbscheduledTime, "db_length")
    if length == "" or length == "-1":
      s += '<openEnded>Yes</openEnded>'
      s += '<duration></duration>'
    else:
      s += '<openEnded>No</openEnded>'
      s += '<duration>P%dH</duration>' % (int(int(length) / 60))
    # hardcoded: commitmentHoursPerWeek
    s += '<commitmentHoursPerWeek>0</commitmentHoursPerWeek>'
    date,time = xml_helpers.getTagValue(dbscheduledTime, "db_dateTime").split(" ")
    s += '<startDate>%s</startDate>' % (date)
    # TODO: timezone???
    s += '<startTime>%s</startTime>' % (time)
    s += '</dateTimeDuration></dateTimeDurations>'

    dbaddresses = item.getElementsByTagName("db_address")
    if (dbaddresses.length != 1):
      print datetime.now(),"parse_usaservice: only 1 db_address supported."
      return None
    dbaddress = dbaddresses[0]
    s += '<locations><location>'
    s += '<name>%s</name>' % (xml_helpers.getTagValue(item, "db_venue_name"))
    s += '<streetAddress1>%s</streetAddress1>' % (xml_helpers.getTagValue(dbaddress, "db_street"))
    s += '<city>%s</city>' % (xml_helpers.getTagValue(dbaddress, "db_city"))
    s += '<region>%s</region>' % (xml_helpers.getTagValue(dbaddress, "db_state"))
    s += '<country>%s</country>' % (xml_helpers.getTagValue(dbaddress, "db_country"))
    s += '<postalCode>%s</postalCode>' % (xml_helpers.getTagValue(dbaddress, "db_zipcode"))
    s += '<latitude>%s</latitude>' % (xml_helpers.getTagValue(dbaddress, "db_latitude"))
    s += '<longitude>%s</longitude>' % (xml_helpers.getTagValue(dbaddress, "db_longitude"))
    s += '</location></locations>'

    type = xml_helpers.getTagValue(item, "db_eventType")
    s += '<categoryTags><categoryTag>%s</categoryTag></categoryTags>' % (type)

    s += '<contactName>%s</contactName>' % xml_helpers.getTagValue(item, "db_host")
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
  return s

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
