# Copyright 2009 Google Inc.  All Rights Reserved.
#

# note: this is designed to consume the output from the craigslist crawler
# example record
#http://limaohio.craigslist.org/vol/1048151556.html-Q-<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd"> <html> <head> 	<title>Foster Parents Needed</title> 	<meta name="robots" content="NOARCHIVE"> 	<link rel="stylesheet" title="craigslist" href="http://www.craigslist.org/styles/craigslist.css" type="text/css" media="all"> </head>   <body onload="initFlag(1048151556)" class="posting">  <div class="bchead"> <a id="ef" href="/email.friend?postingID=1048151556">email this posting to a friend</a> <a href="http://limaohio.craigslist.org">lima / findlay craigslist</a>         &gt;  <a href="/vol/">volunteers</a> </div>  	<div id="flags"> 		<div id="flagMsg"> 			please <a href="http://www.craigslist.org/about/help/flags_and_community_moderation">flag</a> with care: 		</div> 		<div id="flagChooser"> 			<br> 			<a class="fl" id="flag16" href="/flag/?flagCode=16&amp;postingID=1048151556" 				title="Wrong category, wrong site, discusses another post, or otherwise misplaced"> 				miscategorized</a> 			<br>  			<a class="fl" id="flag28" href="/flag/?flagCode=28&amp;postingID=1048151556" 				title="Violates craigslist Terms Of Use or other posted guidelines"> 				prohibited</a> 			<br>  			<a class="fl" id="flag15" href="/flag/?flagCode=15&amp;postingID=1048151556" 				title="Posted too frequently, in multiple cities/categories, or is too commercial"> 				spam/overpost</a> 			<br>  			<a class="fl" id="flag9" href="/flag/?flagCode=9&amp;postingID=1048151556" 				title="Should be considered for inclusion in the Best-Of-Craigslist"> 				best of craigslist</a> 			<br> 		</div> 	</div>     <h2>Foster Parents Needed (Northwest Ohio)</h2> <hr> Reply to: <a href="mailto:&#99;&#111;&#109;&#109;&#45;&#49;&#48;&#52;&#56;&#49;&#53;&#49;&#53;&#53;&#54;&#64;&#99;&#114;&#97;&#105;&#103;&#115;&#108;&#105;&#115;&#116;&#46;&#111;&#114;&#103;?subject=Foster%20Parents%20Needed%20(Northwest%20Ohio)">&#99;&#111;&#109;&#109;&#45;&#49;&#48;&#52;&#56;&#49;&#53;&#49;&#53;&#53;&#54;&#64;&#99;&#114;&#97;&#105;&#103;&#115;&#108;&#105;&#115;&#116;&#46;&#111;&#114;&#103;</a> <sup>[<a href="http://www.craigslist.org/about/help/replying_to_posts" target="_blank">Errors when replying to ads?</a>]</sup><br> Date: 2009-02-24,  8:37AM EST<br> <br> <br> <div id="userbody"> Diversion Adolescent Foster Care of Ohio is accepting applications for foster parents in our Findlay office.  There are many children in Ohio in need of a temporary place to call home. Foster parent training is currently being offered.  Please call Stacy for more information 800-824-3007.  We look forward to meeting with you. www.diversionfostercare.org <br>  		<table> 			<tr> 				<td></td> 				<td></td> 			</tr> 			<tr> 				<td></td> 				<td></td> 			</tr> 		</table>    <br><br><ul> <li> Location: Northwest Ohio <li>it's NOT ok to contact this poster with services or other commercial interests</ul>  </div> PostingID: 1048151556<br>   <br> <hr> <br>  <div class="clfooter">         Copyright &copy; 2009 craigslist, inc.&nbsp;&nbsp;&nbsp;&nbsp;<a href="http://www.craigslist.org/about/terms.of.use.html">terms of use</a>&nbsp;&nbsp;&nbsp;&nbsp;<a href="http://www.craigslist.org/about/privacy_policy">privacy policy</a>&nbsp;&nbsp;&nbsp;&nbsp;<a href="/forums/?forumID=8">feedback forum</a> </div> <script type="text/javascript" src="http://www.craigslist.org/js/jquery.js"></script> <script type="text/javascript" src="http://www.craigslist.org/js/postings.js"></script> </body> </html>  
import sys
import re
import xml.sax.saxutils
import crawl_craigslist
from datetime import datetime

import dateutil.parser

craigslist_latlongs = None

def load_craigslist_latlongs():
  global craigslist_latlongs
  craigslist_latlongs = {}
  latlongs_fh = open('craigslist-metro-latlongs.txt')
  for line in latlongs_fh:
    line = re.sub(r'\s*#.*$', '', line).strip()
    if line == "":
      continue
    try:
      url,lat,long = line.strip().split("|")
    except:
      print "error parsing line",line
      sys.exit(1)
    craigslist_latlongs[url] = lat+","+long
  latlongs_fh.close()

def extract(instr, rx):
  res = re.findall(rx, instr, re.DOTALL)
  if len(res) > 0:
    return res[0].strip()
  return ""

