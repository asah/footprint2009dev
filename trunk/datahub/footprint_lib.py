#!/usr/bin/python
# Copyright 2009 Google Inc.  All Rights Reserved.
#

#from xml.dom.ext import PrettyPrint
from xml.sax.saxutils import escape
import gzip
import zlib
import difflib
import hashlib
import urllib
import re
from datetime import datetime
import parse_footprint
import parse_usaservice
import parse_handsonnetwork
import parse_idealist
import parse_volunteermatch
import os
import subprocess
import sys
import time
import xml_helpers
import xml.dom.pulldom

import dateutil
import dateutil.tz
import dateutil.parser

FIELDSEP = "\t"
RECORDSEP = "\n"

debug = False
progress = False
printhead = False

fieldtypes = {
  "title":"builtin", "description":"builtin", "link":"builtin", "event_type":"builtin", "quantity":"builtin", "image_link":"builtin","event_date_range":"builtin","id":"builtin","location":"builtin",
  "paid":"boolean","openended":"boolean",
  'volunteersSlots':'integer','volunteersFilled':'integer','volunteersNeeded':'integer','minimumAge':'integer',"commitmentHoursPerWeek":'integer',
  'providerURL':'URL','detailURL':'URL','org_organizationURL':'URL','org_logoURL':'URL','org_providerURL':'URL','feed_providerURL':'URL',
  'lastUpdated':'dateTime','expires':'dateTime','feed_createdDateTime':'dateTime',
  # note: type 'location' isn't safe because the Base geocoder can fail, causing the record to be rejected
  "duration":"string","abstract":"string","sexRestrictedTo":"string","skills":"string","contactName":"string","contactPhone":"string","contactEmail":"string","language":"string",'org_name':"string",'org_missionStatement':"string",'org_description':"string",'org_phone':"string",'org_fax':"string",'org_email':"string",'categories':"string",'audiences':"string","commitmentHoursPerWeek":"string","employer":"string","feed_providerName":"string","feed_description":"string",'providerID':'string','feed_providerID':'string','feedID':'string','opportunityID':'string','organizationID':'string','sponsoringOrganizationID':'strng','volunteerHubOrganizationID':'string','org_nationalEIN':'string','org_guidestarID':'string','venue_name':'string',"location_string":"string","orgLocation":"string",
}

# Google Base uses ISO8601... in PST -- I kid you not:
# http://base.google.com/support/bin/answer.py?answer=78170&hl=en#Events%20and%20Activities
# and worse, you have to change an env var in python...
def cvtDateTimeToGoogleBase(datestr, timestr, tz):
  # datestr = YYYY-MM-DD
  # timestr = HH:MM:SS
  # tz = America/New_York
  try:
    tzinfo = dateutil.tz.tzstr(tz)
  except:
    tzinfo = dateutil.tz.tzutc()
  ts = dateutil.parser.parse(datestr + " " + timestr)
  ts = ts.replace(tzinfo=tzinfo)
  pst = dateutil.tz.tzstr("PST8PDT")
  ts = ts.astimezone(pst)
  res = ts.strftime("%Y-%m-%dT%H:%M:%S")
  res = re.sub(r'Z$', '', res)
  return res

csv_repeated_fields = ['categories','audiences',]
direct_map_fields = ['opportunityID','organizationID','abstract','volunteersSlots','volunteersFilled','volunteersNeeded','minimumAge','sexRestrictedTo','skills','contactName','contactPhone','contactEmail','providerURL','language','lastUpdated','expires','detailURL']
organization_fields = ['nationalEIN','guidestarID','name','missionStatement','description','phone','fax','email','organizationURL','logoURL','providerURL',]
def value(n):
  if (n.firstChild != None):
    return n.firstChild.data.replace(",", "")
  else:
    return ""

def flattenFieldToCSV(field):
  #print field
  return ",".join(filter(lambda x: x != "", map(value, field.childNodes)))

