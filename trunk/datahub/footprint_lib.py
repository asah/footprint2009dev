#!/usr/bin/python
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

#from xml.dom.ext import PrettyPrint
import gzip
import hashlib
import urllib
import re
from datetime import datetime
import parse_footprint
import parse_usaservice
import parse_handsonnetwork
import parse_idealist
import parse_craigslist
import parse_americorps
import parse_userpostings
import parse_volunteermatch
import subprocess
import sys
import time
import xml_helpers
import xml.dom.pulldom
from optparse import OptionParser

import dateutil
import dateutil.tz
import dateutil.parser

FIELDSEP = "\t"
RECORDSEP = "\n"

MAX_ABSTRACT_LEN = 250

DEBUG = False
PROGRESS = False
PRINTHEAD = False

FIELDTYPES = {
  "title":"builtin",
  "description":"builtin",
  "link":"builtin",
  "event_type":"builtin",
  "quantity":"builtin",
  "image_link":"builtin",
  "event_date_range":"builtin",
  "id":"builtin",
  "location":"builtin",

  "paid":"boolean",
  "openended":"boolean",

  "volunteersSlots":"integer",
  "volunteersFilled":"integer",
  "volunteersNeeded":"integer",
  "minimumAge":"integer",

  "latitude":"float",
  "longitude":"float",

  "providerURL":"URL",
  "detailURL":"URL",
  "org_organizationURL":"URL",
  "org_logoURL":"URL",
  "org_providerURL":"URL",
  "feed_providerURL":"URL",

  "lastUpdated":"dateTime",
  "expires":"dateTime",
  "feed_createdDateTime":"dateTime",

  # note: type "location" isn"t safe because the Base geocoder can fail,
  # causing the record to be rejected
  "duration":"string",
  "abstract":"string",
  "sexRestrictedTo":"string",
  "skills":"string",
  "contactName":"string",
  "contactPhone":"string",
  "contactEmail":"string",
  "language":"string",
  "org_name":"string",
  "org_missionStatement":"string",
  "org_description":"string",
  "org_phone":"string",
  "org_fax":"string",
  "org_email":"string",
  "categories":"string",
  "audiences":"string",
  "commitmentHoursPerWeek":"string",
  "employer":"string",
  "feed_providerName":"string",
  "feed_description":"string",
  "providerID":"string",
  "feed_providerID":"string",
  "feedID":"string",
  "opportunityID":"string",
  "organizationID":"string",
  "sponsoringOrganizationID":"strng",
  "volunteerHubOrganizationID":"string",
  "org_nationalEIN":"string",
  "org_guidestarID":"string",
  "venue_name":"string",
  "location_string":"string",
  "orgLocation":"string",

  "hidden_details":"string",
}

# Google Base uses ISO8601... in PST -- I kid you not:
# http://base.google.com/support/bin/answer.py?answer=78170&hl=en#Events%20and%20Activities    # pylint: disable-msg=C0301
# and worse, you have to change an env var in python...
def convert_dt_to_gbase(datestr, timestr, timezone):
  """converts dates like YYYY-MM-DD, times like HH:MM:SS and
  timezones like America/New_York, into Google Base format."""
  try:
    tzinfo = dateutil.tz.tzstr(timezone)
  except:
    tzinfo = dateutil.tz.tzutc()
  timestr = dateutil.parser.parse(datestr + " " + timestr)
  timestr = timestr.replace(tzinfo=tzinfo)
  pst = dateutil.tz.tzstr("PST8PDT")
  timestr = timestr.astimezone(pst)
  if timestr.year < 1900:
    timestr = timestr.replace(year=timestr.year+1900)
  res = timestr.strftime("%Y-%m-%dT%H:%M:%S")
  res = re.sub(r'Z$', '', res)
  return res

CSV_REPEATED_FIELDS = ['categories', 'audiences']
DIRECT_MAP_FIELDS = ['opportunityID', 'organizationID', 'volunteersSlots', 'volunteersFilled',
                     'volunteersNeeded', 'minimumAge', 'sexRestrictedTo', 'skills', 'contactName',
                     'contactPhone', 'contactEmail', 'providerURL', 'language', 'lastUpdated',
                     'expires', 'detailURL']
ORGANIZATION_FIELDS = ['nationalEIN', 'guidestarID', 'name', 'missionStatement', 'description',
                       'phone', 'fax', 'email', 'organizationURL', 'logoURL', 'providerURL']

def flattener_value(node):
  """return a DOM node's first child, sans commas"""
  if (node.firstChild != None):
    return node.firstChild.data.replace(",", "")
  else:
    return ""

def flatten_to_csv(domnode):
  """prints the children of a DOM node as CSV separated strings"""
  #print field
  return ",".join(filter(lambda x: x != "", map(flattener_value, domnode.childNodes)))  # pylint: disable-msg=W0141

