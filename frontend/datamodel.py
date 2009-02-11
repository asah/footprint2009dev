# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import geocode

class Location(object):
  plaintext = db.StringProperty()
  center_geopt = db.GeoPt()
  # TODO(paulr): Granularity, etc

  def set_plaintext(self, new_plaintext):
    self.plaintext = new_plaintext
    # geocode


class NotableItem(db.Model):
  # This is a canonical URL for this item.  Treated as primary key.
  url = db.StringProperty()
  location = Location()


class Event(NotableItem):
  date = db.DateProperty()  # TODO(paulr): date ranges, repeating dates, etc
  description = db.StringProperty()

