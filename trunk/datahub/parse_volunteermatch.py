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
  known_elnames = ['feed', 'title', 'subtitle', 'div', 'span', 'updated', 'id', 'link', 'icon', 'logo', 'author', 'name', 'uri', 'email', 'rights', 'entry', 'published', 'g:publish_date', 'g:expiration_date', 'g:event_date_range', 'g:start', 'g:end', 'updated', 'category', 'summary', 'content', 'awb:city', 'awb:country', 'awb:state', 'awb:postalcode', 'g:location', 'g:age_range', 'g:employer', 'g:job_type', 'g:job_industry', 'awb:paid', ]
  xmldoc = xml_helpers.simpleParser(s, known_elnames)

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<providerID>XXX</providerID>'
  s += '<providerName>volunteermatch.org</providerName>'
  s += '<feedID>volunteermatch.org</feedID>'
  s += '<providerURL>http://www.volunteermatch.org/</providerURL>'
  s += '<createdDateTime>2009-01-01T11:11:11</createdDateTime>'
  s += '<description></description>' 
  s += '</FeedInfo>'

  # hardcoded: Organization
  s += '<Organizations>'
  items = xmldoc.getElementsByTagName("listing")
  if (maxrecs > items.length or maxrecs == -1):
    maxrecs = items.length
    
  for item in items[0:maxrecs]:
    orgs = item.getElementsByTagName("parent")
    if (orgs.length == 1):
      org = orgs[0]
      s += '<Organization>'
      s += '<organizationID>%s</organizationID>' % (xml_helpers.getTagValue(org, "key"))
      s += '<nationalEIN></nationalEIN>'
      s += '<name>%s</name>' % (xml_helpers.getTagValue(org, "name"))
      s += '<missionStatement></missionStatement>'
      s += '<description></description>'
      s += '<location><city></city><region></region><postalCode></postalCode></location>'
      s += '<organizationURL>%s</organizationURL>' % (xml_helpers.getTagValue(org, "URL"))
      s += '<donateURL></donateURL>'
      s += '<logoURL></logoURL>'
      s += '<detailURL>%s</detailURL>' % (xml_helpers.getTagValue(org, "detailURL"))
      s += '</Organization>'
    else:
      print "parse_volunteermatch: listing does not have an organization"

  s += '</Organizations>'
    
  s += '<VolunteerOpportunities>'
  items = xmldoc.getElementsByTagName("listing")
  for item in items[0:maxrecs]:
    s += '<VolunteerOpportunity>'
    s += '<volunteerOpportunityID>%s</volunteerOpportunityID>' % (xml_helpers.getTagValue(item, "key"))

    orgs = item.getElementsByTagName("parent")
    if (orgs.length == 1):
      org = orgs[0]
      s += '<sponsoringOrganizationID>%s</sponsoringOrganizationID>' % (xml_helpers.getTagValue(org, "key"))
    else:
      s += '<sponsoringOrganizationID>0</sponsoringOrganizationID>'
      print "parse_volunteermatch: listing does not have an organization"
      
    s += '<title>%s</title>' % (xml_helpers.getTagValue(item, "title"))

    s += '<volunteersNeeded>-8888</volunteersNeeded>'

    s += '<dateTimeDurations><dateTimeDuration>'
    durations = xml_helpers.getChildrenByTagName(item, "duration")
    if (len(durations) == 1):
      duration = durations[0]
      ongoing = duration.getAttribute("ongoing")
      if (ongoing == 'true'):
        s += '<openEnded>Yes</openEnded>'
      else:
        s += '<openEnded>No</openEnded>'
          
      listingTimes = duration.getElementsByTagName("listingTime")
      if (listingTimes.length == 1):
        listingTime = listingTimes[0]
        s += '<startTime>%s</startTime>' % (xml_helpers.getTagValue(listingTime, "startTime"))
        s += '<endTime>%s</endTime>' % (xml_helpers.getTagValue(listingTime, "endTime"))
    else:
      print "parse_volunteermatch: number of durations in item != 1"
        
    commitments = item.getElementsByTagName("commitment")
    if (commitments.length == 1):
      commitment = commitments[0]
      l_num = xml_helpers.getTagValue(commitment, "num")
      l_duration = xml_helpers.getTagValue(commitment, "duration")
      l_period = xml_helpers.getTagValue(commitment, "period")
      if ((l_duration == "hours") and (l_period == "week")):
        s += '<commitmentHoursPerWeek>' + l_num + '</commitmentHoursPerWeek>'
      else:
        print "parse_volunteermatch: commitment given in units != hours/week"
        
    s += '</dateTimeDuration></dateTimeDurations>'

    dbaddresses = item.getElementsByTagName("location")
    if (dbaddresses.length != 1):
      print "parse_volunteermatch: only 1 location supported."
      return None
    dbaddress = dbaddresses[0]
    s += '<locations><location>'
    s += '<streetAddress1>%s</streetAddress1>' % (xml_helpers.getTagValue(dbaddress, "street1"))
    s += '<city>%s</city>' % (xml_helpers.getTagValue(dbaddress, "city"))
    s += '<region>%s</region>' % (xml_helpers.getTagValue(dbaddress, "region"))
    s += '<postalCode>%s</postalCode>' % (xml_helpers.getTagValue(dbaddress, "postalCode"))
    s += '</location></locations>'
    
    s += '<audienceTags>'
    audiences = item.getElementsByTagName("audience")
    for audience in audiences:
      type = xml_helpers.getNodeData(audience)
      s += '<audienceTag>%s</audienceTag>' % (type)
    s += '</audienceTags>'

    s += '<categoryTags>'
    categories = item.getElementsByTagName("category")
    for category in categories:
      type = xml_helpers.getNodeData(category)
      s += '<categoryTag>%s</categoryTag>' % (type)
    s += '</categoryTags>'

    s += '<detailURL>%s</detailURL>' % (xml_helpers.getTagValue(item, "detailURL"))
    s += '<description>%s</description>' % (xml_helpers.getTagValue(item, "description"))

    expires = xml_helpers.getTagValue(item, "expires")
    ts = dateutil.parser.parse(expires)
    expires = ts.strftime("%Y-%m-%dT%H:%M:%S")
    s += '<expires>%s</expires>' % (expires)

    s += '</VolunteerOpportunity>'
    
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'

  s = re.sub(r'><([^/])', r'>\n<\1', s)
  print s
  xmldoc = parse_footprint.Parse(s, maxrecs, progress)
  return xmldoc

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
