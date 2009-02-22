# Copyright 2009 Google Inc.  All Rights Reserved.
#

from google.appengine.ext import db

class InterestTypeProperty(db.IntegerProperty):
  """Describes the level of interest a user has in an opportunity."""
  UNKNOWN = 0
  INTERESTED = 1
  WILL_ATTEND = 2
  HAVE_ATTENDED = 3
  

class User(db.Model):
  """Basic user statistics/preferences data."""
  # user_id is the friendconnect user id.
  # NOTE: I plan to change this to a list property, then we can have multiple
  # userids. We can/should define some type of sceme like fc:blah fb:blah etc.
  user_id = db.StringProperty(required=True)
  first_visit = db.DateTimeProperty(auto_now_add=True)
  recent_visit = db.DateTimeProperty(auto_now=True)


class UserVolunteerOpportunity(db.Model):
  """Our record a user's actions related to an opportunity."""
  user = db.ReferenceProperty(User)
  # volunteerOpportunityID is the stable ID from base; it is probabaly
  # not the same ID provided in the feed from providers.
  volunteerOpportunityID = db.StringProperty(required=True)
  broadcastOn = db.DateTimeProperty()
  expressedInterest = InterestTypeProperty()


class VolunteerOpportunityStats(db.Model):
  """Basic statistics about opportunities. Probably calculated on the fly."""
  volunteerOpportunityID = db.StringProperty(required=True)
  broadcastCount = db.IntegerProperty()
  # interestCount should probably be split into multiple properties for each
  # possible interest type.
  interestedCount = db.IntegerProperty()
  will_attend_count = db.IntegerProperty()
  have_attended_count = db.IntegerProperty()

