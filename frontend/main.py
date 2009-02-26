import cgi

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import views
import urls

application = webapp.WSGIApplication(
    [(urls.URL_HOME, views.main_page_view),
     (urls.URL_SEARCH, views.search_view),
     (urls.URL_API_SEARCH, views.search_api_view),
     (urls.URL_MY_EVENTS, views.my_events_view),
     (urls.URL_POST, views.post_view)
    ],
    debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
