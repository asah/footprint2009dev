#!/usr/bin/python
# Copyright 2009 Google Inc.  All Rights Reserved.
#

from xml.dom.ext import PrettyPrint
from xml.sax.saxutils import escape
import gzip
import hashlib
import urllib
import re
from datetime import datetime
import parse_footprint
import parse_usaservice
import parse_handsonnetwork
import os
import time
import xml_helpers

import dateutil
import dateutil.tz
import dateutil.parser

FIELDSEP = "\t"
RECORDSEP = "\n"

debug = False
progress = False
printhead = False

fieldtypes = {
  "title":"builtin", "description":"builtin", "link":"builtin", "event_type":"builtin", "quantity":"builtin", "expiration_date":"builtin","image_link":"builtin","event_date_range":"builtin","id":"builtin","location":"builtin",
  "paid":"boolean","openended":"boolean",
  'volunteersSlots':'integer','volunteersFilled':'integer','volunteersNeeded':'integer','minimumAge':'integer',"commitmentHoursPerWeek":'integer',
  'providerURL':'URL','org_organizationURL':'URL','org_logoURL':'URL','org_providerURL':'URL','feed_providerURL':'URL',
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
  return res

csv_repeated_fields = ['categories','audiences',]
direct_map_fields = ['opportunityID','organizationID','abstract','volunteersSlots','volunteersFilled','volunteersNeeded','minimumAge','sexRestrictedTo','skills','contactName','contactPhone','contactEmail','providerURL','language','lastUpdated','expires',]
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
      print "no type for field: " + name
      print fieldtypes[name]
    elif (fieldtypes[name] == "builtin"):
      return name
    else:
      return "c:"+name+":"+fieldtypes[name]
  if debug:
    if (len(value) > 70):
      value = value[0:67] + "..."
    return name.rjust(22) + " : " + value
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
    print "geocode: "+loc+"="+latlong
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
    s += FIELDSEP
    s += outputTagValue(opp, field)
  for field in organization_fields:
    s += FIELDSEP
    s += outputField("org_"+field, xml_helpers.getTagValue(org, field))
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
  # TODO: publish_date?
  expires = xml_helpers.getTagValue(opp, "expires")
  if expires != "":
    # TODO: what tz is expires?
    expires = cvtDateTimeToGoogleBase(expires, "", "UTC")
  s += FIELDSEP + outputField("expiration_date", expires)
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
def geocode(addr):
  global geocode_debug, geocode_cache
  loc = addr.lower().strip()
  loc = re.sub(r'^[^0-9a-z]+', r'', loc)
  loc = re.sub(r'[^0-9a-z]+$', r'', loc)
  loc = re.sub(r'\s\s+', r'\s', loc)

  if geocode_cache == None:
    geocode_cache = {}
    fh = open("geocode_cache.txt", "r")
    try:
      for line in fh:
        if "|" in line:
          key,val = line.split("|")
          val = val.rstrip('\n')
          geocode_cache[key.lower()] = val
    finally:
      fh.close()
  if loc in geocode_cache:
    return geocode_cache[loc]

  # geocode with google maps, and cache responses
  params = urllib.urlencode({'q':loc.lower(), 'output':'csv',
                             'oe':'utf8', 'sensor':'false',
                             'key':'ABQIAAAAxq97AW0x5_CNgn6-nLxSrxQuOQhskTx7t90ovP5xOuY_YrlyqBQajVan2ia99rD9JgAcFrdQnTD4JQ'})
  if geocode_debug:
    print "geocoding '"+addr+"'..."
  f = urllib.urlopen("http://maps.google.com/maps/geo?%s" % params)
  res = f.readline()
  if geocode_debug:
    print "response: "+res
  if "," not in res:
    # fail and also don't cache
    return ""
  try:
    respcode,zoom,lat,long = res.split(",")
  except:
    if geocode_debug:
      print "unparseable response: "+res[0:80]
    respcode,zoom,lat,long = 999,0,0,0
  respcode = int(respcode)
  if respcode == 500 or respcode == 620:
    if geocode_debug:
      print "geocoder quota exceeded-- sleeping..."
    time.sleep(1)
    return geocode(addr)

  # these results get cached
  if respcode == 200:
    val = geocode_cache[loc] = lat+","+long
  elif respcode > 200:  # lookup failure
    val = ""

  fh = open("geocode_cache.txt", "a")
  fh.write(addr + "|" + val + "\n")
  fh.close()
  return val

def convertToGoogleBaseEventsType(footprint_xml, do_printhead, progress):
  s = ""
  recno = 0
  global debug
  if debug:
    print "footprint XML:"
    PrettyPrint(footprint_xml)

  feedinfos = footprint_xml.getElementsByTagName("FeedInfo")
  if (feedinfos.length != 1):
    print "bad FeedInfo: should only be one section"
    # TODO: throw error
    exit
  feedinfo = feedinfos[0]

  if do_printhead:
    global printhead
    printhead = True
    s += outputField("id", "")
    s += FIELDSEP + getFeedFields(feedinfo)
    s += FIELDSEP + getBaseEventRequiredFields(footprint_xml, footprint_xml)
    s += FIELDSEP + getBaseOtherFields(footprint_xml, footprint_xml)
    s += FIELDSEP + getDirectMappedField(footprint_xml, footprint_xml)
    s += FIELDSEP + outputField("location", "")
    s += FIELDSEP + outputField("location_string", "")
    s += FIELDSEP + outputField("venue_name", "")
    s += FIELDSEP + outputField("openended", "")
    s += FIELDSEP + outputField("duration", "")
    s += FIELDSEP + outputField("commitmentHoursPerWeek", "")
    s += FIELDSEP + outputField("event_date_range", "")
    s += RECORDSEP
    printhead = False

  organizations = footprint_xml.getElementsByTagName("Organization")
  known_orgs = {}
  for org in organizations:
    id = xml_helpers.getTagValue(org, "organizationID")
    if (id != ""):
      known_orgs[id] = org
    
  opportunities = footprint_xml.getElementsByTagName("VolunteerOpportunity")
  totrecs = 0
  for opp in opportunities:
    id = xml_helpers.getTagValue(opp, "volunteerOpportunityID")
    if (id == ""):
      print "no opportunityID"
      continue
    org_id = xml_helpers.getTagValue(opp, "sponsoringOrganizationID")
    if (org_id not in known_orgs):
      print "unknown org_id: " + org_id + ".  skipping opportunity " + id
      continue
    org = known_orgs[org_id]
    opp_locations = opp.getElementsByTagName("location")
    opp_times = opp.getElementsByTagName("dateTimeDuration")
    for opptime in opp_times:
      openended = xml_helpers.getTagValue(opptime, "openEnded")
      # event_date_range
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
      startDate = xml_helpers.getTagValue(opptime, "startDate")
      startTime = xml_helpers.getTagValue(opptime, "startTime")
      endDate = xml_helpers.getTagValue(opptime, "endDate")
      endTime = xml_helpers.getTagValue(opptime, "endTime")
      # e.g. 2006-12-20T23:00:00/2006-12-21T08:30:00, in PST (GMT-8)
      if (startDate == ""):
        startDate = "1971-01-01"
        startTime = "00:00:00-00:00"
      startend = cvtDateTimeToGoogleBase(startDate, startTime, "UTC")
      if (endDate != ""):
        startend += "/"
        startend += cvtDateTimeToGoogleBase(endDate, endTime, "UTC")
      for opploc in opp_locations:
        if progress:
          totrecs = totrecs + 1
          if totrecs%250==0:
            print datetime.now(),": ",totrecs," records generated."
        recno = recno + 1
        if debug:
          s += "--- record %s\n" % (recno)
        duration = xml_helpers.getTagValue(opptime, "duration")
        commitmentHoursPerWeek = xml_helpers.getTagValue(opptime, "commitmentHoursPerWeek")
        locstr,latlong,geocoded_loc = lookupLocationFields(opploc)
        #if locstr != geocoded_loc:
        #  #print "locstr: ", locstr, " geocoded_loc: ", geocoded_loc
        #  descs = opp.getElementsByTagName("description")
        #  encoded_locstr = escape(locstr)
        #  encoded_locstr = unicode(encoded_locstr,errors="ignore")
        #  encoded_locstr = encoded_locstr.encode('utf-8', "ignore")
        #  descs[0].firstChild.data += ". detailed location information: " + encoded_locstr
        id = computeStableId(opp, org, locstr, openended, duration,
                             commitmentHoursPerWeek, startend)
        s += outputField("id", id)
        s += FIELDSEP + getFeedFields(feedinfo)
        s += FIELDSEP + getBaseEventRequiredFields(opp, org)
        s += FIELDSEP + getBaseOtherFields(opp, org)
        s += FIELDSEP + getDirectMappedField(opp, org)
        s += FIELDSEP + outputField("location", latlong)
        s += FIELDSEP + outputField("location_string", geocoded_loc)
        s += FIELDSEP + outputField("venue_name", xml_helpers.getTagValue(opploc, "name"))
        s += FIELDSEP + outputField("openended", openended)
        s += FIELDSEP + outputField("duration", duration)
        s += FIELDSEP + outputField("commitmentHoursPerWeek", commitmentHoursPerWeek)
        s += FIELDSEP + outputField("event_date_range", startend)
        s += RECORDSEP
  return s

def ftpActivity():
  print ".",

def ftpToBase(f, ftpinfo, s):
  ftplib = __import__('ftplib')
  StringIO = __import__('StringIO')
  fh = StringIO.StringIO(s)
  host = 'uploads.google.com'
  (user,passwd) = ftpinfo.split(":")
  print "connecting to " + host + " as user " + user + "..."
  ftp = ftplib.FTP(host)
  print ftp.getwelcome()
  ftp.login(user, passwd)
  fn = "footprint1.txt"
  if re.search("usa-?service", f):
    fn = "usaservice1.txt"
  elif re.search("handson", f):
    fn = "handsonnetwork1.txt"
  print "uploading: "+fn
  ftp.storbinary("STOR " + fn, fh, 8192)
  print "done."
  ftp.quit()
  #print "file:"
  #print s,

from optparse import OptionParser
if __name__ == "__main__":
  sys = __import__('sys')
  parser = OptionParser("usage: %prog [options] sample_data.xml ...")
  parser.set_defaults(geocode_debug=False)
  parser.set_defaults(debug=False)
  parser.set_defaults(progress=False)
  parser.set_defaults(debug_input=False)
  parser.set_defaults(maxrecs=-1)
  parser.add_option("-d", "--dbg", action="store_true", dest="debug")
  parser.add_option("--dbginput", action="store_true", dest="debug_input")
  parser.add_option("--progress", action="store_true", dest="progress")
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
  if (options.progress):
    progress = True
  f = args[0]
  do_printhead = True
  parsefunc = parse_footprint.Parse
  if re.search("usa-?service", f):
    parsefunc = parse_usaservice.Parse
  elif re.search("handson", f):
    parsefunc = parse_handsonnetwork.Parse
  if re.search(r'[.]gz$', f):
    fh = gzip.open(f, 'rb')
  else:
    fh = open(f, 'rb')
  instr = fh.read()

  # remove tabs and nonprintable junk
  instr = xml_helpers.filterNonPrintable(instr)
  instr = re.sub("\t", " ", instr)                                         
  instr = re.sub(r'\r\n?', "\n", instr)
  instr = re.sub("\xc2?[\x93\x94]", "'", instr)
  instr = re.sub("\xc2?\222", "'", instr)
  instr = re.sub(r'\xc2?[\223\224]', '"', instr)
  instr = re.sub(r'\xc2?[\225\226]', "-", instr)

  if (options.debug_input):
    # split nasty XML inputs, to help isolate problems
    instr = re.sub(r'><', r'>\n<', instr)
    
  footprint_xml = parsefunc(instr, int(options.maxrecs), progress)

  if progress:
    print datetime.now(),"footprint_lib: convertToGoogleBaseEventsType..."
  outstr = convertToGoogleBaseEventsType(footprint_xml, do_printhead, progress)
  #only need this if Base quoted fields it enabled
  #outstr = re.sub(r'"', r'&quot;', outstr)
  if (options.ftpinfo):
    ftpToBase(f, options.ftpinfo, outstr)
  else:
    print outstr,
