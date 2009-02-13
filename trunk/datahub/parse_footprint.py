# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom

def validateXML(xmldoc):
  for node in xmldoc.childNodes:
    if (xmldoc.nodeType == xmldoc.ELEMENT_NODE and
        xmldoc.tagName not in known_elnames):
      print "unknown tagName '"+xmldoc.tagName+"'"
      # TODO: spellchecking...
    validateXML(node)

# parsing footprint format is the identity operation
def ParseFootprintXML(doc):
  xmldoc = minidom.parse(doc)
  validateXML(xmldoc)
  return xmldoc

known_elnames = {
  'FeedInfo': 1,
  'FootprintFeed': 1,
  'Opportunities': 1,
  'Opportunity': 1,
  'Organization': 1,
  'Organizations': 1,
  'abstract': 1,
  'audience': 1,
  'audiences': 1,
  'categories': 1,
  'category': 1,
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
  'directions': 1,
  'durationQuantity': 1,
  'durationUnit': 1,
  'durationUnitEnum': 1,
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
  'opportunityID': 1,
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
  'startDate': 1,
  'startTime': 1,
  'streetAddress1': 1,
  'streetAddress2': 1,
  'streetAddress3': 1,
  'title': 1,
  'tzOlsonPath': 1,
  'virtual': 1,
  'volunteersFilled': 1,
  'volunteersSlots': 1,
  'volunteersStillNeeded': 1,
  'yesNoEnum': 1,
  }

if __name__ == "__main__":
  sys = __import__('sys')
  xmldoc = ParseFootprintXML(sys.argv[1])
  # tests go here