def outputField(name, value):
  global printhead, debug
  if printhead == True:
    if (name not in fieldtypes):
      print datetime.now(),"no type for field: " + name + fieldtypes[name]
      exit(1)
    elif (fieldtypes[name] == "builtin"):
      return name
    else:
      return "c:"+name+":"+fieldtypes[name]
  if debug:
    if (len(value) > 70):
      value = value[0:67] + "..."
    return name.rjust(22) + " : " + value
  if (fieldtypes[name] == "dateTime"):
    return cvtDateTimeToGoogleBase(value, "", "UTC")
  return value

def addrField(node, field):
  addr = xml_helpers.getTagValue(node, field)
  if addr != "":
    addr += " "
  return addr
  
def cityLocationFields(node):
  # note: avoid commas, so it works with CSV
  # (this is good enough for the geocoder)
  loc = ""
  loc += addrField(node, "city")
  loc += addrField(node, "region")
  loc += addrField(node, "postalCode")
  loc += addrField(node, "country")
  return loc

def computeLocationField(node):
  loc = ""
  addr1 = addrField(node, "streetAddress1")
  addr2 = addrField(node, "streetAddress2")
  adde3 = addrField(node, "streetAddress3")
  return loc

def lookupLocationFields(node):
  global debug
  loc = addrField(node, "streetAddress1")
  loc += addrField(node, "streetAddress2")
  loc += addrField(node, "streetAddress3")
  loc += cityLocationFields(node)
  fullloc = loc
  latlong = xml_helpers.getTagValue(node, "latitude") + ","
  latlong += xml_helpers.getTagValue(node, "longitude")
  if latlong == ",":
    latlong = geocode(loc)
  if latlong == "":
    # sometimes address1 contains un-geocodable descriptive language,
    # e.g. venue name, "around the corner from ..." etc.
    loc = addrField(node, "streetAddress2")
    loc += addrField(node, "streetAddress3")
    loc += cityLocationFields(node)
    latlong = geocode(loc)
  if latlong == "":
    # rarely, addr1 & addr are both descriptive
    loc = addrField(node, "streetAddress3")
    loc += cityLocationFields(node)
    latlong = geocode(loc)
  if latlong == "":
    # missing or bogus address lines
    loc = cityLocationFields(node)
    latlong = geocode(loc)
  if latlong == "":
    # missing or bogus city name
    loc = addrField(node, "postalCode")
    loc += addrField(node, "country")
  if latlong == "":
    # missing or bogus postalcode
    loc = addrField(node, "city")
    loc += addrField(node, "region")
    loc += addrField(node, "country")
  if debug:
    print datetime.now(),"geocode: "+loc+"="+latlong
  return (fullloc, latlong, loc)

def outputLocationField(node, mapped_name):
  return outputField(mapped_name, computeLocationField(node)+cityLocationFields(node))

def outputTagValue(node, fieldname):
  return outputField(fieldname, xml_helpers.getTagValue(node, fieldname))

def outputTagValueRenamed(node, xmlname, fieldname):
  return outputField(fieldname, xml_helpers.getTagValue(node, xmlname))

def computeStableId(opp, org, locstr, openended, duration,
                    commitmentHoursPerWeek, startend):
  eid = xml_helpers.getTagValue(org, "nationalEIN");
  if (eid == ""):
    # support informal "organizations" that lack EINs
    eid = xml_helpers.getTagValue(org, "organizationURL")
  # TODO: if two providers have same listing, good odds the
  # locations will be slightly different...
  loc = locstr

  # TODO: if two providers have same listing, the time info
  # is unlikely to be exactly the same, incl. missing fields
  timestr = openended + duration + commitmentHoursPerWeek + startend
  return hashlib.md5(eid + loc + timestr).hexdigest()

