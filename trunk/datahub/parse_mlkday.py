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
parser for MLK Day (same format as SERVEnet)
"""

import xml_helpers as xmlh
import re
import parse_servenet

# pylint: disable-msg=R0915
def parse(instr, maxrecs, progress):
  """return FPXML given servenet data"""
  outstr, numorgs, numopps = parse_servenet.parse(instr, maxrecs, progress)

  feedinfo = '<FeedInfo>'
  feedinfo += xmlh.output_val('providerID', '115')
  feedinfo += xmlh.output_val('providerName', 'mlk_day')
  feedinfo += xmlh.output_val('feedID', 'mlk_day')
  feedinfo += xmlh.output_val('createdDateTime', xmlh.current_ts())
  feedinfo += xmlh.output_val('providerURL', 'http://my.mlkday.gov/')
  feedinfo += xmlh.output_val('description', 'Martin Luther King day')
  # TODO: capture ts -- use now?!
  feedinfo += '</FeedInfo>'
  outstr = re.sub(r'<FeedInfo>.+?</Feedinfo>', feedinfo, outstr)

  #outstr = re.sub(r'><([^/])', r'>\n<\1', outstr)
  return outstr, numorgs, numopps