def output_field(name, value):
  """print a field value, handling long strings, header lines and custom datatypes."""
  #global PRINTHEAD, DEBUG
  if PRINTHEAD:
    if (name not in FIELDTYPES):
      print datetime.now(), "no type for field: " + name + FIELDTYPES[name]
      sys.exit(1)
    elif (FIELDTYPES[name] == "builtin"):
      return name
    else:
      return "c:"+name+":"+FIELDTYPES[name]
  if DEBUG:
    if (len(value) > 70):
      value = value[0:67] + "... (" + str(len(value)) + " bytes)"
    return name.rjust(22) + " : " + value
  if (FIELDTYPES[name] == "dateTime"):
    return convert_dt_to_gbase(value, "", "UTC")
  return value

def get_addr_field(node, field):
  """assuming a node is named (field), return it with optional trailing space."""
  addr = xml_helpers.getTagValue(node, field)
  if addr != "":
    addr += " "
  return addr
  
def city_loc_fields(node):
  """synthesize a city-region-postal-country string."""
  # note: avoid commas, so it works with CSV
  # (this is good enough for the geocoder)
  loc = ""
  loc += get_addr_field(node, "city")
  loc += get_addr_field(node, "region")
  loc += get_addr_field(node, "postalCode")
  loc += get_addr_field(node, "country")
  return loc

def compute_loc_field(node):
  """concatenate street address fields"""
  loc = get_addr_field(node, "streetAddress1")
  loc += get_addr_field(node, "streetAddress2")
  loc += get_addr_field(node, "streetAddress3")
  return loc

def compute_city_field(node):
  """concatenate street address and city/region/postal/country fields"""
  loc = compute_loc_field(node)
  loc += city_loc_fields(node)
  return loc

def lookup_loc_fields(node):
  """try a multitude of field combinations to get a geocode."""
  fullloc = loc = compute_city_field(node)
  latlong = xml_helpers.getTagValue(node, "latitude") + ","
  latlong += xml_helpers.getTagValue(node, "longitude")
  if latlong == ",":
    latlong = geocode(loc)
  if latlong == "":
    # sometimes address1 contains un-geocodable descriptive language,
    # e.g. venue name, "around the corner from ..." etc.
    loc = get_addr_field(node, "streetAddress2")
    loc += get_addr_field(node, "streetAddress3")
    loc += city_loc_fields(node)
    latlong = geocode(loc)
  if latlong == "":
    # rarely, addr1 & addr are both descriptive
    loc = get_addr_field(node, "streetAddress3")
    loc += city_loc_fields(node)
    latlong = geocode(loc)
  if latlong == "":
    # missing or bogus address lines
    loc = city_loc_fields(node)
  if latlong == "":
    # missing or bogus city name
    loc = get_addr_field(node, "postalCode")
    loc += get_addr_field(node, "country")
    latlong = geocode(loc)
  if latlong == "":
    # missing or bogus postalcode
    loc = get_addr_field(node, "city")
    loc += get_addr_field(node, "region")
    loc += get_addr_field(node, "country")
    latlong = geocode(loc)
  if latlong == "":
    loc += get_addr_field(node, "region")
    loc += get_addr_field(node, "country")
    latlong = geocode(loc)
  if DEBUG:
    print datetime.now(), "geocode: " + loc + "=" + latlong
  return (fullloc, latlong, loc)

def output_loc_field(node, mapped_name):
  """macro for output_field( convert node to loc field )"""
  return output_field(mapped_name, compute_loc_field(node)+city_loc_fields(node))

def output_tag_value(node, fieldname):
  """macro for output_field( get node value )"""
  return output_field(fieldname, xml_helpers.getTagValue(node, fieldname))

def output_tag_value_renamed(node, xmlname, newname):
  """macro for output_field( get node value ) then emitted as newname"""
  return output_field(newname, xml_helpers.getTagValue(node, xmlname))

def compute_stable_id(opp, org, locstr, openended, duration,
                      hrs_per_week, startend):
  """core algorithm for computing an opportunity's unique id."""
  if DEBUG:
    print "opp=" + str(opp)  # shuts up pylint
  eid = xml_helpers.getTagValue(org, "nationalEIN")
  if (eid == ""):
    # support informal "organizations" that lack EINs
    eid = xml_helpers.getTagValue(org, "organizationURL")
  # TODO: if two providers have same listing, good odds the
  # locations will be slightly different...
  loc = locstr

  # TODO: if two providers have same listing, the time info
  # is unlikely to be exactly the same, incl. missing fields
  timestr = openended + duration + hrs_per_week + startend
  return hashlib.md5(eid + loc + timestr).hexdigest()