def getDirectMappedField(opp, org):
  s = ""
  paid = xml_helpers.getTagValue(opp, "paid")
  if (paid == "" or paid.lower()[0] != "y"):
    paid = "n"
  else:
    paid = "y"
  s += outputField("paid", paid)
  for field in direct_map_fields:
    s += FIELDSEP + outputTagValue(opp, field)
  for field in organization_fields:
    s += FIELDSEP + outputField("org_"+field, xml_helpers.getTagValue(org, field))
  for field in csv_repeated_fields:
    s += FIELDSEP
    l = opp.getElementsByTagName(field)
    val = ""
    if (l.length > 0):
      val = flattenFieldToCSV(l[0])
    s += outputField(field, val)
  # orgLocation
  s += FIELDSEP
  l = opp.getElementsByTagName(field)
  if (l.length > 0):
    s += outputLocationField(l[0], "orgLocation")
  else:
    s += outputField("orgLocation", "")

  return s

# these are fields that exist in other Base schemas-- for the sake of
# possible syndication, we try to make ourselves look like other Base
# feeds.  Since we're talking about a small overlap, these fields are
# populated *as well as* direct mapping of the footprint XML fields.
# 
def getBaseOtherFields(opp, org):
  s = outputField("quantity", xml_helpers.getTagValue(opp, "volunteersNeeded"))
  s += FIELDSEP + outputField("employer", xml_helpers.getTagValue(org, "name"))
  # don't map expiration_date -- Base has strict limits (e.g. 2 weeks) on this field
  return s

def getBaseEventRequiredFields(opp, org):
  s = outputTagValue(opp, "title")
  s += FIELDSEP + outputTagValue(opp, "description")
  s += FIELDSEP + outputField("link", "http://change.gov/")
  s += FIELDSEP + outputField("image_link", xml_helpers.getTagValue(org, "logoURL"))
  s += FIELDSEP + outputField("event_type", "volunteering")
  return s

def getFeedFields(feedinfo):
  s = outputTagValue(feedinfo, "feedID")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "providerID", "feed_providerID")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "providerName", "feed_providerName")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "providerURL", "feed_providerURL")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "description", "feed_description")
  s += FIELDSEP + outputTagValueRenamed(feedinfo, "createdDateTime", "feed_createdDateTime")
  return s

geocode_debug = False
geocode_cache = None
def geocode(addr, retries=4):
  global geocode_debug, geocode_cache
  loc = addr.lower().strip()
  loc = re.sub(r'^[^0-9a-z]+', r'', loc)
  loc = re.sub(r'[^0-9a-z]+$', r'', loc)
  loc = re.sub(r'\s\s+', r' ', loc)

  if geocode_cache == None:
    geocode_cache = {}
    fh = open("geocode_cache.txt", "r")
    try:
      for line in fh:
        if "|" in line:
          key,val = line.split("|")
          key = re.sub(r'\s\s+', r' ', key)
          geocode_cache[key.lower().strip()] = val.strip()
          if geocode_debug and len(geocode_cache)%250==0:
            print "read",len(geocode_cache),"geocode cache entries."
    finally:
      fh.close()
  if loc in geocode_cache:
    return geocode_cache[loc]

  # geocode with google maps, and cache responses
  params = urllib.urlencode({'q':loc.lower(), 'output':'csv',
                             'oe':'utf8', 'sensor':'false',
                             'key':'ABQIAAAAxq97AW0x5_CNgn6-nLxSrxQuOQhskTx7t90ovP5xOuY_YrlyqBQajVan2ia99rD9JgAcFrdQnTD4JQ'})
  if geocode_debug:
    print datetime.now(),"geocoding '"+loc+"'..."
  f = urllib.urlopen("http://maps.google.com/maps/geo?%s" % params)
  res = f.readline()
  if geocode_debug:
    print datetime.now(),"response: "+res
  if "," not in res:
    # fail and also don't cache
    return ""
  try:
    respcode,zoom,lat,long = res.split(",")
  except:
    if geocode_debug:
      print datetime.now(),"unparseable response: "+res[0:80]
    respcode,zoom,lat,long = 999,0,0,0

  respcode = int(respcode)
  if respcode == 500 or respcode == 620:
    if geocode_debug:
      print datetime.now(),"geocoder quota exceeded-- sleeping..."
    time.sleep(1)
    return geocode(addr, retries-1)

  # these results get cached
  val = ""
  if respcode == 200:
    val = lat+","+long
  geocode_cache[loc] = val
  fh = open("geocode_cache.txt", "a")
  cacheline = loc + "|" + val
  if progress:
    print datetime.now(),"storing cacheline:", cacheline
  fh.write(cacheline + "\n")
  fh.close()
  return val

