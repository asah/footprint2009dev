# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom import minidom
import xml_helpers
from datetime import datetime

def Parse(s, maxrecs, progress):
  # parsing footprint format is the identity operation
  # TODO: maxrecs
  # TODO: progress
  known_elnames = [ 'FeedInfo', 'FootprintFeed', 'Organization', 'Organizations', 'VolunteerOpportunities', 'VolunteerOpportunity', 'abstract', 'audienceTag', 'audienceTags', 'categoryTag', 'categoryTags', 'city', 'commitmentHoursPerWeek', 'contactEmail', 'contactName', 'contactPhone', 'country', 'createdDateTime', 'dateTimeDuration', 'dateTimeDurationType', 'dateTimeDurations', 'description', 'detailURL', 'directions', 'donateURL', 'duration', 'email', 'endDate', 'endTime', 'expires', 'fax', 'feedID', 'guidestarID', 'iCalRecurrence', 'language', 'latitude', 'lastUpdated', 'location', 'locationType', 'locations', 'logoURL', 'longitude', 'minimumAge', 'missionStatement', 'name', 'nationalEIN', 'openEnded', 'organizationID', 'organizationURL', 'paid', 'phone', 'postalCode', 'providerID', 'providerName', 'providerURL', 'region', 'schemaVersion', 'sexRestrictedEnum', 'sexRestritedTo', 'skills', 'sponsoringOrganizationID', 'startDate', 'startTime', 'streetAddress1', 'streetAddress2', 'streetAddress3', 'title', 'tzOlsonPath', 'virtual', 'volunteerHubOrganizationID', 'volunteerOpportunityID', 'volunteersFilled', 'volunteersSlots', 'volunteersNeeded', 'yesNoEnum', ]
  if progress:
    print datetime.now(),"parse_footprint: parsing ",len(s)," bytes."
  xmldoc = xml_helpers.simpleParser(s, known_elnames)
  if progress:
    print datetime.now(),"parse_footprint: done parsing."
  return xmldoc

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here