def get_direct_mapped_field(opp, org):
  """map a field directly from FPXML to Google Base."""
  outstr = ""
  paid = xml_helpers.getTagValue(opp, "paid")
  if (paid == "" or paid.lower()[0] != "y"):
    paid = "n"
  else:
    paid = "y"
  outstr += output_field("paid", paid)
  for field in DIRECT_MAP_FIELDS:
    outstr += FIELDSEP + output_tag_value(opp, field)
  for field in ORGANIZATION_FIELDS:
    outstr += FIELDSEP + output_field("org_"+field, xml_helpers.getTagValue(org, field))
  for field in CSV_REPEATED_FIELDS:
    outstr += FIELDSEP
    fieldval = opp.getElementsByTagName(field)
    val = ""
    if (fieldval.length > 0):
      val = flatten_to_csv(fieldval[0])
    outstr += output_field(field, val)

  # process abstract-- shorten, strip newlines and formatting
  abstract = xml_helpers.getTagValue(opp, "abstract")
  if abstract == "":
    abstract = xml_helpers.getTagValue(opp, "description")
  # strip \n and \b
  abstract = re.sub(r'(\\[bn])+', ' ', abstract)
  # strip XML escaped chars
  abstract = re.sub(r'&([a-z]+|#[0-9]+);', '', abstract)
  abstract = abstract[:MAX_ABSTRACT_LEN]
  outstr += FIELDSEP
  outstr += output_field("abstract", abstract)

  # orgLocation
  outstr += FIELDSEP
  fieldval = opp.getElementsByTagName("orgLocation")
  if (fieldval.length > 0):
    outstr += output_loc_field(fieldval[0], "orgLocation")
  else:
    outstr += output_field("orgLocation", "")

  # hidden_details
  outstr += FIELDSEP
  fieldval = opp.getElementsByTagName("hiddenDetails")
  if (fieldval.length > 0):
    outstr += output_field(fieldval[0], "hidden_details")
  else:
    outstr += output_field("hidden_details", "some hidden text. asdfghjkl.")

  return outstr

def get_base_other_fields(opp, org):
  """These are fields that exist in other Base schemas-- for the sake of
  possible syndication, we try to make ourselves look like other Base
  feeds.  Since we're talking about a small overlap, these fields are
  populated *as well as* direct mapping of the footprint XML fields."""
  outstr = output_field("quantity", xml_helpers.getTagValue(opp, "volunteersNeeded"))
  outstr += FIELDSEP + output_field("employer", xml_helpers.getTagValue(org, "name"))
  # don't map expiration_date -- Base has strict limits (e.g. 2 weeks) on this field
  return outstr

def get_event_reqd_fields(opp, org):
  """Fields required by Google Base, note that they aren't necessarily used by the FP app."""
  outstr = output_tag_value(opp, "title")
  outstr += FIELDSEP + output_tag_value(opp, "description")
  outstr += FIELDSEP + output_field("link", "http://change.gov/")
  outstr += FIELDSEP + output_field("image_link", xml_helpers.getTagValue(org, "logoURL"))
  return outstr

def get_feed_fields(feedinfo):
  """Fields from the <Feed> portion of FPXML."""
  outstr = output_tag_value(feedinfo, "feedID")
  outstr += FIELDSEP + output_tag_value_renamed(feedinfo, "providerID", "feed_providerID")
  outstr += FIELDSEP + output_tag_value_renamed(feedinfo, "providerName", "feed_providerName")
  outstr += FIELDSEP + output_tag_value_renamed(feedinfo, "providerURL", "feed_providerURL")
  outstr += FIELDSEP + output_tag_value_renamed(feedinfo, "description", "feed_description")
  outstr += FIELDSEP + output_tag_value_renamed(feedinfo, "createdDateTime", "feed_createdDateTime")
  return outstr

GEOCODE_DEBUG = False
GEOCODE_CACHE = None
GEOCODE_CACHE_FN = "geocode_cache.txt"
def geocode(addr, retries=4):
  """convert a string addr to a "lat,long" string"""
  global GEOCODE_CACHE
  loc = addr.lower().strip()
  loc = re.sub(r'^[^0-9a-z]+', r'', loc)
  loc = re.sub(r'[^0-9a-z]+$', r'', loc)
  loc = re.sub(r'\s\s+', r' ', loc)

  if GEOCODE_CACHE == None:
    GEOCODE_CACHE = {}
    geocode_fh = open(GEOCODE_CACHE_FN, "r")
    try:
      for line in geocode_fh:
        if "|" in line:
          key, val = line.split("|")
          key = re.sub(r'\s\s+', r' ', key)
          GEOCODE_CACHE[key.lower().strip()] = val.strip()
          if GEOCODE_DEBUG and len(GEOCODE_CACHE) % 250 == 0:
            print "read", len(GEOCODE_CACHE), "geocode cache entries."
    finally:
      geocode_fh.close()
  if loc in GEOCODE_CACHE:
    return GEOCODE_CACHE[loc]

  # geocode with google maps, and cache responses
  params = urllib.urlencode(
    {'q':loc.lower(), 'output':'csv',
     'oe':'utf8', 'sensor':'false',
     'key':'ABQIAAAAxq97AW0x5_CNgn6-nLxSrxQuOQhskTx7t90ovP5xOuY' + \
       '_YrlyqBQajVan2ia99rD9JgAcFrdQnTD4JQ'})
  if GEOCODE_DEBUG:
    print datetime.now(), "geocoding '" + loc + "'..."
  maps_fh = urllib.urlopen("http://maps.google.com/maps/geo?%s" % params)
  res = maps_fh.readline()
  maps_fh.close()
  if GEOCODE_DEBUG:
    print datetime.now(), "response: "+res
  if "," not in res:
    # fail and also don't cache
    return ""
  try:
    respcode, zoom, lat, lng = res.split(",")
  except:
    if GEOCODE_DEBUG:
      print datetime.now(), "unparseable response: "+res[0:80]
    respcode, zoom, lat, lng = 999, 0, 0, 0
    zoom = zoom  # shutup pylint

  respcode = int(respcode)
  if respcode == 500 or respcode == 620:
    if GEOCODE_DEBUG:
      print datetime.now(), "geocoder quota exceeded-- sleeping..."
    time.sleep(1)
    return geocode(addr, retries - 1)

  # these results get cached
  val = ""
  if respcode == 200:
    val = lat + "," + lng
  GEOCODE_CACHE[loc] = val
  geocode_fh = open(GEOCODE_CACHE_FN, "a")
  cacheline = loc + "|" + val
  if PROGRESS:
    print datetime.now(), "storing cacheline:", cacheline
  geocode_fh.write(cacheline + "\n")
  geocode_fh.close()
  return val

