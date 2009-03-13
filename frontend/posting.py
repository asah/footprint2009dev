#!/usr/bin/python
# Copyright 2009 Google Inc.  All Rights Reserved.
#


from datetime import datetime
import logging
import hashlib
import utils
from xml.dom import minidom
from google.appengine.ext import db

class Error(Exception):
  pass

class Posting(db.Model):
  """Postings going through the approval process."""
  # Key is assigned ID (not the stable ID)
  id = db.StringProperty(default="")
  status = db.StringProperty(default="NEW")

  # for queries, parse-out these fields - note that we don't care about datatypes
  quality_score = db.FloatProperty(default=1.0)
  creation_time = db.DateTimeProperty(auto_now=True)
  start_date = db.DateProperty(auto_now=True)

  # listing_xml is the full contents for the listing, assuming it gets approved
  # note: listing_xml also used for fulltext queries
  listing_xml = db.TextProperty(default="")

  # parse-out these fields to improve latency in the moderation UI
  title = db.StringProperty(default="")
  description = db.TextProperty(default="")
  # as per http://code.google.com/p/googleappengine/issues/detail?id=105
  # there's no point in GeoPT esp. given that we're only using this for display
  # there's even bugs (http://aralbalkan.com/1355) in GeoPT, so the heck with it.
  #todo latlong = db.StringProperty(default="")

  def showInModerator():
      return (status.find("NEW") or status.find("EDITED"))
  def showLive():
      return (status.find("ACCEPTED"))
  def reject(type="MANUAL"):
      status = type+"_REJECTED"
      self.put()
  def accept(type="MANUAL"):
      status = type+"_ACCEPTED"
      self.put()
  def delete(type="MANUAL"):
      status = type+"_DELETED"
      self.put()
  def markEdited():
      if status == "NEW" or status == "VERIFIED":
        status += "_EDITED"
      else:
        # throw back on the queue-- undelete, etc.
        status = "NEW_EDITED"
  def computeQualityScore(self):
      # TODO: walk the object to look for missing/bad fields
      quality_score = 1.0
      self.put()

def query(num=25, start=1, quality_score=0.0, start_date="2009-01-01"):
  # TODO: GQL doesn't support string-CONTAINS, limiting keyword search
  # TODO: GQL doesn't let you do inequality comparison on multiple fields.
  if quality_score == 0.0:
    sd = datetime.strptime(start_date, "%Y-%m-%d")
    q = db.GqlQuery("SELECT * FROM Posting " + 
                    "WHERE start_date >= :1 " +
                    "ORDER BY start_date ASC " +
                    "LIMIT %d OFFSET %d" % (int(num), int(start)),
                    sd.date())
  else:
    q = db.GqlQuery("SELECT * FROM Posting " + 
                    "WHERE quality_score >= :1 " +
                    "ORDER BY start_date ASC " +
                    "LIMIT %d OFFSET %d" % (int(num), int(start)),
                    float(quality_score))
  result_set = q.fetch(num)
  reslist = []
  for result in result_set:
    reslist.append(result)
  return reslist

def create(listing_xml):
  posting = Posting(listing_xml=listing_xml)
  dom = minidom.parseString(listing_xml)
  posting.title = utils.GetXmlElementTextOrEmpty(dom, "title")
  posting.description = utils.GetXmlElementTextOrEmpty(dom, "description")
  try:
    start_date = datetime.strptime(utils.GetXmlElementTextOrEmpty(dom, "startDate"), "%Y-%m-%d")
    posting.start_date = start_date.date()
  except:
    pass
    # ignore bad start date
  posting.id = hashlib.md5(listing_xml+str(posting.creation_time)).hexdigest()
  posting.put()
  return posting.key()

