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

"""
parser for footprint itself (identity parse)
"""
import xml_helpers as xmlh
from datetime import datetime
import re

# 90 days
DEFAULT_EXPIRATION = (90 * 86400)

# 10 years
DEFAULT_DURATION = (10 * 365 * 86400)

KNOWN_ELNAMES = [
  'FeedInfo', 'FootprintFeed', 'Organization', 'Organizations',
  'VolunteerOpportunities', 'VolunteerOpportunity', 'abstract', 'audienceTag',
  'audienceTags', 'categoryTag', 'categoryTags', 'city',
  'commitmentHoursPerWeek', 'contactEmail', 'contactName', 'contactPhone',
  'country', 'createdDateTime', 'dateTimeDuration', 'dateTimeDurationType',
  'dateTimeDurations', 'description', 'detailURL', 'directions', 'donateURL',
  'duration', 'email', 'endDate', 'endTime', 'expires', 'fax', 'feedID',
  'guidestarID', 'iCalRecurrence', 'language', 'latitude', 'lastUpdated',
  'location', 'locationType', 'locations', 'logoURL', 'longitude', 'minimumAge',
  'missionStatement', 'name', 'nationalEIN', 'openEnded', 'organizationID',
  'organizationURL', 'paid', 'phone', 'postalCode', 'providerID',
  'providerName', 'providerURL', 'region', 'schemaVersion', 'sexRestrictedEnum',
  'sexRestritedTo', 'skills', 'sponsoringOrganizationID', 'startDate',
  'startTime', 'streetAddress1', 'streetAddress2', 'streetAddress3', 'title',
  'tzOlsonPath', 'virtual', 'volunteerHubOrganizationID',
  'volunteerOpportunityID', 'volunteersFilled', 'volunteersSlots',
  'volunteersNeeded', 'yesNoEnum'
  ]

def set_default_time_elem(doc, entity, tagname, timest=xmlh.current_ts()):
  """footprint macro."""
  cdt = xmlh.set_default_value(doc, entity, tagname, timest)
  xmlh.set_default_attr(doc, cdt, "olsonTZ", "America/Los_Angeles")

def parse_fast(instr, maxrecs, progress):
  """fast parser but doesn't check correctness,
  i.e. must be pre-checked by caller."""
  totrecs = 0
  outstr = '<?xml version="1.0" ?>'
  outstr += '<FootprintFeed schemaVersion="0.1">'
  # note: preserves order, so diff works (vs. one sweep per element type)
  chunks = re.findall(
    re.compile('<(?:Organizations|VolunteerOpportunities|FeedInfo)>.+?'+\
                 '</(?:Organizations|VolunteerOpportunities|FeedInfo)>',
               re.DOTALL), instr)
  for chunk in chunks:
    node = xmlh.simple_parser(chunk, KNOWN_ELNAMES, False)
    if node.firstChild.nodeName == "FeedInfo":
      xmlh.set_default_value(node, node.firstChild, "feedID", "0")
      set_default_time_elem(node, node.firstChild, "createdDateTime")
    if node.firstChild.nodeName == "VolunteerOpportunities":
      totrecs += len(node.firstChild.childNodes)
      if (maxrecs > 0 and totrecs > maxrecs):
        break
      if progress and totrecs % 250 == 0:
        print datetime.now(), ": ", totrecs, " records generated."
      for opp in node.firstChild.childNodes:
        if opp.nodeType == node.ELEMENT_NODE:
          xmlh.set_default_value(node, opp, "volunteersNeeded", -8888)
          xmlh.set_default_value(node, opp, "paid", "No")
          xmlh.set_default_value(node, opp, "sexRestrictedTo", "Neither")
          xmlh.set_default_value(node, opp, "language", "English")
          set_default_time_elem(node, opp, "lastUpdated")
          set_default_time_elem(node, opp, "expires", 
                                xmlh.current_ts(DEFAULT_EXPIRATION))
          for loc in opp.getElementsByTagName("location"):
            xmlh.set_default_value(node, loc, "virtual", "No")
            xmlh.set_default_value(node, loc, "country", "US")
          for dttm in opp.getElementsByTagName("dateTimeDurations"):
            xmlh.set_default_value(node, dttm, "openEnded", "No")
            xmlh.set_default_value(node, dttm, "iCalRecurrence", "")
            if (dttm.getElementsByTagName("startTime") == None and
                dttm.getElementsByTagName("endTime") == None):
              set_default_time_elem(node, dttm, "timeFlexible", "Yes")
            else:
              set_default_time_elem(node, dttm, "timeFlexible", "No")
            xmlh.set_default_value(node, dttm, "openEnded", "No")
          time_elems = opp.getElementsByTagName("startTime")
          time_elems += opp.getElementsByTagName("endTime")
          for el in time_elems:
            xmlh.set_default_attr(node, el, "olsonTZ", "America/Los_Angeles")
            
    outstr += xmlh.prettyxml(node, True)
  outstr += '</FootprintFeed>'
  if progress:
    print datetime.now(), totrecs, "opportunities found."
  return outstr

def parse(instr, maxrecs, progress):
  """return python DOM object given FPXML"""
  # parsing footprint format is the identity operation
  # TODO: maxrecs
  # TODO: progress
  if progress:
    print datetime.now(), "parse_footprint: parsing ", len(instr), " bytes."
  xmldoc = xmlh.simple_parser(instr, KNOWN_ELNAMES, progress)
  if progress:
    print datetime.now(), "parse_footprint: done parsing."
  return xmldoc