def output_opportunity(opp, feedinfo, known_orgs, totrecs):
  """main function for outputting a complete opportunity."""
  outstr = ""
  opp_id = xml_helpers.getTagValue(opp, "volunteerOpportunityID")
  if (opp_id == ""):
    print datetime.now(), "no opportunityID"
    return totrecs, ""
  org_id = xml_helpers.getTagValue(opp, "sponsoringOrganizationID")
  if (org_id not in known_orgs):
    print datetime.now(), "unknown sponsoringOrganizationID: " + org_id + ".  skipping opportunity " + opp_id
    return totrecs, ""
  org = known_orgs[org_id]
  opp_locations = opp.getElementsByTagName("location")
  opp_times = opp.getElementsByTagName("dateTimeDuration")
  repeated_fields = FIELDSEP + get_feed_fields(feedinfo)
  repeated_fields += FIELDSEP + get_event_reqd_fields(opp, org)
  repeated_fields += FIELDSEP + get_base_other_fields(opp, org)
  repeated_fields += FIELDSEP + get_direct_mapped_field(opp, org)
  if len(opp_times) == 0:
    opp_times = [ None ]
  for opptime in opp_times:
    if opptime == None:
      startend = convert_dt_to_gbase("1971-01-01", "00:00:00-00:00", "UTC")
      openended = "Yes"
    else:
      # event_date_range
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
      start_date = xml_helpers.getTagValue(opptime, "startDate")
      start_time = xml_helpers.getTagValue(opptime, "startTime")
      end_date = xml_helpers.getTagValue(opptime, "endDate")
      end_time = xml_helpers.getTagValue(opptime, "endTime")
      openended = xml_helpers.getTagValue(opptime, "openEnded")
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
      if (start_date == ""):
        start_date = "1971-01-01"
        start_time = "00:00:00-00:00"
      startend = convert_dt_to_gbase(start_date, start_time, "UTC")
      if (end_date != "" and end_date + end_time > start_date + start_time):
        startend += "/"
        startend += convert_dt_to_gbase(end_date, end_time, "UTC")
    duration = xml_helpers.getTagValue(opptime, "duration")
    hrs_per_week = xml_helpers.getTagValue(opptime, "commitmentHoursPerWeek")
    time_fields = FIELDSEP + output_field("openended", openended)
    time_fields += FIELDSEP + output_field("duration", duration)
    time_fields += FIELDSEP + output_field("commitmentHoursPerWeek", hrs_per_week)
    time_fields += FIELDSEP + output_field("event_date_range", startend)
    if len(opp_locations) == 0:
      opp_locations = [ None ]
    for opploc in opp_locations:
      totrecs = totrecs + 1
      if PROGRESS and totrecs % 250 == 0:
        print datetime.now(), ": ", totrecs, " records generated."
      if opploc == None:
        locstr, latlong, geocoded_loc = ("", "", "")
        loc_fields = FIELDSEP + output_field("location", "0.0")
        loc_fields += FIELDSEP + output_field("latitude", "0.0")
        loc_fields += FIELDSEP + output_field("longitude", "0.0")
        loc_fields += FIELDSEP + output_field("location_string", "")
        loc_fields += FIELDSEP + output_field("venue_name", "")
      else:
        locstr, latlong, geocoded_loc = lookup_loc_fields(opploc)
        lat = lng = "0.0"
        if latlong != "":
          lat, lng = latlong.split(",")
        loc_fields = FIELDSEP + output_field("location", "")
        loc_fields += FIELDSEP + output_field("latitude", str(float(lat)+1000.0))
        loc_fields += FIELDSEP + output_field("longitude", str(float(lng)+1000.0))
        loc_fields += FIELDSEP + output_field("location_string", geocoded_loc)
        loc_fields += FIELDSEP + output_field("venue_name", xml_helpers.getTagValue(opploc, "name"))
      #if locstr != geocoded_loc:
      #  #print datetime.now(), "locstr: ", locstr, " geocoded_loc: ", geocoded_loc
      #  descs = opp.getElementsByTagName("description")
      #  encoded_locstr = escape(locstr)
      #  encoded_locstr = unicode(encoded_locstr,errors="ignore")
      #  encoded_locstr = encoded_locstr.encode('utf-8', "ignore")
      #  descs[0].firstChild.data += ". detailed location information: " + encoded_locstr
      opp_id = compute_stable_id(opp, org, locstr, openended, duration,
                           hrs_per_week, startend)
      outstr += output_field("id", opp_id)
      outstr += repeated_fields
      outstr += time_fields
      outstr += loc_fields
      outstr += RECORDSEP
  return totrecs, outstr

