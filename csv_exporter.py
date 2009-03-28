#!/usr/bin/env python
#
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
#

import StringIO
import httplib
import logging
import getopt
import socket
import sys
import urllib
import urlparse

def get_csv(url):
  # get from url
  content = ""
  try:
    connection = urllib.urlopen(url);
    content = connection.read()
    connection.close()
  except:
    logging.error('Encountered exception accessing : %s', url)

  return content

def ExportCSV(filename, url, min_key):
  # get csv from url and write to filename
  content = ""
  try:
    csv_file = file(filename, 'a')
    try:
      content = get_csv(url)
      if content:
        csv_file.write(content)
    except:
      logging.error('could not process %s', url)
    finally:
      csv_file.close()
  except IOError:
    logging.error("I/O error({0}): {1}".format(errno, os.strerror(errno)))

  list = content.splitlines()
  line_count = len(list)
  last_line = list[line_count - 1]
  fields = last_line.split('","')

  if min_key == "":
    # that's our header, don't count it
    line_count -= 1

  min_key = fields[0][1:]

  return min_key, line_count

def PrintUsageExit(code):
  print sys.modules['__main__'].__doc__ % sys.argv[0]
  sys.stdout.flush()
  sys.stderr.flush()
  sys.exit(code)

def ParseArguments(argv):
  opts, args = getopt.getopt(
    argv[1:],
    'h',
    ['debug', 'help', 
     'url=', 'filename=', 'digsig=', 'batch_size='
    ])

  url = None
  filename = None
  digsig = ''
  batch_size = 1000

  for option, value in opts:
    if option == '--debug':
      logging.getLogger().setLevel(logging.DEBUG)
    if option in ('-h', '--help'):
      PrintUsageExit(0)
    if option == '--url':
      url = value
    if option == '--filename':
      filename = value
    if option == '--digsig':
      digsig = value
    if option == '--batch_size':
      batch_size = int(value)
      if batch_size <= 0:
        print >>sys.stderr, 'batch_size must be 1 or larger'
        PrintUsageExit(1)

  return (url, filename, batch_size, digsig)


def main(argv):
  logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s %(asctime)s %(filename)s] %(message)s')

  try:
    args = ParseArguments(argv)
    if [arg for arg in args if arg is None]:
      print >>sys.stderr, 'Invalid arguments'
      PrintUsageExit(1)

    url, filename, batch_size, digsig = args

    min_key = ""
    lines = batch_size
    while lines == batch_size:
      url_step = (url + '?digsig=' + str(digsig) + '&min_key=' 
            + str(min_key) + '&limit=' + str(batch_size))
      min_key, lines = ExportCSV(filename, url_step, min_key)
      logging.info('Exported %d records starting at %s', lines, min_key)

    return 0

  except:
    logging.error('could not process %s', url)
    return 1

if __name__ == '__main__':
  sys.exit(main(sys.argv))

