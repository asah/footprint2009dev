# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom
from xml.parsers.expat import ExpatError

def validateXML(xmldoc):
  for node in xmldoc.childNodes:
    if (xmldoc.nodeType == xmldoc.ELEMENT_NODE and
        xmldoc.tagName not in known_elnames):
      print "unknown tagName '"+xmldoc.tagName+"'"
      # TODO: spellchecking...
    validateXML(node)

# parsing footprint format is the identity operation
def ParseXML(doc):
  xmldoc = minidom.parse(doc)
  validateXML(xmldoc)
  return xmldoc

def ParseXMLString(s):
  try:
    xmldoc = minidom.parseString(s)
  except ExpatError, ee:
    print "XML parsing error on line ", ee.lineno
    lines = s.split("\n")
    for i in range(ee.lineno - 3, ee.lineno + 3):
      if i >= 0 and i < len(lines):
        print "%6d %s" % (i+1, lines[i])
    exit(0)
  validateXML(xmldoc)
  return xmldoc

known_elnames = {
  'FeedInfo': 1,
  'FootprintFeed': 1,
  'Organization': 1,
  'Organizations': 1,
  'VolunteerOpportunities': 1,
  'VolunteerOpportunity': 1,
  'abstract': 1,
  'audienceTag': 1,
  'audienceTags': 1,
  'categoryTag': 1,
  'categoryTags': 1,
  'city': 1,
  'commitmentHoursPerWeek': 1,
  'contactEmail': 1,
  'contactName': 1,
  'contactPhone': 1,
  'country': 1,
  'createdDateTime': 1,
  'dateTimeDuration': 1,
  'dateTimeDurationType': 1,
  'dateTimeDurations': 1,
  'description': 1,
  'detailURL': 1,
  'directions': 1,
  'donateURL': 1,
  'duration': 1,
  'email': 1,
  'endDate': 1,
  'endTime': 1,
  'expires': 1,
  'fax': 1,
  'feedID': 1,
  'guidestarID': 1,
  'iCalRecurrence': 1,
  'language': 1,
  'lastUpdated': 1,
  'location': 1,
  'locationType': 1,
  'locations': 1,
  'logoURL': 1,
  'minimumAge': 1,
  'missionStatement': 1,
  'name': 1,
  'nationalEIN': 1,
  'openEnded': 1,
  'organizationID': 1,
  'organizationURL': 1,
  'paid': 1,
  'phone': 1,
  'postalCode': 1,
  'providerID': 1,
  'providerName': 1,
  'providerURL': 1,
  'region': 1,
  'schemaVersion': 1,
  'sexRestrictedEnum': 1,
  'sexRestritedTo': 1,
  'skills': 1,
  'sponsoringOrganizationID': 1,
  'startDate': 1,
  'startTime': 1,
  'streetAddress1': 1,
  'streetAddress2': 1,
  'streetAddress3': 1,
  'title': 1,
  'tzOlsonPath': 1,
  'virtual': 1,
  'volunteerHubOrganizationID': 1,
  'volunteerOpportunityID': 1,
  'volunteersFilled': 1,
  'volunteersSlots': 1,
  'volunteersNeeded': 1,
  'yesNoEnum': 1,
  }

if __name__ == "__main__":
  sys = __import__('sys')
  xmldoc = ParseFootprintXML(sys.argv[1])
  # tests go here


