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
  chunks = re.findall(r'<(?:Organizations|VolunteerOpportunities|FeedInfo)>.+?</(?:Organizations|VolunteerOpportunities|FeedInfo)>', instr, re.DOTALL)
  for chunk in chunks:
    subchunks = re.findall(r'<(?:VolunteerOpportunity)>.+?</(?:VolunteerOpportunity)>', chunk, re.DOTALL)
    for subchunk in subchunks:
      totrecs += 1
      
    #if re.search("<VolunteerOpportunity>", chunk):
      #totrecs = totrecs + 1
      
    if (maxrecs > 0 and totrecs > maxrecs):
      break
    if progress and totrecs % 250 == 0:
      print datetime.now(), ": ", totrecs, " records generated."
      
    node = xml_helpers.simpleParser(chunk, known_elnames, False)
    s = xml_helpers.prettyxml(node, True)
    outstr += s
  outstr += '</FootprintFeed>'
  if progress:
    print datetime.now(), totrecs, "opportunities found."
  return outstr

def parse(s, maxrecs, progress):
  """return python DOM object given FPXML"""
  # parsing footprint format is the identity operation
  # TODO: maxrecs
  # TODO: progress
  if progress:
    print datetime.now(), "parse_footprint: parsing ", len(s), " bytes."
  xmldoc = xml_helpers.simpleParser(s, known_elnames, progress)
  if progress:
    print datetime.now(), "parse_footprint: done parsing."
  return xmldoc

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here

