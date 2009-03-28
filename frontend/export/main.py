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

import cgi
import sys
import os

import logging
import hashlib

from google.appengine.ext import db
from google.appengine.ext.db import GqlQuery
from google.appengine.ext.db import Key
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import models 
import posting 
import utils 

QT = ("ec813d6d0c96f3a562c70d78b7ac98d7ec2cfcaaf44cbd7"
        + "ac897ca3481e27a777398da97d0b93bbe0f5633f6203ff3"
        + "b77ea55f62cf002ad7e4b5ec3f89d18954")

USAGE = ("<pre>/export/UserInfo.csv\n" 
       + "/export/UserStats.csv\n"
       + "/export/UserInterest.csv\n"
       + "/export/VolunteerOpportunity.csv\n"
       + "/export/VolunteerOpportunityStats.csv\n</pre>")

def getFields(table_object):
  fields = ["key"]
  for i,field in enumerate(table_object.properties()):
    fields.append(field)

  return fields

def getMinKey(table, min_key = ""):
  # get the next key in our sequence
  # or get the lowest key value in the table
  if min_key == "":
    query = table.gql("ORDER BY __key__ LIMIT 1")
    row = query.get()
  else:
    row = table(key_name = min_key)

  return row.key()

def getCSV(table, min_key, limit):
  # get up to limit csv rows from this table
  def csv_esc(value):
     try:
       use = str(value.key().id_or_name())
     except:
       use = str(value)

     return str(use).replace("'", "\\'").replace("\n", "\\n")

  if limit < 1:
    return

  fields = getFields(table)

  csv = ""
  if min_key == "":
    csv = '"' + '","'.join(fields) + '"\n'
    cmp = ">="
  else:
    cmp = ">"

  query = table.gql(("WHERE __key__ %s :1 ORDER BY __key__" % cmp), 
     getMinKey(table, min_key))

  rsp = query.fetch(limit)
  for row in rsp:
    line = []
    for field in fields:
      if field == "key":
        value = csv_esc(row.key().id_or_name())
      else:
        value = csv_esc(getattr(row, field, ""))
      line.append('"' + value + '"')
 
    csv += ",".join(line) + "\n"

  return csv

def checkQT(digsig):
  """
  require that callers pass a special param &digsig=[string]
  hash this string, and compare it to a known value
  """
  if QT == hashlib.sha512(digsig).hexdigest():
    return True
  else:
    return False

def get_limits_from_args(request):
  # get our arguments and check for digsig
  min_key = ""
  limit = 1000
  args = request.arguments()
  unique_args = {}
  try:
    # This allows callers to tack-on args for overriding, which can be
    # marginally easier than pre-pending.
    for arg in args:
      allvals = request.get_all(arg)
      if arg == "min_key":
        min_key = allvals[len(allvals)-1]
      elif arg == "limit":
        limit = allvals[len(allvals)-1]
      elif arg == "digsig":
        digsig = allvals[len(allvals)-1]

    if not checkQT(digsig):
       logging.info("missing &digsig. aborting.");
       raise Exception('digsig')

    if limit < 1:
      limit = 1

    return min_key, int(limit)

  except:
    return None, 0

class exportUserInfo(webapp.RequestHandler):
  # setup the parameters we need for exporting UserInfo
  def get(self):
    min_key, limit = get_limits_from_args(self.request)
    self.response.out.write(getCSV(models.UserInfo, min_key, limit))

class exportPosting(webapp.RequestHandler):
  # setup the parameters we need for exporting UserStats
  def get(self):
    min_key, limit = get_limits_from_args(self.request)
    # TODO add Posting to models.py
    self.response.out.write(getCSV(posting.Posting, min_key, limit))

class exportUserStats(webapp.RequestHandler):
  # setup the parameters we need for exporting UserStats
  def get(self):
    min_key, limit = get_limits_from_args(self.request)
    self.response.out.write(getCSV(models.UserStats, min_key, limit))

class exportUserInterest(webapp.RequestHandler):
  # setup the parameters we need for exporting UserInterest
  def get(self):
    min_key, limit = get_limits_from_args(self.request)
    self.response.out.write(getCSV(models.UserInterest, min_key, limit))

class exportVolunteerOpportunityStats(webapp.RequestHandler):
  # setup the parameters we need for exporting VolunteerOpportunityStats
  def get(self):
    min_key, limit = get_limits_from_args(self.request)
    self.response.out.write(getCSV(models.VolunteerOpportunityStats, min_key, 
     limit))

class exportVolunteerOpportunity(webapp.RequestHandler):
  # setup the parameters we need for exporting VolunteerOpportunity
  def get(self):
    min_key, limit = get_limits_from_args(self.request)
    self.response.out.write(getCSV(models.VolunteerOpportunity, min_key, limit))

class showUsage(webapp.RequestHandler):
  # show a list of the Models we can export
  def get(self):
    min_key, limit = get_limits_from_args(self.request)
    if limit > 0:
      self.response.out.write(USAGE)

""" 
TODO
make the table name dynamic, i.e.  ("/export", exportTable)
and then a single function class exportTable(webapp.RequestHandler)
"""
application = webapp.WSGIApplication(
    [ ("/export/UserInfo.csv", exportUserInfo),
      ("/export/UserStats.csv", exportUserStats),
      ("/export/UserInterest.csv", exportUserInterest),
      ("/export/Posting.csv", exportPosting),
      ("/export/VolunteerOpportunity.csv", exportVolunteerOpportunity),
      ("/export/VolunteerOpportunityStats.csv", 
                             exportVolunteerOpportunityStats),
      ("/export/", showUsage)
    ], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
