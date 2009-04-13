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
#
# key     status  description     title   creation_time   quality_score   id      listing_xml     start_date
# 2002    50.NEW  Help clean up the neighborhood .        Logan Circle Cleanup    2009-03-27 19:16:48.779077      1.0     fc0917845283fe0969432877615eb4f3     <VolunteerOpportunity><title>Logan Circle Cleanup</title><description>Help clean up the neighborhood .</description><skills>Wear closed toe shoes and sturdy clothing.</skills><minimumAge>0</minimumAge><detailURL></detailURL><locations><location><name>Logan circle</name><city>washington</city><region></region><postalCode></postalCode><country>US</country><latitude>38.9127600</latitude><longitude>-77.0272440</longitude></location></locations><dateTimeDurations><dateTimeDuration><openEnded>Yes</openEnded><commitmentHoursPerWeek>0</commitmentHoursPerWeek></dateTimeDuration></dateTimeDurations></VolunteerOpportunity>      2009-03-27

from xml.dom import minidom
import xml_helpers
import re
import parse_footprint
from datetime import datetime

known_elnames = [ 'FeedInfo', 'FootprintFeed', 'Organization', 'Organizations', 'VolunteerOpportunities', 'VolunteerOpportunity', 'abstract', 'audienceTag', 'audienceTags', 'categoryTag', 'categoryTags', 'city', 'commitmentHoursPerWeek', 'contactEmail', 'contactName', 'contactPhone', 'country', 'createdDateTime', 'dateTimeDuration', 'dateTimeDurationType', 'dateTimeDurations', 'description', 'detailURL', 'directions', 'donateURL', 'duration', 'email', 'endDate', 'endTime', 'expires', 'fax', 'feedID', 'guidestarID', 'iCalRecurrence', 'language', 'latitude', 'lastUpdated', 'location', 'locationType', 'locations', 'logoURL', 'longitude', 'minimumAge', 'missionStatement', 'name', 'nationalEIN', 'openEnded', 'organizationID', 'organizationURL', 'paid', 'phone', 'postalCode', 'providerID', 'providerName', 'providerURL', 'region', 'schemaVersion', 'sexRestrictedEnum', 'sexRestritedTo', 'skills', 'sponsoringOrganizationID', 'startDate', 'startTime', 'streetAddress1', 'streetAddress2', 'streetAddress3', 'title', 'tzOlsonPath', 'virtual', 'volunteerHubOrganizationID', 'volunteerOpportunityID', 'volunteersFilled', 'volunteersSlots', 'volunteersNeeded', 'yesNoEnum', ]

