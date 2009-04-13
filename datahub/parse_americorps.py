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
parser for Hands On Network
"""

import xml_helpers as xmlh
import re
from datetime import datetime

ORGS = {}
ORGIDS = {}
MAX_ORGID = 0

def register_org(orgname, orgstr):
  """register the organization info, for lookup later."""
  global MAX_ORGID
  if orgname in ORGIDS:
    return ORGIDS[orgname]
  MAX_ORGID = MAX_ORGID + 1
  orgstr = '<Organization>'
  orgstr += '<organizationID>%d</organizationID>' % (len(ORGIDS))
  orgstr += '<nationalEIN></nationalEIN>'
  orgstr += '<name>%s</name>' % (orgname)
  orgstr += '<missionStatement></missionStatement>'
  orgstr += '<description></description>'
  orgstr += '<location>'
  orgstr += xmlh.output_val("city", "")
  orgstr += xmlh.output_val("region", "")
  orgstr += xmlh.output_val("postalCode", "")
  orgstr += '</location>'
  orgstr += '<organizationURL></organizationURL>'
  orgstr += '<donateURL></donateURL>'
  orgstr += '<logoURL></logoURL>'
  orgstr += '<detailURL></detailURL>'
  orgstr += '</Organization>'
  ORGS[MAX_ORGID] = orgstr
  ORGIDS[orgname] = MAX_ORGID
  return MAX_ORGID

# pylint: disable-msg=R0915
def parse(instr, maxrecs, progress):
  """return FPXML given americorps data"""

  # TODO: progress
  known_elnames = [
    'Abstract', 'Categories', 'Category', 'CategoryID', 'Country', 'DateListed',
    'Description', 'DetailURL', 'Duration', 'DurationQuantity', 'DurationUnit',
    'EndDate', 'KeyWords', 'LocalID', 'Location', 'LocationClassification',
    'LocationClassificationID', 'LocationClassifications', 'Locations',
    'LogoURL', 'Name', 'OpportunityDate', 'OpportunityDates', 'OpportunityType',
    'OpportunityTypeID', 'SponsoringOrganization', 'SponsoringOrganizations',
    'StartDate', 'StateOrProvince', 'Title', 'VolunteerOpportunity',
    'ZipOrPostalCode' ]

  instr = re.sub(r'<(/?db):', r'<\1_', instr)
  opps = re.findall(r'<VolunteerOpportunity>.+?</VolunteerOpportunity>',
                    instr, re.DOTALL)
  volopps = ""
  for i, oppstr in enumerate(opps):
    if (maxrecs > 0 and i > maxrecs):
      break
    xmlh.print_progress("opps", progress, i, maxrecs)

    item = xmlh.simple_parser(oppstr, known_elnames, progress=False)

    # SponsoringOrganization/Name -- fortunately, no conflicts
    # but there's no data except the name
    orgname = xmlh.get_tag_val(item, "Name")
    orgid = register_org(orgname, orgname)

    # logoURL -- sigh, this is for the opportunity not the org
    volopps += '<VolunteerOpportunity>'
    volopps += xmlh.output_val('volunteerOpportunityID', str(i))
    volopps += xmlh.output_val('sponsoringOrganizationID', str(orgid))
    volopps += xmlh.output_node('volunteerHubOrganizationID', item, "LocalID")
    volopps += xmlh.output_node('title', item, "Title")
    volopps += xmlh.output_node('abstract', item, "Abstract")
    volopps += xmlh.output_node('description', item, "Description")
    volopps += xmlh.output_node('detailURL', item, "DetailURL")
    volopps += xmlh.output_val('volunteersNeeded', "-8888")

    oppdates = item.getElementsByTagName("OpportunityDate")
    if (oppdates.length != 1):
      print datetime.now(), \
          "parse_americorps.py: only 1 OpportunityDate supported."
      return None
    oppdate = oppdates[0]
    volopps += '<dateTimeDurations><dateTimeDuration>'
    volopps += xmlh.output_val('openEnded', 'No')
    volopps += xmlh.output_val('duration', 'P%s%s' % 
                              (xmlh.get_tag_val(oppdate, "DurationQuantity"),
                               xmlh.get_tag_val(oppdate, "DurationUnit")))
    volopps += xmlh.output_val('commitmentHoursPerWeek', '0')
    volopps += xmlh.output_node('startDate', oppdate, "StartDate")
    volopps += xmlh.output_node('endDate', oppdate, "EndDate")
    volopps += '</dateTimeDuration></dateTimeDurations>'

    volopps += '<locations>'
    opplocs = item.getElementsByTagName("Location")
    for opploc in opplocs:
      volopps += '<location>'
      volopps += xmlh.output_node('region', opploc, "StateOrProvince")
      volopps += xmlh.output_node('country', opploc, "Country")
      volopps += xmlh.output_node('postalCode', opploc, "ZipOrPostalCode")
      volopps += '</location>'
    volopps += '</locations>'

    volopps += '<categoryTags/>'

    volopps += '</VolunteerOpportunity>'
    
  # convert to footprint format
  outstr = '<?xml version="1.0" ?>'
  outstr += '<FootprintFeed schemaVersion="0.1">'
  outstr += '<FeedInfo>'
  # TODO: assign provider IDs?
  outstr += xmlh.output_val('providerID', '106')
  outstr += xmlh.output_val('providerName', 'networkforgood')
  outstr += xmlh.output_val('feedID', 'americorps')
  outstr += xmlh.output_val('createdDateTime', xmlh.current_ts())
  outstr += xmlh.output_val('providerURL', 'http://www.networkforgood.org/')
  outstr += xmlh.output_val('description', 'Americorps')
  # TODO: capture ts -- use now?!
  outstr += '</FeedInfo>'

  # hardcoded: Organization
  outstr += '<Organizations>'
  for key in ORGS:
    outstr += ORGS[key]
  outstr += '</Organizations>'
  outstr += '<VolunteerOpportunities>'
  outstr += volopps
  outstr += '</VolunteerOpportunities>'
  outstr += '</FootprintFeed>'

  outstr = re.sub(r'><([^/])', r'>\n<\1', outstr)
  return outstr

