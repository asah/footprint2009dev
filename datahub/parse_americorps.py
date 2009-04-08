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
  orgstr += xmlh.outputVal("city", "")
  orgstr += xmlh.outputVal("region", "")
  orgstr += xmlh.outputVal("postalCode", "")
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
    xmlh.printProgress("opps", progress, i, maxrecs)

    item = xmlh.simpleParser(oppstr, known_elnames, progress=False)

    # SponsoringOrganization/Name -- fortunately, no conflicts
    # but there's no data except the name
    orgname = xmlh.getTagValue(item, "Name")
    orgid = register_org(orgname, orgname)

    # logoURL -- sigh, this is for the opportunity not the org
    volopps += '<VolunteerOpportunity>'
    volopps += xmlh.outputVal('volunteerOpportunityID', str(i))
    volopps += xmlh.outputVal('sponsoringOrganizationID', str(orgid))
    volopps += xmlh.outputNode('volunteerHubOrganizationID', item, "LocalID")
    volopps += xmlh.outputNode('title', item, "Title")
    volopps += xmlh.outputNode('abstract', item, "Abstract")
    volopps += xmlh.outputNode('description', item, "Description")
    volopps += xmlh.outputNode('detailURL', item, "DetailURL")
    volopps += xmlh.outputVal('volunteersNeeded', "-8888")

    oppdates = item.getElementsByTagName("OpportunityDate")
    if (oppdates.length != 1):
      print datetime.now(), \
          "parse_americorps.py: only 1 OpportunityDate supported."
      return None
    oppdate = oppdates[0]
    volopps += '<dateTimeDurations><dateTimeDuration>'
    volopps += xmlh.outputVal('openEnded', 'No')
    volopps += xmlh.outputVal('duration', 'P%s%s' % 
                              (xmlh.getTagValue(oppdate, "DurationQuantity"),
                               xmlh.getTagValue(oppdate, "DurationUnit")))
    volopps += xmlh.outputVal('commitmentHoursPerWeek', '0')
    volopps += xmlh.outputNode('startDate', oppdate, "StartDate")
    volopps += xmlh.outputNode('endDate', oppdate, "EndDate")
    volopps += '</dateTimeDuration></dateTimeDurations>'

    volopps += '<locations>'
    opplocs = item.getElementsByTagName("Location")
    for opploc in opplocs:
      volopps += '<location>'
      volopps += xmlh.outputNode('region', opploc, "StateOrProvince")
      volopps += xmlh.outputNode('country', opploc, "Country")
      volopps += xmlh.outputNode('postalCode', opploc, "ZipOrPostalCode")
      volopps += '</location>'
    volopps += '</locations>'

    volopps += '<categoryTags/>'

    volopps += '</VolunteerOpportunity>'
    
  # convert to footprint format
  outstr = '<?xml version="1.0" ?>'
  outstr += '<FootprintFeed schemaVersion="0.1">'
  outstr += '<FeedInfo>'
  # TODO: assign provider IDs?
  outstr += xmlh.outputVal('providerID', '106')
  outstr += xmlh.outputVal('providerName', 'networkforgood')
  outstr += xmlh.outputVal('feedID', 'americorps')
  outstr += xmlh.outputVal('createdDateTime', xmlh.curTimeString())
  outstr += xmlh.outputVal('providerURL', 'http://www.networkforgood.org/')
  outstr += xmlh.outputVal('description', 'Americorps')
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

