# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom
import xml_helpers
import re
from datetime import datetime
import xml.sax.saxutils

import dateutil.parser

# xml parser chokes on namespaces, and since we don't need them,
# just replace them for simplicity-- note that this also affects
# the code below
def remove_g_namespace(s, progress):
  if progress:
    print datetime.now(),"removing g: namespace..."
  s = re.sub(r'<(/?)g:', r'<\1gg_', s)
  if progress:
    print datetime.now(),"removing awb: namespace..."
  s = re.sub(r'<(/?)awb:', r'<\1awb_', s)
  return s

def addCdataToContent(s, progress):
  # what if CDATA is already used?!
  if progress:
    print datetime.now(),"adding CDATA to <content>..."
  ## yuck: this caused a RAM explosion...
  #rx = re.compile(r'<content( *?[^>]*?)>(.+?)</content>', re.DOTALL)
  #s = re.sub(rx, r'<content\1><![CDATA[\2]]></content>', s)

  s = re.sub(r'<content([^>]+)>', r'<content\1><![CDATA[', s)
  if progress:
    print datetime.now(),"adding ]]> to </content>..."
  s = re.sub(r'</content>', r']]></content>', s)
  if progress:
    print datetime.now(),"done: ",len(s)," bytes"
  return s

# frees memory for main parse
def ParseHelper(instr, maxrecs, progress):
  # TODO: progress
  known_elnames = ['feed', 'title', 'subtitle', 'div', 'span', 'updated', 'id', 'link', 'icon', 'logo', 'author', 'name', 'uri', 'email', 'rights', 'entry', 'published', 'gg_publish_date', 'gg_expiration_date', 'gg_event_date_range', 'gg_start', 'gg_end', 'updated', 'category', 'summary', 'content', 'awb_city', 'awb_country', 'awb_state', 'awb_postalcode', 'gg_location', 'gg_age_range', 'gg_employer', 'gg_job_type', 'gg_job_industry', 'awb_paid', ]
  # takes forever
  #xmldoc = xml_helpers.simpleParser(s, known_elnames, progress)

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<feedID>idealist.org</feedID>'
  s += '<providerID>103</providerID>'
  s += '<providerName>idealist.org</providerName>'
  s += '<providerURL>http://www.idealist.org/</providerURL>'
  match = re.search(r'<title>(.+?)</title>', instr, re.DOTALL)
  if match:
    s += '<description>%s</description>' % (match.group(1))
  # TODO: capture ts -- use now?!
  s += '<createdDateTime>2009-01-01T11:11:11</createdDateTime>'
  s += '</FeedInfo>'

  # hardcoded: Organization
  s += '<Organizations>'
  #authors = xmldoc.getElementsByTagName("author")
  organizations = {}
  authors = re.findall(r'<author>.+?</author>', instr, re.DOTALL)
  for i,orgstr in enumerate(authors):
    if progress and i>0 and i%250==0:
      print datetime.now(),": ",i," orgs processed."
    org = xml_helpers.simpleParser(orgstr, known_elnames, False)
    s += '<Organization>'
    s += '<organizationID>%d</organizationID>' % (i+1)
    s += '<nationalEIN></nationalEIN>'
    s += '<guidestarID></guidestarID>'
    name = xml_helpers.getTagValue(org, "name")
    organizations[name] = i+1
    s += '<name>%s</name>' % (organizations[name])
    s += '<missionStatement></missionStatement>'
    s += '<description></description>'
    s += '<location><city></city><region></region><postalCode></postalCode></location>'
    s += '<organizationURL>%s</organizationURL>' % (xml_helpers.getTagValue(org, "uri"))
    s += '<donateURL></donateURL>'
    s += '<logoURL></logoURL>'
    s += '<detailURL></detailURL>'
    s += '</Organization>'
  s += '</Organizations>'
    
  s += '<VolunteerOpportunities>'
  entries = re.findall(r'<entry>.+?</entry>', instr, re.DOTALL)
  #entries = xmldoc.getElementsByTagName("entry")
  #if (maxrecs > entries.length):
  #  maxrecs = entries.length
  #for opp in entries[0:maxrecs-1]:
  for i,oppstr in enumerate(entries):
    if (maxrecs>0 and i>maxrecs):
      break
    xml_helpers.printProgress("opps", progress, i, maxrecs)
    opp = xml_helpers.simpleParser(oppstr, known_elnames, False)
    # unmapped: db:rsvp  (seems to be same as link, but with #rsvp at end of url?)
    # unmapped: db:host  (no equivalent?)
    # unmapped: db:county  (seems to be empty)
    # unmapped: attendee_count
    # unmapped: guest_total
    # unmapped: db:title   (dup of title, above)
    # unmapped: contactName
    s += '<VolunteerOpportunity>'
    id_link = xml_helpers.getTagValue(opp, "id")
    s += '<volunteerOpportunityID>%s</volunteerOpportunityID>' % (id_link)
    orgname = xml_helpers.getTagValue(org, "name")  # ok to be lazy-- no other 'name's in this feed
    s += '<sponsoringOrganizationIDs><sponsoringOrganizationID>%s</sponsoringOrganizationID></sponsoringOrganizationIDs>' % (organizations[orgname])
    # hardcoded: volunteerHubOrganizationID
    s += '<volunteerHubOrganizationIDs><volunteerHubOrganizationID>0</volunteerHubOrganizationID></volunteerHubOrganizationIDs>'
    s += '<title>%s</title>' % (xml_helpers.getTagValue(opp, "title"))
    # lazy: id is the same as the link field...
    s += '<detailURL>%s</detailURL>' % (id_link)
    # lazy: idealist stuffs a div in the content...
    s += '<description>%s</description>' % (xml_helpers.getTagValue(opp, "div"))
    s += '<abstract>%s</abstract>' % (xml_helpers.getTagValue(opp, "summary"))
    pubdate = xml_helpers.getTagValue(opp, "published")
    ts = dateutil.parser.parse(pubdate)
    pubdate = ts.strftime("%Y-%m-%dT%H:%M:%S")
    s += '<lastUpdated>%s</lastUpdated>' % (pubdate)
    s += '<expires>%sT23:59:59</expires>' % (xml_helpers.getTagValue(opp, "gg_expiration_date"))
    dbevents = opp.getElementsByTagName("gg_event_date_range")
    if (dbevents.length != 1):
      print datetime.now(),"parse_idealist: only 1 db:event supported."
      return None
    s += '<locations><location>'
    # yucko: idealist is stored in Google Base, which only has 'location'
    # so we stuff it into the city field, knowing that it'll just get
    # concatenated down the line...
    s += '<city>%s</city>' % (xml_helpers.getTagValue(opp, "gg_location"))
    s += '</location></locations>'
    dbscheduledTimes = opp.getElementsByTagName("gg_event_date_range")
    if (dbscheduledTimes.length != 1):
      print datetime.now(),"parse_usaservice: only 1 gg_event_date_range supported."
      return None
    dbscheduledTime = dbscheduledTimes[0]
    s += '<dateTimeDurations><dateTimeDuration>'
    s += '<openEnded>No</openEnded>'
    # ignore duration
    # ignore commitmentHoursPerWeek
    tempdate = xml_helpers.getTagValue(dbscheduledTime, "gg_start")
    ts = dateutil.parser.parse(tempdate)
    tempdate = ts.strftime("%Y-%m-%d")
    s += '<startDate>%s</startDate>' % (tempdate)
    tempdate = xml_helpers.getTagValue(dbscheduledTime, "gg_end")
    ts = dateutil.parser.parse(tempdate)
    tempdate = ts.strftime("%Y-%m-%d")
    s += '<endDate>%s</endDate>' % (tempdate)
    # TODO: timezone???
    s += '</dateTimeDuration></dateTimeDurations>'
    s += '<categoryTags>'
    # proper way is too slow...
    #cats = opp.getElementsByTagName("category")
    #for i,cat in enumerate(cats):
    #  s += '<categoryTag>%s</categoryTag>' % (cat.attributes["label"].value)
    catstrs = re.findall(r'<category term=(["][^"]+["])', oppstr, re.DOTALL)
    for cat in catstrs:
      s += "<categoryTag>" + xml.sax.saxutils.escape(cat) + "</categoryTag>"
    s += '</categoryTags>'
    age_range = xml_helpers.getTagValue(opp, "gg_age_range")
    if re.match(r'and under|Families', age_range):
      s += '<minimumAge>0</minimumAge>'
    elif re.match(r'Teens', age_range):
      s += '<minimumAge>13</minimumAge>'
    elif re.match(r'Adults', age_range):
      s += '<minimumAge>18</minimumAge>'
    elif re.match(r'Seniors', age_range):
      s += '<minimumAge>65</minimumAge>'
    s += '</VolunteerOpportunity>'
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'

  if progress:
    print datetime.now(),"done generating footprint XML-- adding newlines..."
  s = re.sub(r'><([^/])', r'>\n<\1', s)
  #print s
  return s

def Parse(s, maxrecs, progress):
  s = addCdataToContent(s, progress)
  s = remove_g_namespace(s, progress)
  s = ParseHelper(s, maxrecs, progress)
  return s

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