def outputOpportunity(opp, feedinfo, known_orgs, totrecs):
  s = ""
  id = xml_helpers.getTagValue(opp, "volunteerOpportunityID")
  if (id == ""):
    print datetime.now(),"no opportunityID"
    return totrecs,""
  org_id = xml_helpers.getTagValue(opp, "sponsoringOrganizationID")
  if (org_id not in known_orgs):
    print datetime.now(),"unknown org_id: " + org_id + ".  skipping opportunity " + id
    return totrecs,""
  org = known_orgs[org_id]
  opp_locations = opp.getElementsByTagName("location")
  opp_times = opp.getElementsByTagName("dateTimeDuration")
  repeatedFields = FIELDSEP + getFeedFields(feedinfo)
  repeatedFields += FIELDSEP + getBaseEventRequiredFields(opp, org)
  repeatedFields += FIELDSEP + getBaseOtherFields(opp, org)
  repeatedFields += FIELDSEP + getDirectMappedField(opp, org)
  for opptime in opp_times:
    # event_date_range
    # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
    startDate = xml_helpers.getTagValue(opptime, "startDate")
    startTime = xml_helpers.getTagValue(opptime, "startTime")
    endDate = xml_helpers.getTagValue(opptime, "endDate")
    endTime = xml_helpers.getTagValue(opptime, "endTime")
    openended = xml_helpers.getTagValue(opptime, "openEnded")
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
    if (startDate == ""):
      startDate = "1971-01-01"
      startTime = "00:00:00-00:00"
    startend = cvtDateTimeToGoogleBase(startDate, startTime, "UTC")
    if (endDate != "" and endDate+endTime > startDate+startTime):
      startend += "/"
      startend += cvtDateTimeToGoogleBase(endDate, endTime, "UTC")
    duration = xml_helpers.getTagValue(opptime, "duration")
    commitmentHoursPerWeek = xml_helpers.getTagValue(opptime, "commitmentHoursPerWeek")
    timeFields = FIELDSEP + outputField("openended", openended)
    timeFields += FIELDSEP + outputField("duration", duration)
    timeFields += FIELDSEP + outputField("commitmentHoursPerWeek", commitmentHoursPerWeek)
    timeFields += FIELDSEP + outputField("event_date_range", startend)
    for opploc in opp_locations:
      totrecs = totrecs + 1
      if progress and totrecs%250==0:
        print datetime.now(),": ",totrecs," records generated."
      locstr,latlong,geocoded_loc = lookupLocationFields(opploc)
      locFields = FIELDSEP + outputField("location", latlong)
      locFields += FIELDSEP + outputField("location_string", geocoded_loc)
      locFields += FIELDSEP + outputField("venue_name", xml_helpers.getTagValue(opploc, "name"))
      #if locstr != geocoded_loc:
      #  #print datetime.now(),"locstr: ", locstr, " geocoded_loc: ", geocoded_loc
      #  descs = opp.getElementsByTagName("description")
      #  encoded_locstr = escape(locstr)
      #  encoded_locstr = unicode(encoded_locstr,errors="ignore")
      #  encoded_locstr = encoded_locstr.encode('utf-8', "ignore")
      #  descs[0].firstChild.data += ". detailed location information: " + encoded_locstr
      id = computeStableId(opp, org, locstr, openended, duration,
                           commitmentHoursPerWeek, startend)
      s += outputField("id", id)
      s += repeatedFields
      s += timeFields
      s += locFields
      s += RECORDSEP
  return totrecs, s

