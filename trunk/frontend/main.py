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
appengine main().
"""


from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import views
import urls

APPLICATION = webapp.WSGIApplication(
    [(urls.URL_HOME, views.home_page_view),
     (urls.URL_CONSUMER_UI_SEARCH, views.consumer_ui_search_view),
     (urls.URL_API_SEARCH, views.search_view),
     (urls.URL_UI_SNIPPETS, views.ui_snippets_view),
     (urls.URL_UI_MY_SNIPPETS, views.ui_my_snippets_view),
     (urls.URL_MY_EVENTS, views.my_events_view),
     (urls.URL_ACTION, views.action_view),
     (urls.URL_ADMIN, views.admin_view),
     (urls.URL_POST, views.post_view),
     (urls.URL_REDIRECT, views.redirect_view),
     (urls.URL_MODERATE, views.moderate_view),
     (urls.URL_MODERATE_BLACKLIST, views.moderate_blacklist_view),
     (urls.URL_DATAHUB_DASHBOARD, views.datahub_dashboard_view),
    ] +
    [ (url, views.static_content) for url in
         urls.STATIC_CONTENT_FILES.iterkeys() ],
    debug=True)

def main():
  """this comment to appease pylint."""
  run_wsgi_app(APPLICATION)

if __name__ == "__main__":
  main()
