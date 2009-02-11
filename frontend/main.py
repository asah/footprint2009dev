import cgi

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import views

application = webapp.WSGIApplication(
                                     [('/', views.MainPageView),
                                      ('/search', views.SearchView),
                                      ('/friends', views.FriendsView)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
