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

# <VolunteerOpportunity>
# <LocalID>7702:76159:578625</LocalID>
# <AffiliateID>7702</AffiliateID>
# <OrgLocalID>578625</OrgLocalID>
# <Categories>
# <Category><CategoryID>5</CategoryID></Category>
# <Category><CategoryID>6</CategoryID></Category>
# </Categories>
# <DateListed>2008-07-08</DateListed>
# <OpportunityType><OpportunityTypeID>1</OpportunityTypeID></OpportunityType>
# <Title>HHSB Arts &amp; Crafts (FX)</Title>
# <DetailURL>http://www.HandsOnMiami.org/projects/viewProject.php?_mode=occurrenceView&amp;_action=load&amp;ixActivity=76159&amp;_clearFlag=specialevent&amp;_clearFlag=course&amp;ixFeed=6</DetailURL>
# <Description>Join HOM at the Hebrew Home of South Beach for a fun morning of arts and crafts with the seniors who reside at the home.  Volunteers and residents will enjoy sweets. Spanish-speaking volunteers especially welcome.  Family-friendly: minimum age with an adult is 11.   </Description>
# <LogoURL>http://www.HandsOnMiami.org/uploaded_files/deliverFile.php/hom_140x140.gif</LogoURL>
# <LocationClassifications><LocationClassification><LocationClassificationID>1</LocationClassificationID></LocationClassification></LocationClassifications>
# <Locations>
# <Location>
# <Address1>Hebrew Home of South Beach</Address1>
# <Address2>320 Collins Avenue</Address2>
# <City>Miami Beach</City>
# <StateOrProvince>FL</StateOrProvince>
# <ZipOrPostalCode>33139</ZipOrPostalCode>
# <Country>USA</Country>
# </Location>
# </Locations>
# <OpportunityDates>
# <OpportunityDate>
# <StartDate>2008-08-09</StartDate>
# <EndDate>2008-08-09</EndDate>
# <StartTime>10:00:00</StartTime>
# <EndTime>11:30:00</EndTime>
# </OpportunityDate>
# <OpportunityDate>
# <StartDate>2008-08-23</StartDate>
# <EndDate>2008-08-23</EndDate>
# <StartTime>10:00:00</StartTime>
# <EndTime>11:30:00</EndTime>
# </OpportunityDate>
# </OpportunityDates>
# 
# <SponsoringOrganizations>
# <SponsoringOrganization>
# <Name>Hebrew Home of South Beach</Name>
# <Description>Hebrew Home of South Beach; Residential facility managed by D.O.S. Health Care </Description>
# <Country>USA</Country>
# <Phone>305-672-6464</Phone>
# <Extension>220</Extension>
# </SponsoringOrganization>
# </SponsoringOrganizations>
# </VolunteerOpportunity>

from xml.dom import minidom
import xml_helpers as xmlh
import re
import parse_footprint
from datetime import datetime

#def ParseFPXML(instr, maxrecs, progress):
#  instr = re.sub(r'<providerName>.+?</providerName>',
#                 r'<providerName>handsonnetwork</providerName>', instr)
#  instr = re.sub(r'<providerID>.+?</providerID>', 
#                 r'<providerID>102</providerID>', instr)
#  return parse_footprint.Parse(instr, maxrecs, progress)

