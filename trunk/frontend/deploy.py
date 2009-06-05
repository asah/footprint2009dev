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
import private_keys

PRODUCTION_DOMAIN = 'allforgood.org'

PRODUCTION_MAPS_API_KEY = 'ABQIAAAAHtEBbyenR4BaYGl54_p0fRQu5fCZl1K7T-61hQb7PrEsg72lpRQbhbBcd0325oSLzGUQxP7Nz9Rquw'
DEFAULT_MAPS_API_KEY = 'ABQIAAAAHtEBbyenR4BaYGl54_p0fRRlOb26qSyU154aZeLwOrF4C7-DphT-k84KU2QtDbk5G77Rqt1x2njBTQ'

# These are the public Facebook API keys.
DEFAULT_FACEBOOK_KEY = 'df68a40a4a90d4495ed03f920f16c333'
PRODUCTION_FACEBOOK_KEY = '628524bbaf79da8a8a478e5ef49fb84f'

def is_production_site():
  """is this a production instance?"""
  http_host = os.environ.get('HTTP_HOST')
  return (http_host[-len(PRODUCTION_DOMAIN):] == PRODUCTION_DOMAIN)

def is_local_development():
  """is this running on a development server (and not appspot.com)"""
  return (os.environ.get('SERVER_SOFTWARE').find("Development")==0)

def load_standard_template_values(template_values):
  """set template_values[...] for various keys"""
  global DEFAULT_MAPS_API_KEY, DEFAULT_FACEBOOK_KEY
  if not is_production_site():
    # you must install a local_keys.py file and fill it with
    # the keys for your development instance-- it's OK to copy
    # from the global default keys defined in this file, but
    # for example the maps API is unlikely to work since it
    # depends on matching to your server's domain name
    local_keys = __import__('local_keys')
    DEFAULT_MAPS_API_KEY = local_keys.DEFAULT_MAPS_API_KEY
    DEFAULT_FACEBOOK_KEY = local_keys.DEFAULT_FACEBOOK_KEY

  if is_production_site():
    template_values['maps_api_key'] = PRODUCTION_MAPS_API_KEY
    template_values['facebook_key'] = PRODUCTION_FACEBOOK_KEY
  else:
    template_values['maps_api_key'] = DEFAULT_MAPS_API_KEY
    template_values['facebook_key'] = DEFAULT_FACEBOOK_KEY

def get_facebook_key():
  """returns the facebook key"""
  if is_production_site():
    return PRODUCTION_FACEBOOK_KEY
  else:
    return DEFAULT_FACEBOOK_KEY

def get_facebook_secret():
  """returns the facebook secret key"""
  if is_production_site():
    return private_keys.PRODUCTION_FACEBOOK_SECRET
  else:
    return private_keys.DEFAULT_FACEBOOK_SECRET
