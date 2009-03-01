# Copyright 2009 Google Inc.  All Rights Reserved.
#

import xml_helpers
import xml.dom.pulldom
from datetime import datetime
import re

known_elnames = [ 'FeedInfo', 'FootprintFeed', 'Organization', 'Organizations', 'VolunteerOpportunities', 'VolunteerOpportunity', 'abstract', 'audienceTag', 'audienceTags', 'categoryTag', 'categoryTags', 'city', 'commitmentHoursPerWeek', 'contactEmail', 'contactName', 'contactPhone', 'country', 'createdDateTime', 'dateTimeDuration', 'dateTimeDurationType', 'dateTimeDurations', 'description', 'detailURL', 'directions', 'donateURL', 'duration', 'email', 'endDate', 'endTime', 'expires', 'fax', 'feedID', 'guidestarID', 'iCalRecurrence', 'language', 'latitude', 'lastUpdated', 'location', 'locationType', 'locations', 'logoURL', 'longitude', 'minimumAge', 'missionStatement', 'name', 'nationalEIN', 'openEnded', 'organizationID', 'organizationURL', 'paid', 'phone', 'postalCode', 'providerID', 'providerName', 'providerURL', 'region', 'schemaVersion', 'sexRestrictedEnum', 'sexRestritedTo', 'skills', 'sponsoringOrganizationID', 'startDate', 'startTime', 'streetAddress1', 'streetAddress2', 'streetAddress3', 'title', 'tzOlsonPath', 'virtual', 'volunteerHubOrganizationID', 'volunteerOpportunityID', 'volunteersFilled', 'volunteersSlots', 'volunteersNeeded', 'yesNoEnum', ]

def ParseFast(instr, maxrecs, progress):
  totrecs = 0
  outstr = '<?xml version="1.0" ?>'
  outstr += '<FootprintFeed schemaVersion="0.1">'
  # note: preserves order, so diff works (vs. one sweep per element type)
  chunks = re.findall(r'<(?:Organization|VolunteerOpportunity|FeedInfo)>.+?</(?:Organization|VolunteerOpportunity|FeedInfo)>', instr, re.DOTALL)
  for chunk in chunks:
    if re.search("<VolunteerOpportunity>", chunk):
      totrecs = totrecs + 1
      if (maxrecs > 0 and totrecs > maxrecs):
        break
      if progress and totrecs%250==0:
        print datetime.now(),": ",totrecs," records generated."
    node = xml_helpers.simpleParser(chunk, known_elnames, False)
    s = xml_helpers.prettyxml(node)
    outstr += s
  outstr += '</FootprintFeed>'
  if progress:
    print datetime.now(),totrecs,"opportunities found."
  return outstr

def Parse(s, maxrecs, progress):
  # parsing footprint format is the identity operation
  # TODO: maxrecs
  # TODO: progress
  if progress:
    print datetime.now(),"parse_footprint: parsing ",len(s)," bytes."
  xmldoc = xml_helpers.simpleParser(s, known_elnames, progress)
  if progress:
    print datetime.now(),"parse_footprint: done parsing."
  return xmldoc

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here

