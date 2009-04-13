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
toss all the scoring code into one place (rather than a class file)
because scoring tends to get complex quickly.
"""

from datetime import datetime
import logging
import math

import view_helper

def compare_scores(val1, val2):
  """helper function for sorting."""
  diff = val2.score - val1.score
  if (diff > 0):
    return 1
  if (diff < 0):
    return -1
  return 0

def score_results_set(result_set, args):
  """sort results by score, and for each, set .score, .scorestr, .score_notes"""
  logging.debug(str(datetime.now())+": score_results_set(): start")
  idlist = map(lambda x: x.item_id, result_set.results)
  # handle rescoring on interest weights
  others_interests = view_helper.get_interest_for_opportunities(idlist)
  total_results = float(len(result_set.results))
  for i, res in enumerate(result_set.results):
    score_by_base_rank = (total_results - i)/total_results
    score = score_by_base_rank
    score_notes = "  GBase relevance score=" + str(score_by_base_rank)

    # TODO: match on start time, etc.
    delta = res.startdate - datetime.now()
    if delta.days <= 0:
      # good luck joining event this soon
      # also avoids divide-by-zero and dates in the past
      date_dist_multiplier = .0001
    else:  
      date_dist_multiplier = 1.0/(delta.days + (delta.seconds/(24 * 3600)))

    if (("lat" not in args) or args["lat"] == "" or
        ("long" not in args) or args["long"] == "" or
         res.latlong == ""):
      geo_dist_multiplier = 0.5
    else:
      # TODO: error in the DB, we're getting same geocodes for everything
      lat, lng = res.latlong.split(",")
      latdist = float(lat) - float(args["lat"])
      lngdist = float(lng) - float(args["long"])
      # keep one value to right of decimal
      delta_dist = latdist*latdist + lngdist*lngdist
      #logging.info("qloc=%s,%s - listing=%g,%g - dist=%g,%g - delta = %g" %
      #             (args["lat"], args["long"], float(lat), float(lng),
      #              latdist, lngdist, delta_dist))
      # reasonably local
      if delta_dist > 0.025:
        delta_dist = 0.9 + delta_dist
      else:
        delta_dist = delta_dist / (0.025 / 0.9)
      if delta_dist > 0.999:
        delta_dist = 0.999
      geo_dist_multiplier = 1.0 - delta_dist

    interest = -1
    if res.item_id in others_interests:
      interest = others_interests[res.item_id]
    elif "test_stars" in args:
      interest = i % 6

    score *= geo_dist_multiplier
    score_notes += "  geo multiplier=" + str(geo_dist_multiplier)

    if interest >= 0:
      # TODO: remove hocus-pocus math
      interest_weight = (math.log(interest+1.0)/math.log(6.0))**3
      score *= interest_weight
      score_notes += "  "+str(interest)+"-stars="+str(interest_weight)

    score *= date_dist_multiplier
    score_notes += "  startdate multiplier=" + str(date_dist_multiplier)
    score_notes += "\n"
    score_notes += "  days delta=" + str(delta.days)
    score_notes += "  start=" + str(res.startdate)
    score_notes += "  now=" + str(datetime.now())
    score_notes += "  delta.seconds=" + str(delta.seconds)
    res.set_score(score, score_notes)

  result_set.results.sort(cmp=compare_scores)
  logging.debug(str(datetime.now())+": score_results_set(): done")