def output_header(feedinfo, opp, org):
  """fake opportunity printer, which prints the header line instead."""
  global PRINTHEAD
  PRINTHEAD = True
  outstr = output_field("id", "")
  repeated_fields = FIELDSEP + get_feed_fields(feedinfo)
  repeated_fields += FIELDSEP + get_event_reqd_fields(opp, org)
  repeated_fields += FIELDSEP + get_base_other_fields(opp, org)
  repeated_fields += FIELDSEP + get_direct_mapped_field(opp, org)
  time_fields = FIELDSEP + output_field("openended", "")
  time_fields += FIELDSEP + output_field("duration", "")
  time_fields += FIELDSEP + output_field("commitmentHoursPerWeek", "")
  time_fields += FIELDSEP + output_field("event_date_range", "")
  loc_fields = FIELDSEP + output_field("location", "")
  loc_fields += FIELDSEP + output_field("latitude", "")
  loc_fields += FIELDSEP + output_field("longitude", "")
  loc_fields += FIELDSEP + output_field("location_string", "")
  loc_fields += FIELDSEP + output_field("venue_name", "")
  loc_fields += RECORDSEP
  PRINTHEAD = False
  return outstr + repeated_fields + time_fields + loc_fields

def convert_to_footprint_xml(instr, do_fastparse, maxrecs, progress):
  """macro for parsing an FPXML string to XML then format it."""
  if False:
    # grr: RAM explosion, even with pulldom...
    totrecs = 0
    nodes = xml.dom.pulldom.parseString(instr)
    outstr = '<?xml version="1.0" ?>'
    outstr += '<FootprintFeed schemaVersion="0.1">'
    for eltype, node in nodes:
      if eltype == 'START_ELEMENT':
        if node.nodeName == 'VolunteerOpportunity':
          if progress and totrecs > 0 and totrecs % 250 == 0:
            print datetime.now(), ": ", totrecs, " opps processed."
          totrecs = totrecs + 1
          if maxrecs > 0 and totrecs > maxrecs:
            break
        if (node.nodeName == 'FeedInfo' or
            node.nodeName == 'Organization' or
            node.nodeName == 'VolunteerOpportunity'):
          nodes.expandNode(node)
          prettyxml = xml_helpers.prettyxml(node)
          outstr += prettyxml
    outstr += '</FootprintFeed>'
    return outstr
  if do_fastparse:
    return parse_footprint.ParseFast(instr, maxrecs, progress)
  else:
    # slow parse
    xmldoc = parse_footprint.parse(instr, maxrecs, progress)
    # TODO: maxrecs
    return xml_helpers.prettyxml(xmldoc)

