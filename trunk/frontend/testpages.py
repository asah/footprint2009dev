# Various test pages.

import cgi
import datetime
import logging
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import models
import userinfo

class TestLogin(webapp.RequestHandler):
  def get(self):
    user = userinfo.get_user(self.request)
    self.response.out.write('Login info<ul>')
    if user:
      self.response.out.write('<li>Account type: %s'
                              '<li>User_id: %s'
                              '<li>User_info:  %s'
                              '<li>Name: %s'
                              '<li>Image: %s <img src="%s" />' %
                              (user.account_type,
                               user.user_id,
                               user.user_info,
                               user.get_display_name(),
                               user.get_thumbnail_url(),
                               user.get_thumbnail_url()))
    else:
      self.response.out.write('<li>Not logged in.')

    self.response.out.write('<li>Total # of users: %s' %
                            models.UserStats.get_count())

    self.response.out.write('</ul>')
    self.response.out.write('<form method="POST">'
                            'Userid: <input name="userid" />'
                            '<input name="Test Login" type="submit" />'
                            '(Blank form = logout)'
                            '</form>')

  def post(self):
    userid = self.request.get('userid')
    self.response.headers.add_header('Set-Cookie', 'footprinttest=%s;path=/' % userid)
    self.response.out.write('You are logged ')
    if userid:
      self.response.out.write('in!')
    else:
      self.response.out.write('out!')
    self.response.out.write('<br><a href="%s">Continue</a>' % self.request.url)


class ExpressInterest(webapp.RequestHandler):
  def get(self):
    user = userinfo.get_user(self.request)
    opp_id = self.request.get('oid')
    base_url = self.request.get('base_url')
    if self.request.get('i') and self.request.get('i') != '0':
      expressed_interest = models.InterestTypeProperty.INTERESTED
      delta = 1
    else:
      # OK, we probably should add a new 'not interested' value to the enum.
      expressed_interest = models.InterestTypeProperty.UNKNOWN
      delta = -1

    if not user or not opp_id:
      logging.warning('No user or no opp_id.')
      # todo: set responsecode=400
      return

    # Note: this is inscure and should use some simple xsrf protection like
    # a token in a cookie.
    user_entity = user.get_user_info()
    opportunity = models.UserInterest.get_or_insert('id:' + opp_id,
                                                    user=user_entity)

    if opportunity.expressed_interest != expressed_interest:
      opportunity.expressed_interest = expressed_interest
      opportunity.put()
      models.VolunteerOpportunityStats.increment(opp_id,
                                                 interested_count=delta)
      key = 'id:' + opp_id
      info = models.VolunteerOpportunity.get_or_insert(key)
      if info.base_url != base_url:
        info.base_url = base_url
        info.last_base_url_update = datetime.datetime.now()
        info.base_url_failure_count = 0
        info.put()
      logging.info('User %s has changed interest (%s) in %s' %
                 (user_entity.key().name(), expressed_interest, opp_id))
    else:
      logging.info('User %s has not changed interest (%s) in %s' %
                 (user_entity.key().name(), expressed_interest, opp_id))

    # TODO: Write something useful to the http output




application = webapp.WSGIApplication(
                                     [('/test/login', TestLogin),
                                      ('/test/interest', ExpressInterest),
                                      ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
