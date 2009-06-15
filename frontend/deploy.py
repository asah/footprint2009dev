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

In order to run this application, you will need the private_keys.py
file which contains the Facebook API "Application Secret" string and
other confidential config settings.
Contact footprint-eng@googlegroups.com to get this file.
"""

import os
import logging
import private_keys

PRODUCTION_DOMAIN = 'allforgood.org'

MAPS_API_KEYS = {
  'www.allforgood.org' : 'ABQIAAAAHtEBbyenR4BaYGl54_p0fRQu5fCZl1K7T-61hQb7PrEsg72lpRQbhbBcd0325oSLzGUQxP7Nz9Rquw',
  'unknown_what_is_this' : 'ABQIAAAAHtEBbyenR4BaYGl54_p0fRRlOb26qSyU154aZeLwOrF4C7-DphT-k84KU2QtDbk5G77Rqt1x2njBTQ',
  'footprint-loadtest.appspot.com' : 'ABQIAAAAxq97AW0x5_CNgn6-nLxSrxSWKH9akPVZO-6F_G0PvWoeHNZVdRSifDQCrd-osJFuWDqR3Oh0nKDgbw',
  'footprint2009dev.appspot.com' : 'ABQIAAAAxq97AW0x5_CNgn6-nLxSrxTpeCj-9ism2i6Mt7fLlVoN6HsfDBSOZjcyagWjKTMT32rzg71rFenopA'
}

# Google Analytics keys - only needed for dev, qa, and production
# we don't want to track in other instances
GA_KEYS = {
  'www.allforgood.org' : 'UA-8689219-2',
  'footprint2009dev.appspot.com' : 'UA-8689219-3'
}

FACEBOOK_API_KEYS = {}

# These are the public Facebook API keys.
DEFAULT_FACEBOOK_KEY = 'df68a40a4a90d4495ed03f920f16c333'
PRODUCTION_FACEBOOK_KEY = '628524bbaf79da8a8a478e5ef49fb84f'

FACEBOOK_KEY = None
FACEBOOK_SECRET_KEY = None
MAPS_API_KEY = None

def is_production_site():
  """is this a production instance?"""
  http_host = os.environ.get('HTTP_HOST')
  return (http_host[-len(PRODUCTION_DOMAIN):] == PRODUCTION_DOMAIN)

def is_local_development():
  """is this running on a development server (and not appspot.com)"""
  return (os.environ.get('SERVER_SOFTWARE').find("Development")==0)

def load_keys():
  """load facebook, maps, etc. keys."""
  global FACEBOOK_KEY, MAPS_API_KEY, FACEBOOK_SECRET_KEY, GA_KEY
  if FACEBOOK_KEY or MAPS_API_KEY or FACEBOOK_SECRET_KEY:
    return

  if is_local_development():
    # to define your own keys, modify local_keys.py-- ok to checkin.
    local_keys = __import__('local_keys')
    try:
      MAPS_API_KEYS.update(local_keys.MAPS_API_KEYS)
    except:
      logging.info("local_keys.MAPS_API_KEYS not defined")
    try:
      FACEOOK_API_KEYS.update(local_keys.FACEOOK_API_KEYS)
    except:
      logging.info("local_keys.FACEBOOK_API_KEYS not defined")

  # no default for maps api-- has to match
  http_host = os.environ.get('HTTP_HOST')
  MAPS_API_KEY = MAPS_API_KEYS.get(http_host, 'unknown')
  logging.debug("host="+http_host+"  maps api key="+MAPS_API_KEY)

  # no default for ga key
  GA_KEY = GA_KEYS.get(http_host, 'unknown')
  logging.debug("host="+http_host+"  ga key="+GA_KEY)

  # facebook API has default key
  if is_production_site():
    FACEBOOK_KEY = FACEBOOK_API_KEYS[PRODUCTION_DOMAIN]
  else:
    FACEBOOK_KEY = FACEBOOK_API_KEYS.get(http_host, DEFAULT_FACEBOOK_KEY) 
  logging.debug("host="+http_host+"  facebook key="+FACEBOOK_KEY)

  # facebook secret keys are a special case
  if is_production_site():
    FACEBOOK_SECRET_KEY = private_keys.PRODUCTION_FACEBOOK_SECRET
  else:
    FACEBOOK_SECRET_KEY = private_keys.DEFAULT_FACEBOOK_SECRET

def load_standard_template_values(template_values):
  """set template_values[...] for various keys"""
  load_keys()
  template_values['maps_api_key'] = MAPS_API_KEY
  template_values['facebook_key'] = FACEBOOK_KEY
  template_values['ga_key'] = GA_KEY

def get_facebook_secret():
  """returns the facebook secret key"""
  load_keys()
  return FACEBOOK_SECRET_KEY

def get_facebook_key():
  """returns the facebook public key"""
  load_keys()
  return FACEBOOK_KEY
