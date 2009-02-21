# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom
from xml.parsers.expat import ExpatError
import xml_helpers

def Parse(s, maxrecs):
  # parsing footprint format is the identity operation
  # TODO: maxrecs
  return xml_helpers.simpleParser(s, known_elnames)

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
  'latitude': 1,
  'lastUpdated': 1,
  'location': 1,
  'locationType': 1,
  'locations': 1,
  'logoURL': 1,
  'longitude': 1,
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
  # tests go here

