#!/usr/bin/python2.5
# Copyright 2009 Google Inc.  All Rights Reserved.
#


import datetime
from google.appengine.ext import db


class Error(Exception):
  pass


class BadAccountType(Error):
  pass


class InterestTypeProperty(db.IntegerProperty):
  """Describes the level of interest a user has in an opportunity."""
  UNKNOWN = 0
  INTERESTED = 1
  WILL_ATTEND = 2
  HAVE_ATTENDED = 3


def IncrementProperties(model_class, key, props_to_set, **kwargs):
  """Generic method to increment statistics. Can also set properties.

  Example:

  Args:
    model_class: model class
    key: Entity key.
    props_to_set: Dictionary of properties to set to explicit values.
    kwargs: Properties to increment by specified amount.
  """

  def txn():
    stats = model_class.get_by_key_name(key)
    if not stats:
      stats = model_class(key_name=key)

    def increment(prop):
      if getattr(stats, prop):
        setattr(stats, prop, getattr(stats, prop) + kwargs[prop])
      else:
        setattr(stats, prop, kwargs[prop])

    # Set explicit values first.
    if props_to_set:
      for prop in props_to_set.iterkeys():
        setattr(stats, prop, props_to_set[prop])

    # Increment properties by requested amount.
    for prop in kwargs.iterkeys():
      increment(prop)

    stats.put()
    return stats

  return db.run_in_transaction(txn)


class UserInfo(db.Model):
  """Basic user statistics/preferences data."""
  # Key is accounttype:user_id.
  first_visit = db.DateTimeProperty(auto_now_add=True)
  last_edit = db.DateTimeProperty(auto_now=True)

  def account_type(self):
    key_name = self.key().name()
    return key_name.split(':', 1)[0]

  def user_id(self):
    key_name = self.key().name()
    return key_name.split(':', 1)[1]

  # Known types of accounts. Type must not start with a number.
  FRIENDCONNECT = 'friendconnect'
  FACEBOOK = 'facebook'
  TEST = 'test'
  KNOWN_TYPES = (FRIENDCONNECT, FACEBOOK, TEST)

  @classmethod
  def get_or_insert_user(cls, account_type, user_id):
    """Gets existing or creates a new user.

    Similar to get_or_insert, increments UserStats if appropriate.

    Args:
      account_type: Type of account used.
      user_id: address within that system.

    Returns:
      UserInfo for this user.

    Raises:
      BadAccountType if the account_type is unknown.
      Various datastore exceptions.
    """
    if not account_type in cls.KNOWN_TYPES:
      raise BadAccountType()

    key_name = '%s:%s' % (account_type, user_id)
    user_info = cls.get_by_key_name(key_name)

    def txn():
      entity = cls.get_by_key_name(key_name)
      created_entity = False
      if entity is None:
        entity = cls(key_name=key_name)
        entity.put()
        created_entity = True
      return (entity, created_entity)

    (user_info, created_entity) = db.run_in_transaction(txn)

    if created_entity:
      UserStats.Increment(account_type, user_id)

    return user_info


class UserStats(db.Model):
  """Stats about how many users we have."""
  count = db.IntegerProperty(default=0)

  @classmethod
  def Increment(cls, account_type, user_id):
    """Sharded counter. User ID is only for sharding."""

    def txn():
      # We want << 1000 shards.
      # This cheesy shard mechanism allows us some amount of way to see how
      # many users of each type we have too.
      shard_name = account_type + ':' + user_id[:2]
      counter = cls.get_by_key_name(shard_name)
      if not counter:
        counter = cls(key_name=shard_name)
      counter.count += 1
      counter.put()

    db.run_in_transaction(txn)

  @staticmethod
  def get_count():
    total = 0
    for counter in UserStats.all():
      total += counter.count
    return total


class UserInterest(db.Model):
  """Our record a user's actions related to an opportunity."""
  # Key is 'id:' + the stable ID from base; it is probabaly not the same ID
  # provided in the feed from providers.
  user = db.ReferenceProperty(UserInfo,
                              collection_name='interests')
  broadcast_on = db.DateTimeProperty()
  expressed_interest = InterestTypeProperty()


class VolunteerOpportunityStats(db.Model):
  """Basic statistics about opportunities."""
  # The __key__ is 'id:' + volunteer_opportunity_id
  last_edit = db.DateTimeProperty(auto_now=True)
  
  # Statistics about expressed interest:
  broadcast_count = db.IntegerProperty(default=0)
  interested_count = db.IntegerProperty(default=0)
  will_attend_count = db.IntegerProperty(default=0)
  have_attended_count = db.IntegerProperty(default=0)

  @classmethod
  def increment(cls, volunteer_opportunity_id, **kwargs):
    """Helper to increment volunteer opportunity stats.

    Example:
    models.VolunteerOpportunity.increment(opp_id, interested_count=1)
    
    Args:
      volunteer_opportunity_id: ID of opportunity.
      kwargs: Named properties to increment, and the delta to increment by.
    """
    props_to_set = {}
    return IncrementProperties(cls,
                               'id:' + volunteer_opportunity_id,
                               None,
                               **kwargs)

class VolunteerOpportunity(db.Model):
  """Basic information about opportunities.
  
  Separate from VolunteerOpportunity because these entries need not be
  operated on transactionally since there's no counts.
  """
  # The __key__ is 'id:' + volunteer_opportunity_id

  # Information about the opportunity  
  # URL to the Google Base entry
  base_url = db.StringProperty()
  # When we last update the Base URL.
  last_base_url_update = db.DateTimeProperty()
  # Incremented (possibly incorrectly to avoid transactions) when we try
  # to load the data from base but fail. Also the last date/time seen.
  base_url_failure_count = db.IntegerProperty(default=0)
  last_base_url_update_failure = db.DateTimeProperty()
