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

import datetime
import logging
import math
import time

import view_helper


def compare_scores(x,y):
  diff = y.score - x.score
  if (diff > 0): return 1
  if (diff < 0): return -1
  return 0

def score_results_set(result_set, args):
  # handle rescoring on interest weights
  idlist = map(lambda x: x.id, result_set.results)
  others_interests = view_helper.get_interest_for_opportunities(idlist)
  total_results = float(len(result_set.results))
  for i,res in enumerate(result_set.results):
    res.score_by_base_rank = (total_results - i)/total_results
    res.score = res.score_by_base_rank

    # TODO: match on start time, etc.
    delta = res.startdate - datetime.datetime.now()
    if delta.days <= 0:
      # good luck joining event this quickly; also covers divide-by-zero and past-dates
      res.date_dist_multiplier = .0001
    else:  
      res.date_dist_multiplier = 1.0/(delta.days + (delta.seconds/(24 * 3600)))

    if (("lat" not in args) or args["lat"] == "" or
        ("long" not in args) or args["long"] == "" or
         res.latlong == ""):
      res.geo_dist_multiplier = 0.5
    else:
      # TODO: error in the DB, we're getting same geocodes for everything
      lat, lng = res.latlong.split(",")
      latdist = float(lat) - float(args["lat"])
      lngdist = float(lng) - float(args["long"])
      # keep one value to right of decimal
      delta_dist = latdist*latdist + lngdist * lngdist
      #logging.info("qloc=%s,%s - listing=%g,%g - dist=%g,%g - delta = %g" %
      #             (args["lat"], args["long"], float(lat), float(lng), latdist, lngdist, delta_dist))
      # reasonably local
      if delta_dist > 0.025:
        delta_dist = 0.9 + delta_dist
      else:
        delta_dist = delta_dist / (0.025 / 0.9)
      if delta_dist > 0.999:
        delta_dist = 0.999
      res.geo_dist_multiplier = 1.0 - delta_dist

    interest = -1
    if res.id in others_interests:
      interest = others_interests[res.id]
    elif "test_stars" in args:
      interest = i % 6

    score_notes = ""
    res.score = res.score_by_base_rank
    score_notes += "  GBase relevance score=" + str(res.score_by_base_rank)

    res.score *= res.geo_dist_multiplier
    score_notes += "  geo multiplier=" + str(res.geo_dist_multiplier)

    if interest >= 0:
      # TODO: remove hocus-pocus math
      interest_weight = (math.log(interest+1.0)/math.log(6.0))**3
      res.score *= interest_weight
      score_notes += "  "+str(interest)+"-stars="+str(interest_weight)

    res.score *= res.date_dist_multiplier
    score_notes += "  startdate multiplier=" + str(res.date_dist_multiplier)
    score_notes += "\n"
    score_notes += "  days delta=" + str(delta.days)
    score_notes += "  start=" + str(res.startdate)
    score_notes += "  now=" + str(datetime.datetime.now())
    score_notes += "  delta.seconds=" + str(delta.seconds)

    res.scorestr = "%.4g" % (res.score)
    res.score_notes = score_notes

  result_set.results.sort(cmp=compare_scores)

