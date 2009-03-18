# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom
import xml_helpers
import re
from datetime import datetime

import dateutil.parser

orgs = {}
orgids = {}
max_orgid = 0
def Parse(instr, maxrecs, progress):
  global max_orgid, orgs, orgids

  # TODO: progress
  known_elnames = [ 'Abstract', 'Categories', 'Category', 'CategoryID', 'Country', 'DateListed', 'Description', 'DetailURL', 'Duration', 'DurationQuantity', 'DurationUnit', 'EndDate', 'KeyWords', 'LocalID', 'Location', 'LocationClassification', 'LocationClassificationID', 'LocationClassifications', 'Locations', 'LogoURL', 'Name', 'OpportunityDate', 'OpportunityDates', 'OpportunityType', 'OpportunityTypeID', 'SponsoringOrganization', 'SponsoringOrganizations', 'StartDate', 'StateOrProvince', 'Title', 'VolunteerOpportunity', 'ZipOrPostalCode', ]

  def register_org(orgname, orgstr):
      global max_orgid, orgs, orgids
      if orgname in orgids:
          return orgids[orgname]
      max_orgid = max_orgid + 1
      orgstr = '<Organization>'
      orgstr += '<organizationID>%d</organizationID>' % (len(orgids))
      orgstr += '<nationalEIN></nationalEIN>'
      orgstr += '<name>%s</name>' % (orgname)
      orgstr += '<missionStatement></missionStatement>'
      orgstr += '<description></description>'
      orgstr += '<location><city></city><region></region><postalCode></postalCode></location>'
      orgstr += '<organizationURL></organizationURL>'
      orgstr += '<donateURL></donateURL>'
      orgstr += '<logoURL></logoURL>'
      orgstr += '<detailURL></detailURL>'
      orgstr += '</Organization>'
      orgs[max_orgid] = orgstr
      orgids[orgname] = max_orgid
      return max_orgid

  instr = re.sub(r'<(/?db):', r'<\1_', instr)
  opps = re.findall(r'<VolunteerOpportunity>.+?</VolunteerOpportunity>', instr, re.DOTALL)
  volopps = ""
  for i,oppstr in enumerate(opps):
    if (maxrecs>0 and i>maxrecs):
      break
    xml_helpers.printProgress("opps", progress, i, maxrecs)

    item = xml_helpers.simpleParser(oppstr, known_elnames, progress=False)

    # SponsoringOrganization/Name -- fortunately, no conflicts
    # but there's no data except the name
    orgname = xml_helpers.getTagValue(item, "Name")
    orgid = register_org(orgname, orgname)

    # logoURL -- sigh, this is for the opportunity not the org
    volopps += '<VolunteerOpportunity>'
    volopps += '<volunteerOpportunityID>%d</volunteerOpportunityID>' % (i)
    volopps += '<sponsoringOrganizationID>%d</sponsoringOrganizationID>' % (orgid)
    volopps += '<volunteerHubOrganizationID>%s</volunteerHubOrganizationID>' % (xml_helpers.getTagValue(item, "LocalID"))
    volopps += '<title>%s</title>' % (xml_helpers.getTagValue(item, "Title"))
    volopps += '<abstract>%s</abstract>' % (xml_helpers.getTagValue(item, "Abstract"))
    volopps += '<description>%s</description>' % (xml_helpers.getTagValue(item, "Description"))
    volopps += '<detailURL>%s</detailURL>' % (xml_helpers.getTagValue(item, "DetailURL"))
    volopps += '<volunteersNeeded>-8888</volunteersNeeded>'

    oppdates = item.getElementsByTagName("OpportunityDate")
    if (oppdates.length != 1):
      print datetime.now(),"parse_americorps.py: only 1 OpportunityDate supported."
      return None
    oppdate = oppdates[0]
    volopps += '<dateTimeDurations><dateTimeDuration>'
    volopps += '<openEnded>No</openEnded>'
    volopps += '<duration>P%s%s</duration>' % (xml_helpers.getTagValue(oppdate, "DurationQuantity"), xml_helpers.getTagValue(oppdate, "DurationUnit"))
    volopps += '<commitmentHoursPerWeek>0</commitmentHoursPerWeek>'
    volopps += '<startDate>%s</startDate>' % (xml_helpers.getTagValue(oppdate, "StartDate"))
    volopps += '<endDate>%s</endDate>' % (xml_helpers.getTagValue(oppdate, "EndDate"))
    volopps += '</dateTimeDuration></dateTimeDurations>'

    volopps += '<locations>'
    opplocs = item.getElementsByTagName("Location")
    for opploc in opplocs:
        volopps += '<location>'
        volopps += '<region>%s</region>' % (xml_helpers.getTagValue(opploc, "StateOrProvince"))
        volopps += '<country>%s</country>' % (xml_helpers.getTagValue(opploc, "Country"))
        volopps += '<postalCode>%s</postalCode>' % (xml_helpers.getTagValue(opploc, "ZipOrPostalCode"))
        volopps += '</location>'
    volopps += '</locations>'

    volopps += '<categoryTags/>'

    volopps += '</VolunteerOpportunity>'
    
  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  # TODO: assign provider IDs?
  s += '<providerID>106</providerID>'
  s += '<providerName>networkforgood</providerName>'
  s += '<feedID>americorps</feedID>'
  s += '<createdDateTime>2008-12-30T14:30:10.5</createdDateTime>' # TODO: get/create real feed date
  s += '<providerURL>http://www.networkforgood.org/</providerURL>'
  s += '<description>Americorps</description>'
  # TODO: capture ts -- use now?!
  s += '</FeedInfo>'

  # hardcoded: Organization
  s += '<Organizations>'
  for key in orgs:
      s += orgs[key]
  s += '</Organizations>'
  s += '<VolunteerOpportunities>'
  s += volopps
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'

  s = re.sub(r'><([^/])', r'>\n<\1', s)
  return s

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
