# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from xml.dom import minidom
import xml_helpers
import re
from datetime import datetime

import dateutil.parser

# pylint: disable-msg=R0915
def parse(s, maxrecs, progress):
  """return FPXML given volunteermatch data"""
  # TODO: progress
  known_elnames = ['feed', 'title', 'subtitle', 'div', 'span', 'updated', 'id', 'link', 'icon', 'logo', 'author', 'name', 'uri', 'email', 'rights', 'entry', 'published', 'g:publish_date', 'g:expiration_date', 'g:event_date_range', 'g:start', 'g:end', 'updated', 'category', 'summary', 'content', 'awb:city', 'awb:country', 'awb:state', 'awb:postalcode', 'g:location', 'g:age_range', 'g:employer', 'g:job_type', 'g:job_industry', 'awb:paid', ]
  xmldoc = xml_helpers.simpleParser(s, known_elnames, progress)

  pubdate = xml_helpers.getTagValue(xmldoc, "created")
  ts = dateutil.parser.parse(pubdate)
  pubdate = ts.strftime("%Y-%m-%dT%H:%M:%S")

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<providerID>104</providerID>'
  s += '<providerName>volunteermatch.org</providerName>'
  s += '<feedID>volunteermatch.org</feedID>'
  s += '<providerURL>http://www.volunteermatch.org/</providerURL>'
  s += '<createdDateTime>%s</createdDateTime>' % (pubdate)
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
      print datetime.now(), "parse_volunteermatch: listing does not have an organization"
      return None

  s += '</Organizations>'
    
  s += '<VolunteerOpportunities>'
  items = xmldoc.getElementsByTagName("listing")
  for item in items[0:maxrecs]:
    s += '<VolunteerOpportunity>'
    s += '<volunteerOpportunityID>%s</volunteerOpportunityID>' % (xml_helpers.getTagValue(item, "key"))

    orgs = item.getElementsByTagName("parent")
    if (orgs.length == 1):
      org = orgs[0]
      s += '<sponsoringOrganizationIDs><sponsoringOrganizationID>%s</sponsoringOrganizationID></sponsoringOrganizationIDs>' % (xml_helpers.getTagValue(org, "key"))
    else:
      s += '<sponsoringOrganizationIDs><sponsoringOrganizationID>0</sponsoringOrganizationID></sponsoringOrganizationIDs>'
      print datetime.now(), "parse_volunteermatch: listing does not have an organization"
      
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
      print datetime.now(), "parse_volunteermatch: number of durations in item != 1"
      return None
        
    commitments = item.getElementsByTagName("commitment")
    l_period = l_duration = ""
    if (commitments.length == 1):
      commitment = commitments[0]
      l_num = xml_helpers.getTagValue(commitment, "num")
      l_duration = xml_helpers.getTagValue(commitment, "duration")
      l_period = xml_helpers.getTagValue(commitment, "period")
      if ((l_duration == "hours") and (l_period == "week")):
        s += '<commitmentHoursPerWeek>' + l_num + '</commitmentHoursPerWeek>'
      elif ((l_duration == "hours") and (l_period == "day")):
        # note: weekdays only
        s += '<commitmentHoursPerWeek>' + str(int(l_num)*5) + '</commitmentHoursPerWeek>'
      elif ((l_duration == "hours") and (l_period == "month")):
        hrs = int(float(l_num)/4.0)
        if hrs < 1: hrs = 1
        s += '<commitmentHoursPerWeek>' + str(hrs) + '</commitmentHoursPerWeek>'
      elif ((l_duration == "hours") and (l_period == "event")):
        # TODO: ignore for now, later compute the endTime if not already provided
        pass
      else:
        print datetime.now(), "parse_volunteermatch: commitment given in units != hours/week: ", l_duration, "per", l_period
        
    s += '</dateTimeDuration></dateTimeDurations>'

    dbaddresses = item.getElementsByTagName("location")
    if (dbaddresses.length != 1):
      print datetime.now(), "parse_volunteermatch: only 1 location supported."
      return None
    dbaddress = dbaddresses[0]
    s += '<locations><location>'
    s += '<streetAddress1>%s</streetAddress1>' % (xml_helpers.getTagValue(dbaddress, "street1"))
    s += '<city>%s</city>' % (xml_helpers.getTagValue(dbaddress, "city"))
    s += '<region>%s</region>' % (xml_helpers.getTagValue(dbaddress, "region"))
    s += '<postalCode>%s</postalCode>' % (xml_helpers.getTagValue(dbaddress, "postalCode"))
    
    geolocs = item.getElementsByTagName("geolocation")
    if (geolocs.length == 1):
      geoloc = geolocs[0]
      s += '<latitude>%s</latitude>' % (xml_helpers.getTagValue(geoloc, "latitude"))
      s += '<longitude>%s</longitude>' % (xml_helpers.getTagValue(geoloc, "longitude"))
    
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

    s += '<skills>%s</skills>' % (xml_helpers.getTagValue(item, "skill"))

    s += '<detailURL>%s</detailURL>' % (xml_helpers.getTagValue(item, "detailURL"))
    s += '<description>%s</description>' % (xml_helpers.getTagValue(item, "description"))

    expires = xml_helpers.getTagValue(item, "expires")
    ts = dateutil.parser.parse(expires)
    expires = ts.strftime("%Y-%m-%dT%H:%M:%S")
    s += '<expires>%s</expires>' % (expires)

    s += '</VolunteerOpportunity>'
    
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'

  #s = re.sub(r'><([^/])', r'>\n<\1', s)
  #print(s)
  return s

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