def convert_to_gbase_events_type(instr, do_fastparse, maxrecs, progress):
  """non-trivial logic for converting FPXML to google base formatting."""
  # todo: maxrecs
  outstr = ""
  if progress:
    print datetime.now(), "convert_to_gbase_events_type..."

  example_org = None
  known_orgs = {}
  if do_fastparse:
    known_elnames = [ 'FeedInfo', 'FootprintFeed', 'Organization', 'Organizations', 'VolunteerOpportunities', 'VolunteerOpportunity', 'abstract', 'audienceTag', 'audienceTags', 'categoryTag', 'categoryTags', 'city', 'commitmentHoursPerWeek', 'contactEmail', 'contactName', 'contactPhone', 'country', 'createdDateTime', 'dateTimeDuration', 'dateTimeDurationType', 'dateTimeDurations', 'description', 'detailURL', 'directions', 'donateURL', 'duration', 'email', 'endDate', 'endTime', 'expires', 'fax', 'feedID', 'guidestarID', 'iCalRecurrence', 'language', 'latitude', 'lastUpdated', 'location', 'locationType', 'locations', 'logoURL', 'longitude', 'minimumAge', 'missionStatement', 'name', 'nationalEIN', 'openEnded', 'organizationID', 'organizationURL', 'paid', 'phone', 'postalCode', 'providerID', 'providerName', 'providerURL', 'region', 'schemaVersion', 'sexRestrictedEnum', 'sexRestritedTo', 'skills', 'sponsoringOrganizationID', 'startDate', 'startTime', 'streetAddress1', 'streetAddress2', 'streetAddress3', 'title', 'tzOlsonPath', 'virtual', 'volunteerHubOrganizationID', 'volunteerOpportunityID', 'volunteersFilled', 'volunteersSlots', 'volunteersNeeded', 'yesNoEnum', ]
    totrecs = 0
    # note: preserves order, so diff works (vs. one sweep per element type)
    chunks = re.findall(r'<(?:Organization|VolunteerOpportunity|FeedInfo)>.+?</(?:Organization|VolunteerOpportunity|FeedInfo)>', instr, re.DOTALL)
    for chunk in chunks:
      node = xml_helpers.simpleParser(chunk, known_elnames, False)
      if re.search("<FeedInfo>", chunk):
        if progress:
          print datetime.now(), ": feedinfo seen."
        feedinfo = xml_helpers.simpleParser(chunk, known_elnames, False)
        continue
      if re.search("<Organization>", chunk):
        if progress and len(known_orgs) % 250 == 0:
          print datetime.now(), ": ", len(known_orgs), " organizations seen."
        org = xml_helpers.simpleParser(chunk, known_elnames, False)
        org_id = xml_helpers.getTagValue(org, "organizationID")
        if (org_id != ""):
          known_orgs[org_id] = org
        if example_org == None:
          example_org = org
        continue
      if re.search("<VolunteerOpportunity>", chunk):
        opp = xml_helpers.simpleParser(chunk, None, False)
        if totrecs == 0:
          outstr += output_header(feedinfo, node, example_org)
        totrecs, spiece = output_opportunity(opp, feedinfo, known_orgs, totrecs)
        outstr += spiece
        if (maxrecs > 0 and totrecs > maxrecs):
          break
    if progress:
      print datetime.now(), totrecs, "opportunities found."
    #totrecs = 0
    #nodes = xml.dom.pulldom.parseString(instr)
    #example_org = None
    #for type,node in nodes:
    #  if type == 'START_ELEMENT':
    #    if node.nodeName == 'FeedInfo':
    #      nodes.expandNode(node)
    #      feedinfo = node
    #    elif node.nodeName == 'Organization':
    #      nodes.expandNode(node)
    #      id = xml_helpers.getTagValue(node, "organizationID")
    #      if (id != ""):
    #        known_orgs[id] = node
    #      if example_org == None:
    #        example_org = node
    #    elif node.nodeName == 'VolunteerOpportunity':
    #      nodes.expandNode(node)
    #      if totrecs == 0:
    #        outstr += output_header(feedinfo, node, example_org)
    #      totrecs, spiece = output_opportunity(node, feedinfo, known_orgs, totrecs)
    #      outstr += spiece
  else:
    # not do_fastparse
    footprint_xml = parse_footprint.parse(instr, maxrecs, progress)
    
    feedinfos = footprint_xml.getElementsByTagName("FeedInfo")
    if (feedinfos.length != 1):
      print datetime.now(), "bad FeedInfo: should only be one section"
      # TODO: throw error
      sys.exit(1)
    feedinfo = feedinfos[0]
    organizations = footprint_xml.getElementsByTagName("Organization")
    for org in organizations:
      org_id = xml_helpers.getTagValue(org, "organizationID")
      if (org_id != ""):
        known_orgs[org_id] = org
    opportunities = footprint_xml.getElementsByTagName("VolunteerOpportunity")
    totrecs = 0
    for opp in opportunities:
      if totrecs == 0:
        outstr += output_header(feedinfo, opp, organizations[0])
      totrecs, spiece = output_opportunity(opp, feedinfo, known_orgs, totrecs)
      outstr += spiece

  return outstr

def ftp_to_base(filename, ftpinfo, instr):
  """ftp the string to base, guessing the feed name from the original filename."""
  ftplib = __import__('ftplib')
  stringio = __import__('StringIO')

  dest_fn = "footprint1.txt"
  if re.search("usa-?service", filename):
    dest_fn = "usaservice1.gz"
  elif re.search("(handson|hot.footprint)", filename):
    dest_fn = "handsonnetwork1.gz"
  elif re.search("(volunteer[.]gov)", filename):
    dest_fn = "volunteergov1.gz"
  elif re.search("idealist", filename):
    dest_fn = "idealist1.gz"
  elif re.search("(userpostings|/export/Posting)", filename):
    dest_fn = "footprint_userpostings1.gz"
  elif re.search("craigslist", filename):
    dest_fn = "craigslist1.gz"
  elif re.search("americorps", filename):
    dest_fn = "americorps1.gz"
  elif re.search("volunteermatch", filename):
    dest_fn = "volunteermatch1.gz"

  if re.search(r'[.]gz$', dest_fn):
    print "compressing data from", len(instr), "bytes"
    gzip_fh = gzip.open(dest_fn, 'wb', 9)
    gzip_fh.write(instr)
    gzip_fh.close()
    data_fh = open(dest_fn, 'rb')
  else:
    data_fh = stringio.StringIO(instr)

  host = 'uploads.google.com'
  (user, passwd) = ftpinfo.split(":")
  print datetime.now(), "connecting to " + host + " as user " + user + "..."
  ftp = ftplib.FTP(host)
  print datetime.now(), "FTP server says:", ftp.getwelcome()
  ftp.login(user, passwd)
  print datetime.now(), "uploading filename", dest_fn
  ftp.storbinary("STOR " + dest_fn, data_fh, 8192)
  print datetime.now(), "done."
  ftp.quit()
  data_fh.close()

  #print datetime.now(), "file:"
  #print s,