def outputHeader(feedinfo, opp, org):
  global printhead
  printhead = True
  s = outputField("id", "")
  # repeatedFields (see below)
  s += FIELDSEP + getFeedFields(feedinfo)
  s += FIELDSEP + getBaseEventRequiredFields(opp, org)
  s += FIELDSEP + getBaseOtherFields(opp, org)
  s += FIELDSEP + getDirectMappedField(opp, org)
  # timeFields
  s += FIELDSEP + outputField("openended", "")
  s += FIELDSEP + outputField("duration", "")
  s += FIELDSEP + outputField("commitmentHoursPerWeek", "")
  s += FIELDSEP + outputField("event_date_range", "")
  # locFields
  s += FIELDSEP + outputField("location", "")
  s += FIELDSEP + outputField("location_string", "")
  s += FIELDSEP + outputField("venue_name", "")
  s += RECORDSEP
  printhead = False
  return s

def convertToFootprintXML(instr, do_fastparse, maxrecs, progress):
  if False:
    # grr: RAM explosion, even with pulldom...
    totrecs = 0
    nodes = xml.dom.pulldom.parseString(instr)
    outstr = '<?xml version="1.0" ?>'
    outstr += '<FootprintFeed schemaVersion="0.1">'
    for type,node in nodes:
      if type == 'START_ELEMENT':
        if node.nodeName == 'VolunteerOpportunity':
          if progress and totrecs>0 and totrecs%250==0:
            print datetime.now(),": ",totrecs," opps processed."
          totrecs = totrecs + 1
          if maxrecs > 0 and totrecs > maxrecs:
            break
        if (node.nodeName == 'FeedInfo' or
            node.nodeName == 'Organization' or
            node.nodeName == 'VolunteerOpportunity'):
          nodes.expandNode(node)
          s = xml_helpers.prettyxml(node)
          outstr += s
    outstr += '</FootprintFeed>'
    return outstr
  if do_fastparse:
    return parse_footprint.ParseFast(instr, maxrecs, progress)
  else:
    # slow parse
    xmldoc = parse_footprint.Parse(instr, maxrecs, progress)
    # TODO: maxrecs
    return xml_helpers.prettyxml(xmldoc)

def convertToGoogleBaseEventsType(instr, do_fastparse, maxrecs, progress):
  # todo: maxrecs
  global debug
  s = ""
  if progress:
    print datetime.now(),"convertToGoogleBaseEventsType..."

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
          print datetime.now(),": feedinfo seen."
        feedinfo = xml_helpers.simpleParser(chunk, known_elnames, False)
        continue
      if re.search("<Organization>", chunk):
        if progress and len(known_orgs)%250==0:
          print datetime.now(),": ",len(known_orgs)," organizations seen."
        org = xml_helpers.simpleParser(chunk, known_elnames, False)
        id = xml_helpers.getTagValue(org, "organizationID")
        if (id != ""):
          known_orgs[id] = org
        if example_org == None:
          example_org = org
        continue
      if re.search("<VolunteerOpportunity>", chunk):
        opp = xml_helpers.simpleParser(chunk, None, False)
        if totrecs == 0:
          s += outputHeader(feedinfo, node, example_org)
        totrecs,spiece = outputOpportunity(opp, feedinfo, known_orgs, totrecs)
        s += spiece
        totrecs = totrecs + 1
        if (maxrecs > 0 and totrecs > maxrecs):
          break
    if progress:
      print datetime.now(),totrecs,"opportunities found."
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
    #        s += outputHeader(feedinfo, node, example_org)
    #      totrecs,spiece = outputOpportunity(node, feedinfo, known_orgs, totrecs)
    #      s += spiece
  else:
    # not do_fastparse
    footprint_xml = parse_footprint.Parse(instr, maxrecs, progress)
    
    feedinfos = footprint_xml.getElementsByTagName("FeedInfo")
    if (feedinfos.length != 1):
      print datetime.now(),"bad FeedInfo: should only be one section"
      # TODO: throw error
      exit
    feedinfo = feedinfos[0]
    organizations = footprint_xml.getElementsByTagName("Organization")
    for org in organizations:
      id = xml_helpers.getTagValue(org, "organizationID")
      if (id != ""):
        known_orgs[id] = org
    opportunities = footprint_xml.getElementsByTagName("VolunteerOpportunity")
    totrecs = 0
    for opp in opportunities:
      if totrecs == 0:
        s += outputHeader(feedinfo, opp, organizations[0])
      totrecs,spiece = outputOpportunity(opp, feedinfo, known_orgs, totrecs)
      s += spiece

  return s