# pylint: disable-msg=R0915
def parse(instr, maxrecs, progress):
  """return FPXML given FP user postings data"""
  # ignore unapproved opportunities
  instr = re.sub(r'^.+REJECTED\t.+$', r'', instr)

  if progress:
    print datetime.now(), "parse_userpostings.Parse: starting parse..."

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<providerID>108</providerID>'
  s += '<providerName>footprint</providerName>'
  s += '<feedID>footprint</feedID>'
  s += '<createdDateTime>%s</createdDateTime>' % xml_helpers.current_ts()
  s += '<providerURL>http://sites.google.com/site/footprintorg/</providerURL>'
  s += '<description></description>'
  # TODO: capture ts -- use now?!
  s += '</FeedInfo>'

  # hardcoded: Organization
  s += '<Organizations>'
  sponsor_ids = {}
  sponsorstrs = re.findall(r'<SponsoringOrganization>.+?</SponsoringOrganization>', instr, re.DOTALL)
  for i,orgstr in enumerate(sponsorstrs):
    if progress and i > 0 and i % 250 == 0:
      print datetime.now(), ": ", i, " orgs processed."
    org = xml_helpers.simple_parser(orgstr, known_elnames, False)
    #sponsors = xmldoc.getElementsByTagName("SponsoringOrganization")
    #for i,org in enumerate(sponsors):
    s += '<Organization>'
    name = xml_helpers.get_tag_val(org, "Name")
    desc = xml_helpers.get_tag_val(org, "Description")
    s += '<organizationID>%d</organizationID>' % (i+1)
    s += '<nationalEIN></nationalEIN>'
    s += '<name>%s</name>' % (xml_helpers.get_tag_val(org, "Name"))
    s += '<missionStatement></missionStatement>'
    s += '<description>%s</description>' % (xml_helpers.get_tag_val(org, "Description"))
    # unmapped: Email
    # unmapped: Phone
    # unmapped: Extension
    s += '<location>'
    #s += '<city>%s</city>' % (xml_helpers.get_tag_val(org, "City"))
    #s += '<region>%s</region>' % (xml_helpers.get_tag_val(org, "State"))
    #s += '<postalCode>%s</postalCode>' % (xml_helpers.get_tag_val(org, "PostalCode"))
    s += '<country>%s</country>' % (xml_helpers.get_tag_val(org, "Country"))
    s += '</location>'
    s += '<organizationURL>%s</organizationURL>' % (xml_helpers.get_tag_val(org, "URL"))
    s += '<donateURL></donateURL>'
    s += '<logoURL></logoURL>'
    s += '<detailURL></detailURL>'
    s += '</Organization>'
    sponsor_ids[name+desc] = i+1
  s += '</Organizations>'
    
  s += '<VolunteerOpportunities>'
  if progress:
    print datetime.now(), "finding VolunteerOpportunities..."
  opps = re.findall(r'<VolunteerOpportunity>.+?</VolunteerOpportunity>', instr, re.DOTALL)
  totrecs = 0
  for i,oppstr in enumerate(opps):
    if (maxrecs>0 and i>maxrecs):
      break
    xml_helpers.print_progress("opps", progress, i, maxrecs)
    opp = xml_helpers.simple_parser(oppstr, known_elnames, False)
    orgs = opp.getElementsByTagName("SponsoringOrganization")
    if orgs:
        name = xml_helpers.get_tag_val(orgs[0], "Name")
        desc = xml_helpers.get_tag_val(orgs[0], "Description")
        sponsor_id = sponsor_ids[name+desc]
    else:
        name = ""
        desc = ""
        sponsor_id = 0
    oppdates = opp.getElementsByTagName("OpportunityDate")
    if (oppdates == None or oppdates.count == 0):
      oppdates = [ None ]
    else: 
      # unmapped: LogoURL
      # unmapped: OpportunityTypeID   (categoryTag?)
      # unmapped: LocationClassificationID (flatten)
      outstr_for_all_dates_pre = '<volunteerOpportunityID>%s</volunteerOpportunityID>' % (xml_helpers.get_tag_val(opp, "LocalID"))
      outstr_for_all_dates_pre += '<sponsoringOrganizationIDs><sponsoringOrganizationID>%s</sponsoringOrganizationID></sponsoringOrganizationIDs>' % (sponsor_id)
        # unmapped: OrgLocalID
      outstr_for_all_dates_pre += '<volunteerHubOrganizationIDs><volunteerHubOrganizationID>%s</volunteerHubOrganizationID></volunteerHubOrganizationIDs>' % (xml_helpers.get_tag_val(opp, "AffiliateID"))
      outstr_for_all_dates_pre += '<title>%s</title>' % (xml_helpers.get_tag_val(opp, "Title"))
      outstr_for_all_dates_pre += '<abstract></abstract>'
      outstr_for_all_dates_pre += '<volunteersNeeded>-8888</volunteersNeeded>'
      
      locations = opp.getElementsByTagName("location")
      if (locations.length != 1):
        print datetime.now(), "parse_userpostings: only 1 location supported."
        return None
      loc = locations[0]
      outstr_for_all_dates_post = '<locations><location>'
        # yuck, uses address1 for venue name... sometimes... no way to detect: presence of numbers?
      outstr_for_all_dates_post += '<streetAddress1>%s</streetAddress1>' % (xml_helpers.get_tag_val(loc, "Address1"))
      outstr_for_all_dates_post += '<streetAddress2>%s</streetAddress2>' % (xml_helpers.get_tag_val(loc, "Address2"))
      outstr_for_all_dates_post += '<city>%s</city>' % (xml_helpers.get_tag_val(loc, "city"))
      outstr_for_all_dates_post += '<region>%s</region>' % (xml_helpers.get_tag_val(loc, "region"))
      outstr_for_all_dates_post += '<country>%s</country>' % (xml_helpers.get_tag_val(loc, "country"))
      outstr_for_all_dates_post += '<postalCode>%s</postalCode>' % (xml_helpers.get_tag_val(loc, "postalCode"))
      outstr_for_all_dates_post += '<latitude>%s</latitude>' % (xml_helpers.get_tag_val(loc, "latitude"))
      outstr_for_all_dates_post += '<longitude>%s</longitude>' % (xml_helpers.get_tag_val(loc, "longitude"))
        # no equivalent: latitude, longitude
      outstr_for_all_dates_post += '</location></locations>'
      
      outstr_for_all_dates_post += '<detailURL>%s</detailURL>' % (xml_helpers.get_tag_val(opp, "DetailURL"))
      outstr_for_all_dates_post += '<description>%s</description>' % (xml_helpers.get_tag_val(opp, "Description"))
      outstr_for_all_dates_post += '<lastUpdated>%sT00:00:00</lastUpdated>' % (xml_helpers.get_tag_val(opp, "DateListed"))
       
      oppcount = 0
      dtds = ''
      for oppdate in oppdates:
        oppcount = oppcount + 1
        if progress:
          totrecs = totrecs + 1
          if totrecs % 250 == 0:
            print datetime.now(), ": ", totrecs, " records generated."
  
        dtds += '<dateTimeDuration>'
        if oppdate == None:
          dtds += '<openEnded>Yes</openEnded>'
        else:
          dtds += '<openEnded>No</openEnded>'
          # hardcoded: commitmentHoursPerWeek
          dtds += '<commitmentHoursPerWeek>0</commitmentHoursPerWeek>'
          # TODO: timezone
          dtds += '<startDate>%s</startDate>' % (xml_helpers.get_tag_val(oppdate, "startDate"))
          dtds += '<endDate>%s</endDate>' % (xml_helpers.get_tag_val(oppdate, "endDate"))
          dtds += '<startTime>%s</startTime>' % (xml_helpers.get_tag_val(oppdate, "startTime"))
          dtds += '<endTime>%s</endTime>' % (xml_helpers.get_tag_val(oppdate, "endTime"))
        dtds += '</dateTimeDuration>'
        
      if oppcount == 0: # insert an open ended datetimeduration
        dtds = '<dateTimeDuration><openEnded>Yes</openEnded></dateTimeDuration>'
        
      s += '<VolunteerOpportunity>'
      s += outstr_for_all_dates_pre
      s += '<dateTimeDurations>';
      s += dtds
      s += '</dateTimeDurations>';
      s += outstr_for_all_dates_post
      s += '</VolunteerOpportunity>'
    
  if progress:
    print datetime.now(), "done with VolunteerOpportunities..."
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'
  s = re.sub(r'><([^/])', r'>\n<\1', s)
  print s
  if progress:
    print datetime.now(), "parse_userpostings.Parse: done."
  return s

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