def guess_parse_func(inputfmt, filename):
  """from the filename and the --inputfmt,guess the input type and parse func"""
  if inputfmt == "fpxml":
    parsefunc = parse_footprint.parse
  elif (inputfmt == "usaservice" or
        inputfmt == "usasvc" or
        (inputfmt == None and
         re.search("usa-?service", filename))):
    parsefunc = parse_usaservice.parse
  elif (inputfmt == "craigslist" or
        inputfmt == "cl" or
        (inputfmt == None and
         re.search("craigslist", filename))):
    parsefunc = parse_craigslist.parse
  elif (inputfmt == "americorps" or
        (inputfmt == None and
         re.search("americorps", filename))):
    parsefunc = parse_americorps.parse
  elif (inputfmt == "handson" or
        inputfmt == "handsonnetwork"):
    parsefunc = parse_handsonnetwork.parse
  elif (inputfmt == None and
         re.search("(handson|hot.footprint)", filename)):
    # now using FPXML
    #parsefunc = parse_handsonnetwork.ParseFPXML
    parsefunc = parse_footprint.parse
    inputfmt = "fpxml"
  elif (inputfmt == None and
         re.search("(volunteer[.]gov)", filename)):
    parsefunc = parse_footprint.parse
    inputfmt = "fpxml"
  elif (inputfmt == "idealist" or
        (inputfmt == None and
         re.search("idealist", filename))):
    parsefunc = parse_idealist.parse
  elif (inputfmt == "fp_userpostings" or
        (inputfmt == None and
         re.search("(userpostings|/export/Posting)", filename))):
    parsefunc = parse_userpostings.parse
  elif (inputfmt == "volunteermatch" or
        inputfmt == "vm" or
        (inputfmt == None and
         re.search("volunteermatch", filename))):
    parsefunc = parse_volunteermatch.parse
  else:
    print datetime.now(), "unknown input format-- try --inputfmt"
    sys.exit(1)
  return inputfmt, parsefunc


def clean_input_string(instr):
  """run various cleanups for low-level encoding issues."""
  if PROGRESS:
    print datetime.now(), "read file: ", len(instr), " bytes."
  instr = re.sub(r'\r\n?', "\n", instr)
  if PROGRESS:
    print datetime.now(), "filtered dos newlines:", len(instr), " bytes"
  instr = re.sub(r'(?:\t|&#9;)', " ", instr)                                         
  if PROGRESS:
    print datetime.now(), "filtered tabs:", len(instr), " bytes"
  instr = re.sub(r'\xc2?[\x93\x94\222]', "'", instr)
  if PROGRESS:
    print datetime.now(), "filtered iso8859-1 single quotes:", len(instr), " bytes"
  instr = re.sub(r'\xc2?[\223\224]', '"', instr)
  if PROGRESS:
    print datetime.now(), "filtered iso8859-1 double quotes:", len(instr), " bytes"
  instr = re.sub(r'\xc2?[\225\226\227]', "-", instr)
  if PROGRESS:
    print datetime.now(), "filtered iso8859-1 dashes:", len(instr), " bytes"
  instr = xml_helpers.cleanString(instr)
  if PROGRESS:
    print datetime.now(), "filtered nonprintables:", len(instr), " bytes"
  return instr

def parse_options():
  """parse cmdline options"""
  global DEBUG, PROGRESS, GEOCODE_DEBUG, FIELDSEP, RECORDSEP
  parser = OptionParser("usage: %prog [options] sample_data.xml ...")
  parser.set_defaults(geocode_debug=False)
  parser.set_defaults(debug=False)
  parser.set_defaults(progress=False)
  parser.set_defaults(debug_input=False)
  parser.set_defaults(output="basetsv")
  parser.set_defaults(test=False)
  parser.set_defaults(clean=True)
  parser.set_defaults(maxrecs=-1)
  parser.add_option("-d", "--dbg", action="store_true", dest="debug")
  parser.add_option("--clean", action="store_true", dest="clean")
  parser.add_option("--noclean", action="store_false", dest="clean")
  parser.add_option("--inputfmt", action="store", dest="inputfmt")
  parser.add_option("--test", action="store_true", dest="test")
  parser.add_option("--dbginput", action="store_true", dest="debug_input")
  parser.add_option("--progress", action="store_true", dest="progress")
  parser.add_option("--outputfmt", action="store", dest="outputfmt")
  parser.add_option("-g", "--geodbg", action="store_true", dest="geocode_debug")
  parser.add_option("--ftpinfo", dest="ftpinfo")
  parser.add_option("--fs", "--fieldsep", action="store", dest="fs")
  parser.add_option("--rs", "--recordsep", action="store", dest="rs")
  parser.add_option("-n", "--maxrecords", action="store", dest="maxrecs")
  (options, args) = parser.parse_args(sys.argv[1:])
  if (len(args) == 0):
    parser.print_help()
    sys.exit(0)
  if options.fs != None:
    FIELDSEP = options.fs
  if options.rs != None:
    RECORDSEP = options.rs
  if (options.debug):
    DEBUG = True
    GEOCODE_DEBUG = True
    PROGRESS = True
    FIELDSEP = "\n"
  if (options.geocode_debug):
    GEOCODE_DEBUG = True
  if options.test:
    options.progress = True
  if (options.progress):
    PROGRESS = True
  return options, args