def ftpActivity():
  print ".",

def ftpToBase(f, ftpinfo, s):
  ftplib = __import__('ftplib')
  StringIO = __import__('StringIO')
  fh = StringIO.StringIO(s)
  host = 'uploads.google.com'
  (user,passwd) = ftpinfo.split(":")
  print datetime.now(),"connecting to " + host + " as user " + user + "..."
  ftp = ftplib.FTP(host)
  print ftp.getwelcome()
  ftp.login(user, passwd)
  fn = "footprint1.txt"
  if re.search("usa-?service", f):
    fn = "usaservice1.gz"
  elif re.search("handson", f):
    fn = "handsonnetwork1.gz"
  elif re.search("idealist", f):
    fn = "idealist1.gz"
  elif re.search("volunteermatch", f):
    fn = "volunteermatch1.gz"

  if re.search(r'[.]gz$', fn):
    s = zlib.compress(s, 9)

  print datetime.now(),"uploading",len(s),"bytes under filename"+fn
  ftp.storbinary("STOR " + fn, fh, 8192)
  print datetime.now(),"done."
  ftp.quit()
  #print datetime.now(),"file:"
  #print s,

from optparse import OptionParser
if __name__ == "__main__":
  sys = __import__('sys')
  parser = OptionParser("usage: %prog [options] sample_data.xml ...")
  parser.set_defaults(geocode_debug=False)
  parser.set_defaults(debug=False)
  parser.set_defaults(progress=False)
  parser.set_defaults(debug_input=False)
  parser.set_defaults(output="basetsv")
  parser.set_defaults(test=False)
  parser.set_defaults(maxrecs=-1)
  parser.add_option("-d", "--dbg", action="store_true", dest="debug")
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
    exit(0)
  if options.fs != None:
    FIELDSEP = options.fs
  if options.rs != None:
    RECORDSEP = options.rs
  if (options.debug):
    debug = True
    geocode_debug = True
    progress = True
    FIELDSEP = "\n"
  if (options.geocode_debug):
    geocode_debug = True
  if options.test:
    options.progress = True
  if (options.progress):
    progress = True
  f = args[0]
  if options.inputfmt == "fpxml":
    parsefunc = parse_footprint.Parse
  elif (options.inputfmt == "usaservice" or
        options.inputfmt == "usasvc" or
        (options.inputfmt == None and
         re.search("usa-?service", f))):
    parsefunc = parse_usaservice.Parse
  elif (options.inputfmt == "handson" or
        options.inputfmt == "handsonnetwork" or
        (options.inputfmt == None and
         re.search("handson", f))):
    parsefunc = parse_handsonnetwork.Parse
  elif (options.inputfmt == "idealist" or
        (options.inputfmt == None and
         re.search("idealist", f))):
    parsefunc = parse_idealist.Parse
  elif (options.inputfmt == "volunteermatch" or
        options.inputfmt == "vm" or
        (options.inputfmt == None and
         re.search("volunteermatch", f))):
    parsefunc = parse_volunteermatch.Parse
  else:
    print datetime.now(),"unknown input format-- try --inputfmt"
    exit(1)

  if re.search(r'[.]gz$', f):
    fh = gzip.open(f, 'rb')
  elif f == "-":
    fh = sys.stdin
  else:
    fh = open(f, 'rb')
  if progress:
    print datetime.now(),"reading file..."
  instr = fh.read()

  # remove tabs and nonprintable junk
  if progress:
    print datetime.now(),"read file: ", len(instr)," bytes."
  instr = re.sub(r'\r\n?', "\n", instr)
  if progress:
    print datetime.now(),"filtered dos newlines:",len(instr)," bytes"
  instr = re.sub("\t", " ", instr)                                         
  if progress:
    print datetime.now(),"filtered tabs:",len(instr)," bytes"
  instr = re.sub("\xc2?[\x93\x94\222]", "'", instr)
  if progress:
    print datetime.now(),"filtered iso8859-1 single quotes:",len(instr)," bytes"
  #instr = re.sub(r'\xc2?[\223\224]', '"', instr)
  if progress:
    print datetime.now(),"filtered iso8859-1 double quotes:",len(instr)," bytes"
  instr = re.sub(r'\xc2?[\225\226\227]', "-", instr)
  if progress:
    print datetime.now(),"filtered iso8859-1 dashes:",len(instr)," bytes"
  instr = xml_helpers.cleanString(instr)
  if progress:
    print datetime.now(),"filtered nonprintables:",len(instr)," bytes"
  if (options.debug_input):
    # split nasty XML inputs, to help isolate problems
    instr = re.sub(r'><', r'>\n<', instr)

  if options.inputfmt == "fpxml":
    footprint_xmlstr = instr
  else:
    if progress:
      print datetime.now(),"parsing..."
    footprint_xmlstr = parsefunc(instr, int(options.maxrecs), progress)

  if options.test:
    print datetime.now(),"testing input: generating Footprint XML..."
    # free some RAM
    del instr
    fpxml = convertToFootprintXML(footprint_xmlstr, True, int(options.maxrecs), True)
    # free some RAM
    del footprint_xmlstr
    print datetime.now(),"testing input: parsing and regenerating Footprint XML..."
    fpxml2 = convertToFootprintXML(fpxml, True, int(options.maxrecs), True)
    print datetime.now(),"testing input: comparing outputs..."
    hash1 = hashlib.md5(fpxml).hexdigest()
    hash2 = hashlib.md5(fpxml2).hexdigest()
    fn1 = "/tmp/pydiff-"+hash1
    fn2 = "/tmp/pydiff-"+hash2
    if hash1 == hash2:
      print datetime.now(),"success:  getting head...\n"
      fh = open(fn1, "w+")
      fh.write(fpxml)
      fh.close()
      subprocess.call(['head', fn1])
    else:
      print datetime.now(),"errors-- hash1="+hash1+" hash2="+hash2+" running diff",fn1,fn2
      fh = open(fn1, "w+")
      fh.write(fpxml)
      fh.close()
      fh = open(fn2, "w+")
      fh.write(fpxml2)
      fh.close()
      subprocess.call(['diff', fn1, fn2])
      # grr-- difflib performance sucks
      #for line in difflib.unified_diff(fpxml, fpxml2, fromfile='(first output)', tofile='(second output)'):
      #print line
    exit(0)

  do_fastparse = not options.debug_input
  if options.outputfmt == "fpxml":
    # TODO: pretty printing option
    print convertToFootprintXML(footprint_xmlstr, do_fastparse, int(options.maxrecs), progress)
    exit(0)
  elif (options.outputfmt != "basetsv" and not options.ftpinfo):
    print datetime.now(),"--outputfmt not implemented: try 'basetsv' or 'fpxml'"
    exit(1)

  outstr = convertToGoogleBaseEventsType(footprint_xmlstr, do_fastparse, int(options.maxrecs), progress)
  #only need this if Base quoted fields it enabled
  #outstr = re.sub(r'"', r'&quot;', outstr)
  if (options.ftpinfo):
    ftpToBase(f, options.ftpinfo, outstr)
  else:
    print outstr,
