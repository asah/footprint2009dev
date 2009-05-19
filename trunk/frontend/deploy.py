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
Data needed for live vs dev deployment.
"""

import os

from google.appengine.ext import webapp

PRODUCTION_DOMAIN = 'allforgood.org'

def is_production_site():
  http_host = os.environ.get('HTTP_HOST')
  return (http_host[-len(PRODUCTION_DOMAIN):] == PRODUCTION_DOMAIN)

def load_standard_template_values(template_values):
  # TODO: Allow maps_api_key to be picked up from envvar, for testing and
  #     devt on personal servers.

  if is_production_site():
    template_values['maps_api_key'] = 'ABQIAAAAHtEBbyenR4BaYGl54_p0fRQu5fCZl1K7T-61hQb7PrEsg72lpRQbhbBcd0325oSLzGUQxP7Nz9Rquw'
  else:
    template_values['maps_api_key'] = 'ABQIAAAAHtEBbyenR4BaYGl54_p0fRRlOb26qSyU154aZeLwOrF4C7-DphT-k84KU2QtDbk5G77Rqt1x2njBTQ'