def main():
  """main function for cmdline execution."""
  options, args = parse_options()
  filename = args[0]
  options.inputfmt, parsefunc = guess_parse_func(options.inputfmt, filename)

  if re.search(r'^https?://', filename):
    if PROGRESS:
      print datetime.now(), "starting download..."
    outfh = urllib.urlopen(filename)
    if (re.search(r'[.]gz$', filename)):
      # is there a way to fetch and unzip an URL in one shot?
      content = outfh.read()
      outfh.close()
      tmp_fn = "/tmp/tmp-"+hashlib.md5().hexdigest()
      tmpfh = open(tmp_fn, "wb+")
      tmpfh.write(content)
      tmpfh.close()
      outfh = gzip.open(tmp_fn, 'rb')
    if PROGRESS:
      print datetime.now(), "done."
  elif re.search(r'[.]gz$', filename):
    outfh = gzip.open(filename, 'rb')
  elif filename == "-":
    outfh = sys.stdin
  else:
    outfh = open(filename, 'rb')
  if PROGRESS:
    print datetime.now(), "reading file..."
  instr = outfh.read()

  # remove tabs and nonprintable junk
  if options.clean:
    instr = clean_input_string(instr)

  if (options.debug_input):
    # split nasty XML inputs, to help isolate problems
    instr = re.sub(r'><', r'>\n<', instr)

  if options.inputfmt == "fpxml":
    footprint_xmlstr = instr
  else:
    if PROGRESS:
      print datetime.now(), "parsing..."
    footprint_xmlstr = parsefunc(instr, int(options.maxrecs), PROGRESS)

  if options.test:
    print datetime.now(), "testing input: generating Footprint XML..."
    # free some RAM
    del instr
    fpxml = convert_to_footprint_xml(footprint_xmlstr, True, int(options.maxrecs), True)
    # free some RAM
    del footprint_xmlstr
    print datetime.now(), "testing input: parsing and regenerating Footprint XML..."
    fpxml2 = convert_to_footprint_xml(fpxml, True, int(options.maxrecs), True)
    print datetime.now(), "testing input: comparing outputs..."
    hash1 = hashlib.md5(fpxml).hexdigest()
    hash2 = hashlib.md5(fpxml2).hexdigest()
    fn1 = "/tmp/pydiff-"+hash1
    fn2 = "/tmp/pydiff-"+hash2
    if hash1 == hash2:
      print datetime.now(), "success:  getting head...\n"
      outfh = open(fn1, "w+")
      outfh.write(fpxml)
      outfh.close()
      subprocess.call(['head', fn1])
    else:
      print datetime.now(), "errors-- hash1=" + hash1 + " hash2=" + \
          hash2 + " running diff", fn1, fn2
      outfh = open(fn1, "w+")
      outfh.write(fpxml)
      outfh.close()
      outfh = open(fn2, "w+")
      outfh.write(fpxml2)
      outfh.close()
      subprocess.call(['diff', fn1, fn2])
      # grr-- difflib performance sucks
      #for line in difflib.unified_diff(fpxml, fpxml2, fromfile='(first output)', tofile='(second output)'):
      #print line
    sys.exit(0)

  do_fastparse = not options.debug_input
  if options.outputfmt == "fpxml":
    # TODO: pretty printing option
    print convert_to_footprint_xml(footprint_xmlstr, do_fastparse, int(options.maxrecs), PROGRESS)
    sys.exit(0)

  if options.outputfmt == "basetsv" or options.ftpinfo:
    outstr = convert_to_gbase_events_type(footprint_xmlstr, do_fastparse, int(options.maxrecs), PROGRESS)
  #coming soon... footprint vertical for Base...
  #elif options.outputfmt == "fpbasetsv":
  #  outstr = convertToGoogleBaseVolunteerType(footprint_xmlstr, do_fastparse, int(options.maxrecs), PROGRESS)
  else:
    print datetime.now(), "--outputfmt not implemented: try 'basetsv', 'fpbasetsv' or 'fpxml'"
    sys.exit(1)

  #only need this if Base quoted fields it enabled
  #outstr = re.sub(r'"', r'&quot;', outstr)
  if (options.ftpinfo):
    ftp_to_base(filename, options.ftpinfo, outstr)
  else:
    print outstr,

if __name__ == "__main__":
  main()
