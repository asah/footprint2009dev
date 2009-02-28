# Copyright 2009 Google Inc.  All Rights Reserved.
#

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
import xml_helpers
import parse_footprint
import re
from datetime import datetime

def ParseHelper(instr, maxrecs, progress):
  known_elnames = [ 'Address1', 'Address2', 'AffiliateID', 'Categories', 'Category', 'City', 'Country', 'DateListed', 'Description', 'DetailURL', 'EndDate', 'EndTime', 'Extension', 'LocalID', 'Location', 'LocationClassifications', 'Locations', 'LogoURL', 'Name', 'OpportunityDate', 'OpportunityDates', 'OpportunityType', 'OrgLocalID', 'Phone', 'SponsoringOrganization', 'SponsoringOrganizations', 'StartDate', 'StartTime', 'StateOrProvince', 'Title', 'VolunteerOpportunity', 'ZipOrPostalCode', ]
  #xmldoc = xml_helpers.simpleParser(instr, known_elnames)

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<providerID>102</providerID>'
  s += '<providerName>handsonnetwork.org</providerName>'
  s += '<feedID>handsonnetwork.org</feedID>'
  s += '<createdDateTime></createdDateTime>'
  s += '<providerURL>http://www.handsonnetwork.org/</providerURL>'
  s += '<description></description>'
  # TODO: capture ts -- use now?!
  s += '</FeedInfo>'

  # hardcoded: Organization
  s += '<Organizations>'
  sponsor_ids = {}
  sponsorstrs = re.findall(r'<SponsoringOrganization>.+?</SponsoringOrganization>', instr, re.DOTALL)
  for i,orgstr in enumerate(sponsorstrs):
    if progress and i>0 and i%250==0:
      print datetime.now(),": ",i," orgs processed."
    org = xml_helpers.simpleParser(orgstr, known_elnames)
    #sponsors = xmldoc.getElementsByTagName("SponsoringOrganization")
    #for i,org in enumerate(sponsors):
    s += '<Organization>'
    name = xml_helpers.getTagValue(org, "Name")
    desc = xml_helpers.getTagValue(org, "Description")
    s += '<organizationID>%d</organizationID>' % (i+1)
    s += '<nationalEIN></nationalEIN>'
    s += '<name>%s</name>' % (xml_helpers.getTagValue(org, "Name"))
    s += '<missionStatement></missionStatement>'
    s += '<description>%s</description>' % (xml_helpers.getTagValue(org, "Description"))
    # unmapped: Email
    # unmapped: Phone
    # unmapped: Extension
    s += '<location>'
    #s += '<city>%s</city>' % (xml_helpers.getTagValue(org, "City"))
    #s += '<region>%s</region>' % (xml_helpers.getTagValue(org, "State"))
    #s += '<postalCode>%s</postalCode>' % (xml_helpers.getTagValue(org, "PostalCode"))
    s += '<country>%s</country>' % (xml_helpers.getTagValue(org, "Country"))
    s += '</location>'
    s += '<organizationURL>%s</organizationURL>' % (xml_helpers.getTagValue(org, "URL"))
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
    print "finding VolunteerOpportunities..."
  opps = re.findall(r'<VolunteerOpportunity>.+?</VolunteerOpportunity>', instr, re.DOTALL)
  totrecs = 0
  for i,oppstr in enumerate(opps):
    if (maxrecs>0 and i>maxrecs):
      break
    if progress and i>0 and i%100==0:
      print datetime.now(),": ",i," opps processed."
    opp = xml_helpers.simpleParser(oppstr, known_elnames)
    orgs = opp.getElementsByTagName("SponsoringOrganization")
    name = xml_helpers.getTagValue(orgs[0], "Name")
    desc = xml_helpers.getTagValue(orgs[0], "Description")
    sponsor_id = sponsor_ids[name+desc]
    oppdates = opp.getElementsByTagName("OpportunityDate")
    if (oppdates == None):
      oppdates = [ None ]
    
    # unmapped: LogoURL
    # unmapped: OpportunityTypeID   (categoryTag?)
    # unmapped: LocationClassificationID (flatten)
    outstr_for_all_dates_pre = '<volunteerOpportunityID>%s</volunteerOpportunityID>' % (xml_helpers.getTagValue(opp, "LocalID"))
    outstr_for_all_dates_pre += '<sponsoringOrganizationID>%s</sponsoringOrganizationID>' % (sponsor_id)
      # unmapped: OrgLocalID
    outstr_for_all_dates_pre += '<volunteerHubOrganizationID>%s</volunteerHubOrganizationID>' % (xml_helpers.getTagValue(opp, "AffiliateID"))
    outstr_for_all_dates_pre += '<title>%s</title>' % (xml_helpers.getTagValue(opp, "Title"))
    outstr_for_all_dates_pre += '<abstract></abstract>'
    outstr_for_all_dates_pre += '<volunteersNeeded>-8888</volunteersNeeded>'
    

    locations = opp.getElementsByTagName("Location")
    if (locations.length != 1):
      print "parse_handsonnetwork: only 1 location supported."
      return None
    loc = locations[0]
    outstr_for_all_dates_post = '<locations><location>'
      # yuck, uses address1 for venue name... sometimes... no way to detect: presence of numbers?
    outstr_for_all_dates_post += '<streetAddress1>%s</streetAddress1>' % (xml_helpers.getTagValue(loc, "Address1"))
    outstr_for_all_dates_post += '<streetAddress2>%s</streetAddress2>' % (xml_helpers.getTagValue(loc, "Address2"))
    outstr_for_all_dates_post += '<city>%s</city>' % (xml_helpers.getTagValue(loc, "City"))
    outstr_for_all_dates_post += '<region>%s</region>' % (xml_helpers.getTagValue(loc, "State"))
    outstr_for_all_dates_post += '<country>%s</country>' % (xml_helpers.getTagValue(loc, "Country"))
    outstr_for_all_dates_post += '<postalCode>%s</postalCode>' % (xml_helpers.getTagValue(loc, "ZipOrPostalCode"))
      # no equivalent: latitude, longitude
    outstr_for_all_dates_post += '</location></locations>'
    
    outstr_for_all_dates_post += '<detailURL>%s</detailURL>' % (xml_helpers.getTagValue(opp, "DetailURL"))
    outstr_for_all_dates_post += '<description>%s</description>' % (xml_helpers.getTagValue(opp, "Description"))
    outstr_for_all_dates_post += '<lastUpdated>%s</lastUpdated>' % (xml_helpers.getTagValue(opp, "DateListed"))

    for oppdate in oppdates:
      if progress:
        totrecs = totrecs + 1
        if totrecs%250==0:
          print datetime.now(),": ",totrecs," records generated."

      s += '<VolunteerOpportunity>'
      s += outstr_for_all_dates_pre
      
      s += '<dateTimeDurations><dateTimeDuration>'
      if oppdate == None:
        s += '<openEnded>Yes</openEnded>'
      else:
        s += '<openEnded>No</openEnded>'
        # hardcoded: commitmentHoursPerWeek
        s += '<commitmentHoursPerWeek>0</commitmentHoursPerWeek>'
        # TODO: timezone
        s += '<startDate>%s</startDate>' % (xml_helpers.getTagValue(oppdate, "StartDate"))
        s += '<endDate>%s</endDate>' % (xml_helpers.getTagValue(oppdate, "EndDate"))
        s += '<startTime>%s</startTime>' % (xml_helpers.getTagValue(oppdate, "StartTime"))
        s += '<endTime>%s</endTime>' % (xml_helpers.getTagValue(oppdate, "EndTime"))
      s += '</dateTimeDuration></dateTimeDurations>'
      
      s += outstr_for_all_dates_post
      s += '</VolunteerOpportunity>'
  if progress:
    print "done with VolunteerOpportunities..."
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'
  return s

def Parse(instr, maxrecs, progress):
  # frees up RAM to split parsing from FP parsing and codegen
  if progress:
    print datetime.now(),"parse_handsonnetwork.Parse: starting parse..."
  s = ParseHelper(instr, maxrecs, progress)
  #s = re.sub(r'><([^/])', r'>\n<\1', s)
  #print s
  if progress:
    print datetime.now(),"parse_handsonnetwork.Parse: starting FP XML parse..."
  cvtd_xml = parse_footprint.Parse(s, maxrecs, progress)
  if progress:
    print datetime.now(),"parse_handsonnetwork.Parse: return FP DOM."
  return cvtd_xml

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