def Parse(instr, maxrecs, progress):
  global craigslist_latlongs
  if craigslist_latlongs == None:
    load_craigslist_latlongs()
  if progress:
    print datetime.now(),"loading craigslist crawler output..."
  crawl_craigslist.parse_cache_file(instr, listings_only=True)
  if progress:
    print datetime.now(),"loaded",len(crawl_craigslist.pages),"pages."

  # convert to footprint format
  s = '<?xml version="1.0" ?>'
  s += '<FootprintFeed schemaVersion="0.1">'
  s += '<FeedInfo>'
  s += '<feedID>craigslist.org</feedID>'
  s += '<providerID>105</providerID>'
  s += '<providerName>craigslist.org</providerName>'
  s += '<providerURL>http://www.craigslist.org/</providerURL>'
  s += '<createdDateTime>2009-01-01T11:11:11</createdDateTime>'
  s += '</FeedInfo>'

  # no "organization" in craigslist postings
  s += '<Organizations>'
  s += '<Organization>'
  s += '<organizationID>0</organizationID>'
  s += '<nationalEIN></nationalEIN>'
  s += '<name></name>'
  s += '<missionStatement></missionStatement>'
  s += '<description></description>'
  s += '<location><city></city><region></region><postalCode></postalCode></location>'
  s += '<organizationURL></organizationURL>'
  s += '<donateURL></donateURL>'
  s += '<logoURL></logoURL>'
  s += '<detailURL></detailURL>'
  s += '</Organization>'
  s += '</Organizations>'

  skipped_listings = {}
  skipped_listings["body"] = skipped_listings["title"] = 0
  s += '<VolunteerOpportunities>'
  for i,url in enumerate(crawl_craigslist.pages):
    page = crawl_craigslist.pages[url]

    id = extract(url, "/vol/(.+?)[.]html$")
    title = extract(page, "<title>(.+?)</title>")
    body = extract(page, '<div id="userbody">(.+?)<')
    locstr = extract(page, "Location: (.+?)<")
    datestr = extract(page, "Date: (.+?)<")
    ts = dateutil.parser.parse(datestr)
    datetimestr = ts.strftime("%Y-%m-%dT%H:%M:%S")
    datestr = ts.strftime("%Y-%m-%d")

    # skip bogus listings
    if title == "":
      skipped_listings["title"] = skipped_listings["title"] + 1
      continue
    if len(body) < 25:
      skipped_listings["body"] = skipped_listings["body"] + 1
      continue

    if (maxrecs>0 and i>maxrecs):
      break
    if progress and i>0 and i%250==0:
      print datetime.now(),": ",i," listings processed; skipped",
      print skipped_listings["title"]+skipped_listings["body"],"listings (",
      print skipped_listings["title"],"for no-title and",
      print skipped_listings["body"],"for short body)"
      #print "---"
      #print "title:",title
      #print "loc:",locstr
      #print "date:",datestr
      #print "body:",body[0:100]

    s += '<VolunteerOpportunity>'
    s += '<volunteerOpportunityID>%s</volunteerOpportunityID>' % (id)
    s += '<sponsoringOrganizationIDs><sponsoringOrganizationID>0</sponsoringOrganizationID></sponsoringOrganizationIDs>'
    s += '<volunteerHubOrganizationIDs><volunteerHubOrganizationID>0</volunteerHubOrganizationID></volunteerHubOrganizationIDs>'
    s += '<title>%s</title>' % (title)
    s += '<detailURL>%s</detailURL>' % (url)
    # avoid CDATA in body...
    esc_body = xml.sax.saxutils.escape(body)
    esc_body100 = xml.sax.saxutils.escape(body[0:100])
    s += '<description>%s</description>' % (esc_body)
    s += '<abstract>%s</abstract>' % (esc_body100 + "...")
    s += '<lastUpdated>%s</lastUpdated>' % (datetimestr)
    # TODO: expires
    # TODO: synthesize location from metro...
    s += '<locations><location>'
    s += '<name>%s</name>' % (xml.sax.saxutils.escape(locstr))
    # what about the few that do geocode?
    lat,long = "",""
    try:
      domain,unused = url.split("vol/")
      lat,long = craigslist_latlongs[domain].split(",")
    except:
      # ignore for now
      #print url
      #continue
      pass
    s += '<latitude>%s</latitude>' % (lat)
    s += '<longitude>%s</longitude>' % (long)
    s += '</location></locations>'
    #s += '<locations><location>'
    #s += '<city>%s</city>' % (
    #s += '<region>%s</region>' % (
    #s += '</location></locations>'
    s += '<dateTimeDurations><dateTimeDuration>'
    s += '<openEnded>No</openEnded>'
    s += '<startDate>%s</startDate>' % (datestr)
    # TODO: endDate = startDate + N=14 days?
    # TODO: timezone???
    #s += '<endDate>%s</endDate>' % (
    s += '</dateTimeDuration></dateTimeDurations>'
    # TODO: categories???
    #s += '<categoryTags>'
    s += '</VolunteerOpportunity>'
  s += '</VolunteerOpportunities>'
  s += '</FootprintFeed>'

  if progress:
    print datetime.now(),"done generating footprint XML-- adding newlines..."
  s = re.sub(r'><([^/])', r'>\n<\1', s)
  #print s
  return s

if __name__ == "__main__":
  sys = __import__('sys')
  # tests go here
