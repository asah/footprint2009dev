#!/usr/bin/python2.5
# Copyright 2009 Google Inc.  All Rights Reserved.
#

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


def IncrementProperties(model_class, key, **kwargs):
  """Generic method to increment statistics.

  Example:

  Args:
    model_class: model class
    key: Entity key.
    kwargs: Properties to increment.
  """

  def txn():
    stats = model_class.get_by_key_name(key)
    if not stats:
      stats = VolunteerOpportunityStats(key_name=key)

    def increment(prop):
      if getattr(stats, prop):
        setattr(stats, prop, getattr(stats, prop) + kwargs[prop])
      else:
        setattr(stats, prop, kwargs[prop])

    for prop in kwargs.iterkeys():
      increment(prop)

    stats.put()

  db.run_in_transaction(txn)


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
  GOOGLE = 'google'  # Google Account; not Google Apps account.
  TEST = 'test'
  KNOWN_TYPES = (FRIENDCONNECT, GOOGLE, TEST)

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
  """Basic statistics about opportunities. Probably calculated on the fly."""

  # The __key__ is 'id:' + volunteer_opportunity_id
  broadcast_count = db.IntegerProperty(default=0)
  # interestCount should probably be split into multiple properties for each
  # possible interest type.
  interested_count = db.IntegerProperty(default=0)
  will_attend_count = db.IntegerProperty(default=0)
  have_attended_count = db.IntegerProperty(default=0)

  @classmethod
  def increment(cls, volunteer_opportunity_id, **kwargs):
    # Example:
    # models.VolunteerOpportunityStats.increment(opp_id, interested_count=1)
    return IncrementProperties(cls,
                               'id:' + volunteer_opportunity_id,
                               **kwargs)

