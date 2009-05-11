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
paths used in the app
"""
URL_HOME = '/'
URL_CONSUMER_UI_SEARCH = '/search'
URL_API_SEARCH = '/api/volopps'
URL_LEGACY_API_SEARCH = '/api/search'
URL_MY_EVENTS = '/myevents'
URL_FRIENDS = '/friends'
URL_POST = '/post'
URL_ADMIN = '/admin'
URL_MODERATE = '/moderate'
URL_UI_SNIPPETS = '/ui_snippets'
URL_UI_MY_SNIPPETS = '/ui_my_snippets'
URL_REDIRECT = '/url'
URL_ACTION = '/action'  # User actions like starring

STATIC_CONTENT_LOCATION = 'http://footprint2009dev.googlecode.com/svn/trunk/frontend/html/'

# Mappings between appliation URLs (key) and static content
# files to fetch (STATIC_CONTENT_LOCATION + value).
# So, for example, the application URL '/about' maps to
# the remote URL 'http://code.google.com/.../trunk/frontend/html/about_us.html'
STATIC_CONTENT_FILES = {
  '/about' : 'about_us.html',
  '/privacypolicy' : 'privacy_policy.html',
  '/publishers' : 'publishers.html',
  '/help' : 'help.html',
  '/faq' : 'faq.html',
}