def Parse(instr, maxrecs, progress):
  if progress:
    print datetime.now(),"parse_handsonnetwork.Parse: starting parse..."
  known_elnames = [
    'Address1', 'Address2', 'AffiliateID', 'Categories', 'Category', 'City',
    'Country', 'DateListed', 'Description', 'DetailURL', 'EndDate', 'EndTime',
    'Extension', 'LocalID', 'Location', 'LocationClassifications',
    'Locations', 'LogoURL', 'Name', 'OpportunityDate', 'OpportunityDates',
    'OpportunityType', 'OrgLocalID', 'Phone', 'SponsoringOrganization',
    'SponsoringOrganizations', 'StartDate', 'StartTime', 'StateOrProvince',
    'Title', 'VolunteerOpportunity', 'ZipOrPostalCode'
    ]

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<providerID>102</providerID>'
  s += '<providerName>handsonnetwork.org</providerName>'
  s += '<feedID>handsonnetwork.org</feedID>'
  # TODO: get/create real feed date
  s += '<createdDateTime>2008-12-30T14:30:10.5</createdDateTime>'
  s += '<providerURL>http://www.handsonnetwork.org/</providerURL>'
  s += '<description></description>'
  # TODO: capture ts -- use now?!
  s += '</FeedInfo>'

  # hardcoded: Organization
  s += '<Organizations>'
  sponsor_ids = {}
  sponsorstrs = re.findall(
    r'<SponsoringOrganization>.+?</SponsoringOrganization>', instr, re.DOTALL)
  for i,orgstr in enumerate(sponsorstrs):
    if progress and i>0 and i%250==0:
      print datetime.now(),": ",i," orgs processed."
    org = xmlh.simpleParser(orgstr, known_elnames, False)
    #sponsors = xmldoc.getElementsByTagName("SponsoringOrganization")
    #for i,org in enumerate(sponsors):
    s += '<Organization>'
    name = xmlh.getTagValue(org, "Name")
    desc = xmlh.getTagValue(org, "Description")
    s += '<organizationID>%d</organizationID>' % (i+1)
    s += '<nationalEIN></nationalEIN>'
    s += '<name>%s</name>' % (xmlh.getTagValue(org, "Name"))
    s += '<missionStatement></missionStatement>'
    s += '<description>%s</description>' % \
        (xmlh.getTagValue(org, "Description"))
    # unmapped: Email
    # unmapped: Phone
    # unmapped: Extension
    s += '<location>'
    #s += '<city>%s</city>' % (xmlh.getTagValue(org, "City"))
    #s += '<region>%s</region>' % (xmlh.getTagValue(org, "State"))
    #s += '<postalCode>%s</postalCode>' % \
    #   (xmlh.getTagValue(org, "PostalCode"))
    s += '<country>%s</country>' % (xmlh.getTagValue(org, "Country"))
    s += '</location>'
    s += '<organizationURL>%s</organizationURL>' % \
        (xmlh.getTagValue(org, "URL"))
    s += '<donateURL></donateURL>'
    s += '<logoURL></logoURL>'
    s += '<detailURL></detailURL>'
    s += '</Organization>'
    sponsor_ids[name+desc] = i+1
    
  s += '</Organizations>'
    
  s += '<VolunteerOpportunities>'
  #items = xmldoc.getElementsByTagName("VolunteerOpportunity")
  #if (maxrecs > items.length):
  #  maxrecs = items.length
  #for item in items[0:maxrecs-1]:
  if progress:
    print datetime.now(),"finding VolunteerOpportunities..."
  opps = re.findall(r'<VolunteerOpportunity>.+?</VolunteerOpportunity>',
                    instr, re.DOTALL)
  totrecs = 0
  for i,oppstr in enumerate(opps):
    if (maxrecs>0 and i>maxrecs):
      break
    xmlh.printProgress("opps", progress, i, maxrecs)
    opp = xmlh.simpleParser(oppstr, known_elnames, False)
    orgs = opp.getElementsByTagName("SponsoringOrganization")
    name = xmlh.getTagValue(orgs[0], "Name")
    desc = xmlh.getTagValue(orgs[0], "Description")
    sponsor_id = sponsor_ids[name+desc]
    oppdates = opp.getElementsByTagName("OpportunityDate")
    if (oppdates == None or oppdates.count == 0):
      oppdates = [ None ]
    else: 
      # unmapped: LogoURL
      # unmapped: OpportunityTypeID   (categoryTag?)
      # unmapped: LocationClassificationID (flatten)
      datestr_pre = xmlh.outputVal('volunteerOpportunityID', opp, "LocalID")
      datestr_pre = xmlh.outputPlural('sponsoringOpportunityID', sponsor_id)
      # unmapped: OrgLocalID
      datestr_pre = xmlh.outputPluralNode('volunteerHubOrganizationID', opp,
                                         "AffiliateID")
      datestr_pre = xmlh.outputNode('title', opp, "Title")
      datestr_pre += '<abstract></abstract>'
      datestr_pre += '<volunteersNeeded>-8888</volunteersNeeded>'
      
      locations = opp.getElementsByTagName("Location")
      if (locations.length != 1):
        print datetime.now(),"parse_handsonnetwork: only 1 location supported."
        return None
      loc = locations[0]
      datestr_post = '<locations><location>'
      # yuck, uses address1 for venue name... sometimes...
      #no way to detect: presence of numbers?
      datestr_post += xmlh.outputNode('streetAddress1', loc, "Address1")
      datestr_post += xmlh.outputNode('streetAddress2', loc, "Address2")
      datestr_post += xmlh.outputNode('city', loc, "City")
      datestr_post += xmlh.outputNode('region', loc, "State")
      datestr_post += xmlh.outputNode('country', loc, "Country")
      datestr_post += xmlh.outputNode('postalCode', loc, "ZipOrPostalCode")
      # no equivalent: latitude, longitude
      datestr_post += '</location></locations>'
      
      datestr_post += xmlh.outputNode('detailURL', opp, "DetailURL")
      datestr_post += xmlh.outputNode('description', opp, "Description")
      datestr_post += xmlh.outputVal('lastUpdated', opp,
                 '%sT00:00:00' % (xmlh.getTagValue(opp, "DateListed")))
       
      oppcount = 0
      datetimedur = ''
      for oppdate in oppdates:
        oppcount = oppcount + 1
        if progress:
          totrecs = totrecs + 1
          if totrecs%250==0:
            print datetime.now(),": ",totrecs," records generated."
  
        datetimedur += '<dateTimeDuration>'
        if oppdate == None:
          datetimedur += '<openEnded>Yes</openEnded>'
        else:
          datetimedur += '<openEnded>No</openEnded>'
          # hardcoded: commitmentHoursPerWeek
          datetimedur += '<commitmentHoursPerWeek>0</commitmentHoursPerWeek>'
          # TODO: timezone
          datetimedur += '<startDate>%s</startDate>' % (xmlh.getTagValue(oppdate, "StartDate"))
          datetimedur += '<endDate>%s</endDate>' % (xmlh.getTagValue(oppdate, "EndDate"))
          datetimedur += '<startTime>%s</startTime>' % (xmlh.getTagValue(oppdate, "StartTime"))
          datetimedur += '<endTime>%s</endTime>' % (xmlh.getTagValue(oppdate, "EndTime"))
        datetimedur += '</dateTimeDuration>'
        
      if oppcount == 0: # insert an open ended datetimeduration
        datetimedur = '<dateTimeDuration><openEnded>'
        datetimedur += 'Yes</openEnded></dateTimeDuration>'
        
      s += '<VolunteerOpportunity>'
      s += datestr_pre
      s += '<dateTimeDurations>';
      s += datetimedur
      s += '</dateTimeDurations>';
      s += datestr_post
      s += '</VolunteerOpportunity>'
    
  if progress:
    print datetime.now(),"done with VolunteerOpportunities..."
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'
  s = re.sub(r'><([^/])', r'>\n<\1', s)
  if progress:
    print datetime.now(),"parse_handsonnetwork.Parse: done."
  return s

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
