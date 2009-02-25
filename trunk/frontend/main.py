import cgi

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import views
import urls

application = webapp.WSGIApplication(
                                     [(urls.URL_HOME, views.MainPageView),
                                      (urls.URL_SEARCH, views.SearchView),
                                      (urls.URL_API_SEARCH, views.SearchAPIView),
                                      (urls.URL_FRIENDS, views.FriendsView)],
                                      (urls.URL_MY_EVENTS, views.MyEventsView),
                                      (urls.URL_POST, views.PostView)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