def createTestDatabase():
  id1 = create("<VolunteerOpportunity><volunteerOpportunityID>1001</volunteerOpportunityID><sponsoringOrganizationIDs><sponsoringOrganizationID>1</sponsoringOrganizationID></sponsoringOrganizationIDs><volunteerHubOrganizationIDs><volunteerHubOrganizationID>3011</volunteerHubOrganizationID></volunteerHubOrganizationIDs><title>Be a Business Mentor - Trenton, NJ &amp; Beyond</title><dateTimeDurations><dateTimeDuration><openEnded>Yes</openEnded><duration>P6M</duration><commitmentHoursPerWeek>4</commitmentHoursPerWeek></dateTimeDuration></dateTimeDurations><locations><location><city>Trenton</city><region>NJ</region><postalCode>08608</postalCode></location><location><city>Berkeley</city><region>CA</region><postalCode>94703</postalCode></location><location><city>Santa Cruz</city><region>CA</region><postalCode>95062</postalCode></location></locations><categoryTags><categoryTag>Community</categoryTag><categoryTag>Computers &amp; Technology</categoryTag><categoryTag>Employment</categoryTag></categoryTags><minimumAge>21</minimumAge><skills>In order to maintain the integrity of the MicroMentor program, we require that our Mentor volunteers have significant business experience and expertise, such as: 3 years of business ownership experience</skills><detailURL>http://www.volunteermatch.org/search/index.jsp?l=08540</detailURL><description>This is where you come in. Simply by sharing your business know-how, you can make a huge difference in the lives of entrepreneurs from low-income and marginalized communities, helping them navigate the opportunities and challenges of running a business and improving their economic well-being and creating new jobs where they are most needed.</description></VolunteerOpportunity>")
  id2 = create("<VolunteerOpportunity><volunteerOpportunityID>2001</volunteerOpportunityID><sponsoringOrganizationIDs><sponsoringOrganizationID>2</sponsoringOrganizationID></sponsoringOrganizationIDs><title>DODGEBALL TO HELP AREA HUNGRY</title><dateTimeDurations><dateTimeDuration><openEnded>No</openEnded><startDate>2009-02-22</startDate><endDate>2009-02-22</endDate><startTime>18:45:00</startTime><endTime>21:00:00</endTime></dateTimeDuration><dateTimeDuration><openEnded>No</openEnded><startDate>2009-02-27</startDate><endDate>2009-02-27</endDate><startTime>18:45:00</startTime><endTime>21:00:00</endTime></dateTimeDuration></dateTimeDurations><locations><location><city>West Windsor</city><region>NJ</region><postalCode>08550</postalCode></location></locations><audienceTags><audienceTag>Teens</audienceTag><audienceTag>High School Students</audienceTag></audienceTags><categoryTags><categoryTag>Community</categoryTag><categoryTag>Homeless &amp; Hungry</categoryTag><categoryTag>Hunger</categoryTag></categoryTags><minimumAge>14</minimumAge><skills>Must be in High School</skills><detailURL>http://www.volunteermatch.org/search/opp451561.jsp</detailURL><description>The Mercer County Quixote Quest Teen Volunteer Club is hosting a FUN Dodgeball Tournament at Mercer County College on Sunday afternoon, February 22nd. The proceeds from the event will bebefit the Trenton Area Soup Kitchen. Teens are invited to enter a team of six...with at least three female players (3 guys and 3 girls or more girls). Each team playing will bring a $50 entry fee and a matching sponsor donation of $50. (Total of $100 from each team).</description><lastUpdated olsonTZ=\"America/Denver\">2009-02-02T19:02:01</lastUpdated></VolunteerOpportunity>")
  id3 = create("<VolunteerOpportunity><volunteerOpportunityID>2002</volunteerOpportunityID><sponsoringOrganizationIDs><sponsoringOrganizationID>2</sponsoringOrganizationID></sponsoringOrganizationIDs><title>YOUNG ADULT TO HELP GUIDE MERCER COUNTY TEEN VOLUNTEER CLUB</title><volunteersNeeded>3</volunteersNeeded><dateTimeDurations><dateTimeDuration><openEnded>No</openEnded><startDate>2009-01-01</startDate><endDate>2009-05-31</endDate><iCalRecurrence>FREQ=WEEKLY;INTERVAL=2</iCalRecurrence><commitmentHoursPerWeek>2</commitmentHoursPerWeek></dateTimeDuration></dateTimeDurations><locations><location><city>Mercer County</city><region>NJ</region><postalCode>08610</postalCode></location></locations><audienceTags><audienceTag>Teens</audienceTag></audienceTags><categoryTags><categoryTag>Community</categoryTag><categoryTag>Children &amp; Youth</categoryTag></categoryTags><skills>Be interested in promoting youth volunteerism. Be available two Tuesday evenings per month.</skills><detailURL>http://www.volunteermatch.org/search/opp200517.jsp</detailURL><description>Quixote Quest is a volunteer club for teens who have a passion for community service. The teens each volunteer for their own specific cause. Twice monthly, the club meets. At the club meetings the teens from different high schools come together for two hours to talk about their volunteer experiences and spend some hang-out time together that helps them bond as fraternity...family. Quixote Quest is seeking young adults roughly between 20 and 30 years of age who would be interested in being a guide and advisor to the teens during these two evening meetings a month.</description><lastUpdated olsonTZ=\"America/Denver\">2008-12-02T19:02:01</lastUpdated></VolunteerOpportunity>")
  return (id1,id2,id3)


    

