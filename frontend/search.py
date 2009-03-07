# Copyright 2009 Google Inc.  All Rights Reserved.
#

import base_search
import logging
import geocode

# args is expected to be a list of args
# and any path info is supposed to be homogenized into this,
# e.g. /listing/56_foo should be resolved into [('id',56)]
# by convention, repeated args are ignored, LAST ONE wins.
def search(args):
  num = 10
  if "num" in args:
    num = int(args["num"])
    if num < 1: num = 1
    if num > 999: num = 999
  args["num"] = num

  start_index = 1
  if "start" in args:
    start_index = int(args["start"])
    if start_index < 1: start_index = 1
    if start_index > 1000-num: start_index = 1000-num
  args["start"] = start_index

  if "q" not in args:
    args["q"] = ""

  if "output" in args:
    if args["output"] in ['html','tsv','csv','json','rss','rssdesc','xml',
                          'snippets_list']:
      output = args["output"]
    else:
      searchParamError(args, "output")
  else:
    args["output"] = "html"

  if "fields" in args:
    # TODO: csv list of fields
    if args["fields"] in ['all','rss']:
      fields = args["fields"]
    else:
      searchParamError(args, "fields")
  else:
    args["fields"] = "all"

  # TODO: process dbg -- currently, anything goes...

  # RESERVED: v
  # RESERVED: sort
  # RESERVED: type

  if "vol_loc" in args:
    res = geocode.geocode(args["vol_loc"])
    if res != "":
      args["lat"],args["long"] = res.split(",")
    if "vol_dist" not in args:
      args["vol_dist"] = 25
  else:
    args["vol_loc"] = args["vol_dist"] = ""
    args["vol_lat"] = args["vol_long"] = ""

  vol_start = ""
  if "vol_start" in args:
    vol_start = args["vol_start"]
  vol_end = ""
  if "vol_end" in args:
    vol_end = args["vol_end"]
  vol_tz = ""
  if "vol_tz" in args:
    vol_tz = args["vol_tz"]
  vol_duration = ""
  if "vol_duration" in args:
    vol_duration = args["vol_duration"]

  id = ""
  if "id" in args:
    id = args["id"]

  res = base_search.search(args)

  res.is_first_page = (start_index == 1)
  # TODO: detect last page
  res.is_last_page = True
  # TODO: remove-- urls should be implemented by the caller
  res.prev_page_url = ""
  res.next_page_url = ""

  return res
