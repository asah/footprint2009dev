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

import utils 
import models 
import posting 

QT = "%s%s%s" % ("ec813d6d0c96f3a562c70d78b7ac98d7ec2cfcaaf44cbd7",
                 "ac897ca3481e27a777398da97d0b93bbe0f5633f6203ff3",
                 "b77ea55f62cf002ad7e4b5ec3f89d18954")

USAGE = """
<pre>/export/TABLENAME.tsv, eg. UserStats.tsv
</pre>
"""

class Fail(Exception):
  def __init__(self, message):
    logging.error("see /export/ for usage")
    logging.error(message)

def export_table_as_tsv(table, min_key, limit):
  """ 
  get rows from this table as TSV
  """

  delim, recsep = ("\t", "\n")

  def get_min_key(table, min_key = ""):
    # get the next key in our sequence
    # or get the lowest key value in the table
    if min_key == "":
      query = table.gql("ORDER BY __key__ LIMIT 1")
      row = query.get()
    else:
      row = table(key_name = min_key)

    if not row:
      if min_key == "":
        raise Fail("no data in %s" % table)
      else:
        return None

    return row.key()

  def get_fields(table_object):
    # get a list of field names prepended with "key"
    fields = ["key"]
    for i,field in enumerate(table_object.properties()):
      fields.append(field)
    return fields

  def field_to_str(value):
    # get our field value as a string
    if not value:
      field_value = ""
    else:
      try:
        # could be a Key object
        field_value = str(value.key().id_or_name())
      except:
        field_value = str(value)
    return field_value

  def get_header(fields, delim):
    # get a delimited list of the field names
    header = delim.join(fields)
    return header

  def esc_value(value, delim, recsep):
    # make sure our delimiter and record separator are not in the data
    return field_to_str(value).replace(delim, "\\t").replace(recsep, "\\n")

  fields = get_fields(table)

  output = []
  if min_key == "":
    # this is the first record we output so add the header
    output.append(get_header(fields, delim))
    cmp = ">="
  else:
    cmp = ">"

  query = table.gql(("WHERE __key__ %s :1 ORDER BY __key__" % cmp), 
          get_min_key(table, min_key))

  rsp = query.fetch(limit)
  for row in rsp:
    line = []
    for field in fields:
      if field == "key":
        value = row.key().id_or_name()
      else:
        value = getattr(row, field, "")
      line.append(esc_value(value, delim, recsep))
    output.append(delim.join(line))

  return "%s%s" % (recsep.join(output), recsep)

class exportTableTSV(webapp.RequestHandler):
  # export a table
  def get(self, table):

    digsig = utils.get_last_arg(self.request, "digsig", "")
    if hashlib.sha512(digsig).hexdigest() != QT:
      # require callers pass param &digsig=[string] such that
      # the hash of the string they pass to us equals QT
      raise Fail("no &digsig")

    try:
      limit = int(utils.get_last_arg(self.request, "limit", "1000"))
    except:
      raise Fail("non integer &limit")

    if limit < 1:
      # 1000 is the max records that can be fetched ever
      limit = 1000

    min_key = utils.get_last_arg(self.request, "min_key", "")

    if table == "UserInfo":
      self.response.out.write(export_table_as_tsv(
        models.UserInfo, min_key, limit))
    elif table == "UserStats":
      self.response.out.write(export_table_as_tsv(
        models.UserStats, min_key, limit))
    elif table == "UserInterest":
      self.response.out.write(export_table_as_tsv(
        models.UserInterest, min_key, limit))
    elif table == "VolunteerOpportunityStats":
      self.response.out.write(export_table_as_tsv(
        models.VolunteerOpportunityStats, min_key, limit))
    elif table == "VolunteerOpportunity":
      self.response.out.write(export_table_as_tsv(
        models.VolunteerOpportunity, min_key, limit))
    elif table == "Posting":
      # TODO add Posting to models.py
      self.response.out.write(export_table_as_tsv(
        posting.Posting, min_key, limit))
    else:
      raise Fail("not programmed to handle '%s'" % table)

class showUsage(webapp.RequestHandler):
  # show a list of the Models we can export
  def get(self):
    self.response.out.write(USAGE)

application = webapp.WSGIApplication(
    [ ("/export/(.*)\.tsv", exportTableTSV),
      ("/export/", showUsage)
    ], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
