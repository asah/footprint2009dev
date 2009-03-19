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

# Various test pages.

import cgi
import datetime
import logging
import os

from google.appengine.ext import db
from google.appengine.api import users
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
                              '<li>Moderator: %s'
                              '<li>Image: %s <img src="%s" />' %
                              (user.account_type,
                               user.user_id,
                               user.get_user_info(),
                               user.get_display_name(),
                               user.get_user_info().moderator,
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


class TestModerator(webapp.RequestHandler):
  def get(self):
    user = userinfo.get_user(self.request)
    if not user:
      self.response.out.write('Not logged in.')
      return

    self.response.out.write('Moderator Request<ul>')

    if user.get_user_info().moderator:
      self.response.out.write('<li>You are already a moderator.')

    if user.get_user_info().moderator_request_email:
      # NOTE: This is very vulnerable to html injection.
      self.response.out.write('<li>We have received your request'
                              '<li>Your email: %s'
                              '<li>Your comments: %s'
                              %
                              (user.get_user_info().moderator_request_email,
                               user.get_user_info().moderator_request_desc))

    self.response.out.write('</ul>')
    self.response.out.write('<form method="POST">'
                            'Your email address: <input name="email" /><br>'
                            'Why you want to be a moderator: <br><textarea name="desc"></textarea>'
                            '<br><input type="submit" name="submit"/>'
                            '</form>')

  def post(self):
    # todo: xsrf protection
    user = userinfo.get_user(self.request)
    if not user:
      self.response.out.write('Not logged in.')
      return

    if not self.request.get('email'):
      # TODO: Actual validation.
      self.response.out.write('<div style="color:red">Email address required.</div>')
    else:
      user_info = user.get_user_info()
      user_info.moderator_request_email = self.request.get('email')
      user_info.moderator_request_desc = self.request.get('desc')
      if not user_info.moderator_request_admin_notes:
        user_info.moderator_request_admin_notes = ''
      user_info.moderator_request_admin_notes += (
          '%s: Requested.\n' %
          datetime.datetime.isoformat(datetime.datetime.now()))
      user_info.put()

    return self.get()


class AdminModerator(webapp.RequestHandler):
  def get(self):
    if not users.is_current_user_admin():
      html = '<html><body><a href="%s">Sign in</a></body></html>'
      self.response.out.write(html % (users.create_login_url(self.request.url)))
      return

    self.response.out.write('<h1>Moderator Management</h1>')

    moderator_query = models.UserInfo.gql('WHERE moderator = TRUE')
    request_query = models.UserInfo.gql('WHERE moderator = FALSE and ' +
                                        'moderator_request_email != \'\'')

    self.response.out.write('<form method="POST">')
    self.response.out.write('Existing moderators<table>')
    self.response.out.write('<tr><td>+</td><td>-</td><td>UID</td><td>Email</td></tr>')
    for moderator in moderator_query:
      # NOTE: This is very vulnerable to html injection.
      self.response.out.write('<tr><td>&nbsp;</td><td>'
          '<input type="checkbox" name="enable" value="%s"></td><td>%s</td>'
          '<td><span title="%s">%s</span></td></tr>' %
          (moderator.key().name(), moderator.key().name(),
           moderator.moderator_request_desc, moderator.moderator_request_email))

    self.response.out.write('</table>Requests<table>')

    self.response.out.write('<tr><td>+</td><td>-</td><td>UID</td><td>Email</td></tr>')
    for request in request_query:
      # NOTE: This is very vulnerable to html injection.
      self.response.out.write('<tr><td>'
          '<input type="checkbox" name="enable" value="%s"></td><td>&nbsp;</td>'
          '<td>%s</td><td><span title="%s">%s</span></td></tr>' %
          (request.key().name(), request.key().name(),
           request.moderator_request_desc, request.moderator_request_email))

    self.response.out.write('</table>'
                            '<input type="submit" />'
                            '</form>')

  def post(self):
    # todo: xsrf protection
    if not users.is_current_user_admin():
      html = '<html><body><a href="%s">Sign in</a></body></html>'
      self.response.out.write(html % (users.create_login_url(self.request.url)))
      return

    keys_to_enable = self.request.POST.getall('enable')
    keys_to_disable = self.request.POST.getall('disable')

    now = datetime.datetime.isoformat(datetime.datetime.now())
    admin = users.get_current_user().email()

    users_to_enable = models.UserInfo.get_by_key_name(keys_to_enable)
    for user in users_to_enable:
      user.moderator = True
      if not user.moderator_request_admin_notes:
        user.moderator_request_admin_notes = ''
      user.moderator_request_admin_notes += '%s: Enabled by %s.\n' % (now, admin)
    db.put(users_to_enable)

    users_to_disable = models.UserInfo.get_by_key_name(keys_to_disable)
    for user in users_to_disable:
      user.moderator = False
      if not user.moderator_request_admin_notes:
        user.moderator_request_admin_notes = ''
      user.moderator_request_admin_notes += '%s: Disabled by %s.\n' % (now, admin)
    db.put(users_to_disable)

    self.response.out.write(
        '<div style="color: green">Enabled %s and disabled %s moderators.</div>' %
        (len(users_to_enable), len(users_to_disable)))
    self.response.out.write('<a href="?zx=%d">Continue</a>' %
                            datetime.datetime.now().microsecond)



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
    opportunity = models.UserInterest.get_or_insert(
        models.UserInterest.DATASTORE_PREFIX + opp_id,
        user=user_entity)

    if opportunity.expressed_interest != expressed_interest:
      opportunity.expressed_interest = expressed_interest
      opportunity.put()
      models.VolunteerOpportunityStats.increment(opp_id,
                                                 interested_count=delta)
      key = models.UserInterest.DATASTORE_PREFIX + opp_id
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
                                      ('/test/moderator', TestModerator),
                                      ('/test/adminmoderator', AdminModerator),
                                      ('/test/interest', ExpressInterest),
                                      ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
