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

"""
export main().
"""

import re
import logging
import hashlib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import utils 
import models 
import posting 
from fastpageviews import pagecount

QT = "%s%s%s" % ("ec813d6d0c96f3a562c70d78b7ac98d7ec2cfcaaf44cbd7",
                 "ac897ca3481e27a777398da97d0b93bbe0f5633f6203ff3",
                 "b77ea55f62cf002ad7e4b5ec3f89d18954")

USAGE = """
<pre>
/export/TABLENAME.tsv, eg. UserStats.tsv
/export/TABLENAME/TABLENAME_BACKUP, eg. UserInfo/UserInfo_20090416
</pre>
"""

class Fail(Exception):
  """
  handle errors
  """
  def __init__(self, message):
    pagecount.IncrPageCount("export.Fail", 1)
    if hasattr(Exception, '__init__'):
      Exception.__init__(self)
    logging.error("see /export/ for usage")
    logging.error(message)

class ShowUsage(webapp.RequestHandler):
  """ show user how to export a table """
  def __init__(self):
    if hasattr(webapp.RequestHandler, '__init__'):
      webapp.RequestHandler.__init__(self)

  def response(self):
    """ pylint wants a public reponse method """
    webapp.RequestHandler.__response__(self)

  def get(self):
    """ show the usage string """
    pagecount.IncrPageCount("export.ShowUsage", 1)
    self.response.out.write(USAGE)

def verify_dig_sig(request, caller):
  """ 
  require callers pass param &digsig=[string] such that
  the hash of the string they pass to us equals QT
  """
  digsig = utils.get_last_arg(request, "digsig", "")
  if hashlib.sha512(digsig).hexdigest() != QT:
    pagecount.IncrPageCount("export.%s.noDigSig" % caller, 1)
    raise Fail("no &digsig")

def get_limit(request, caller):
  """ get our limit """
  try:
    limit = int(utils.get_last_arg(request, "limit", "1000"))
  except:
    pagecount.IncrPageCount("export.%s.nonIntLimit" % caller, 1)
    raise Fail("non integer &limit")

  if limit < 1:
    # 1000 is the max records that can be fetched ever
    limit = 1000

  return limit

def get_model(table, caller):
  """ get our model """
  if table == "UserInfo":
    model = models.UserInfo
  elif table == "UserStats":
    model = models.UserStats
  elif table == "UserInterest":
    model = models.UserInterest
  elif table == "VolunteerOpportunityStats":
    model = models.VolunteerOpportunityStats
  elif table == "VolunteerOpportunity":
    model = models.VolunteerOpportunity
  elif table == "Posting":
    # TODO add Posting to models.py
    model = posting.Posting
  elif table == "PageCountShard":
    # TODO add PageCountShard to models.py
    model = pagecount.PageCountShard
  else:
    pagecount.IncrPageCount("export.%s.unknownTable" % caller, 1)
    raise Fail("unknown table name '%s'" % table)

  return model

def get_min_key(table, min_key = ""):
  """
  get the next key in our sequence
  or get the lowest key value in the table
  """
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

def export_table_as_tsv(table, min_key, limit):
  """ 
  get rows from this table as TSV
  """

  delim, recsep = ("\t", "\n")

  def get_fields(table_object):
    """ get a list of field names prepended with 'key' """
    fields = ["key"]
    for field in table_object.properties():
      fields.append(field)
    return fields

  def field_to_str(value):
    """ get our field value as a string """
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
    """ get a delimited list of the field names """
    header = delim.join(fields)
    return header

  def esc_value(value, delim, recsep):
    """ make sure our delimiter and record separator are not in the data """
    return field_to_str(value).replace(delim, "\\t").replace(recsep, "\\n")

  fields = get_fields(table)

  output = []
  if min_key == "":
    # this is the first record we output so add the header
    output.append(get_header(fields, delim))
    inequality = ">="
  else:
    inequality = ">"

  query = table.gql(("WHERE __key__ %s :1 ORDER BY __key__" % inequality), 
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

class ExportTableTSV(webapp.RequestHandler):
  """ export the data in the table """
  def __init__(self):
    if hasattr(webapp.RequestHandler, '__init__'):
      webapp.RequestHandler.__init__(self)

  def request(self):
    """ pylint wants a public request method """
    webapp.RequestHandler.__response__(self)

  def response(self):
    """ pylint wants a public response method """
    webapp.RequestHandler.__response__(self)

  def get(self, table):
    """ handle the request to export the table """
    pagecount.IncrPageCount("export.ExportTableTSV.attempt", 1)
    verify_dig_sig(self.request, "ExportTableTSV")
    limit = get_limit(self.request, "ExportTableTSV")
    min_key = utils.get_last_arg(self.request, "min_key", "")
    model = get_model(table, "ExportTableTSV")
    self.response.out.write(export_table_as_tsv(model, min_key, limit))
    pagecount.IncrPageCount("export.ExportTableTSV.success", 1)

def transfer_table(source, destination, min_key, limit):
  """ transfer records from source to destination """
  last_key = ""
  number_of_rows = 0

  def populate_row(src_table, dest_table, row, key = None):
    """ put a row from the src_table into the dest_table """
    if key:
      row_i = dest_table(key_name = str(key))
    else:
      row_i = dest_table()

    for field in src_table.properties():
      setattr(row_i, field, getattr(row, field))

    row_i.put()

  if min_key == "":
    # this is the first record 
    inequality = ">="
  else:
    inequality = ">"

  query = source.gql(("WHERE __key__ %s :1 ORDER BY __key__" % inequality),
          get_min_key(source, min_key))

  rsp = query.fetch(limit)
  for row in rsp:
    last_key = row.key().id_or_name()
    try:
      # try to preserve our key name
      populate_row(source, destination, row, last_key)
      number_of_rows += 1
    except:
      populate_row(source, destination, row)
      number_of_rows += 1

  return last_key, number_of_rows

class TransferTable(webapp.RequestHandler):
  """ export the data in the table """
  def __init__(self):
    if hasattr(webapp.RequestHandler, '__init__'):
      webapp.RequestHandler.__init__(self)

  def request(self):
    """ pylint wants a public request method """
    webapp.RequestHandler.__response__(self)

  def response(self):
    """ pylint wants a public response method """
    webapp.RequestHandler.__response__(self)

  def get(self, table_from, table_to):
    """ handle the request to replicate a table """
    pagecount.IncrPageCount("export.TransferTable.attempt", 1)
    verify_dig_sig(self.request, "TransferTable")
    limit = get_limit(self.request, "TransferTable")
    min_key = utils.get_last_arg(self.request, "min_key", "")

    if table_from == table_to:
      pagecount.IncrPageCount("export.TransferTable.sameTableName", 1)
      raise Fail("cannot transfer '%s' to itself" % table_from)

    if (table_to[0:len(table_from)] + '_') != (table_from + '_'):
      raise Fail("destination must start with '%s_'" % table_from)

    good_chars = re.compile(r'[A-Za-z0-9_]')
    good_name = ''.join(c for c in table_to if good_chars.match(c))
    if table_to != good_name:
      pagecount.IncrPageCount("export.TransferTable.badDestName", 1)
      raise Fail("destination contains nonalphanumerics '%s'" % table_to)

    source = get_model(table_from, "TransferTable")
    destination = type(table_to, (source,), {})

    if min_key == "":
      while True:
        query = destination.all()
        results = query.fetch(1000)
        if results:
          db.delete(results)
        else:
          break

    last_key, rows = transfer_table(source, destination, min_key, limit) 
    self.response.out.write("from %s to %s\nrows\t%d\nlast_key\t%s\n"
      % (table_from, table_to, rows, last_key))
    pagecount.IncrPageCount("export.TransferTable.success", 1)

class PopulateTable(webapp.RequestHandler):
  """ populate the data in the table """
  def __init__(self):
    if hasattr(webapp.RequestHandler, '__init__'):
      webapp.RequestHandler.__init__(self)

  def request(self):
    """ pylint wants a public request method """
    webapp.RequestHandler.__response__(self)

  def response(self):
    """ pylint wants a public response method """
    webapp.RequestHandler.__response__(self)

  def post(self, table):
    """ handle the request to populate the table """
    pagecount.IncrPageCount("export.PopulateTable.attempt", 1)
    verify_dig_sig(self.request, "PopulateTable")
    destination = get_model(table, "PopulateTable")

    try:
      reset = int(utils.get_last_arg(self.request, "reset", "0"))
    except:
      pagecount.IncrPageCount("export.%s.nonIntLimit" % "PopulateTable", 1)
      raise Fail("invalid &reset signal")

    if reset == 1:
      pagecount.IncrPageCount("export.%s.reset" % "PopulateTable", 1)
      while True:
        query = destination.all()
        results = query.fetch(1000)
        if results:
          self.response.out.write("deleting %d from %s\n" 
              % (len(results), table))
          db.delete(results)
        else:
          self.response.out.write("%s reset\n" % table)
          break

    rows = self.request.get("row").split("\n")
    # the first row is a header
    header = rows.pop(0).split("\t")
    
    field_typing = 0
    written = 0
    for row in rows:
      if len(row) > 4:
        fields = row[4:].split("\t")
        for i, field in enumerate(fields):
          if i == 0:
            try:
              row_i = destination(key_name = str(field))
            except:
              row_i = destination()
          else:
            try:
              setattr(row_i, header[i], field)
            except:
              try:
                setattr(row_i, header[i], int(field))
              except:
                field_typing += 1
                try:
                  setattr(row_i, header[i], float(field))
                except:
                  field_typing += 1
             
        if field_typing:
          # TODO implement field typing
          field_typing = 0
        row_i.put()
        written += 1

    self.response.out.write("wrote %d rows to %s\n" % (written, table))
    pagecount.IncrPageCount("export.PopulateTable.success", 1)

APPLICATION = webapp.WSGIApplication(
    [ ("/export/(.*?)\.tsv", ExportTableTSV),
      ("/export/-/(.*?)", PopulateTable),
      ("/export/(.*?)/(.*?)", TransferTable),
      ("/export/", ShowUsage)
    ], debug=True)

def main():
  """ execution begins """
  run_wsgi_app(APPLICATION)

if __name__ == "__main__":
  main()
