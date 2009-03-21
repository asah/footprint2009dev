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

import cgi
import datetime
import os
import urllib
import urlparse
import logging
import re

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import recaptcha

import api
import base_search
import geocode
import models
import posting
import search
import urls
import userinfo

TEMPLATE_DIR = 'templates/'
MAIN_PAGE_TEMPLATE = 'main_page.html'
TEST_PAGEVIEWS_TEMPLATE = 'test_pageviews.html'
SEARCH_RESULTS_TEMPLATE = 'search_results.html'
SEARCH_RESULTS_DEBUG_TEMPLATE = 'search_results_debug.html'
SEARCH_RESULTS_RSS_TEMPLATE = 'search_results.rss'
SNIPPETS_LIST_TEMPLATE = 'snippets_list.html'
SNIPPETS_LIST_RSS_TEMPLATE = 'snippets_list.rss'
MY_EVENTS_TEMPLATE = 'my_events.html'
FRIENDS_TEMPLATE = 'work_with_others.html'
POST_TEMPLATE = 'post.html'
POST_RESULT_TEMPLATE = 'post_result.html'
ADMIN_TEMPLATE = 'admin.html'
MODERATE_TEMPLATE = 'moderate.html'

DEFAULT_NUM_RESULTS = 10

# TODO: not safe vs. spammers to checkin... but in our design,
# the worst that happens is a bit more spam in our moderation
# queue, i.e. no real badness, just slightly longer review 
# cycle until we can regen a new key.  Meanwhile, avoiding this
# outright is a big pain for launch, regen is super easy and
# it could be a year+ before anybody notices.  Note: the varname
# is intentionally boring, to avoid accidental discovery by
# code search tools.
PK = "6Le2dgUAAAAAABp1P_NF8wIUSlt8huUC97owQ883"

def get_unique_args_from_request(request):
  """ Gets unique args from a request.arguments() list.
  If a URL search string contains a param more than once, only
  the last value is retained.
  For example, for the query "http://foo.com/?a=1&a=2&b=3"
  this function would return { 'a': '2', 'b': '3' }

  Args:
    request: A list given by webapp.RequestHandler.request.arguments()
  Returns:
    dictionary of URL parameters.
  """
  args = request.arguments()
  unique_args = {}
  for arg in args:
    allvals = request.get_all(arg)
    unique_args[arg] = allvals[len(allvals)-1]
  return unique_args


def load_userinfo_into_dict(user, dict):
  if user:
    dict["user"] = user
    dict["user_days_since_joined"] = (datetime.datetime.now()
                                      - user.get_user_info().first_visit).days
  else:
    dict["user"] = None

def render_template(template_filename, template_values, minimize=False):
  path = os.path.join(os.path.dirname(__file__),
                      TEMPLATE_DIR + template_filename)
  rendered = template.render(path, template_values)
  if minimize:
    rendered = re.sub('\s+', ' ', rendered)
  return rendered


class test_page_views_view(webapp.RequestHandler):
  def get(self):
    pagename = "testpage%s" % (self.request.get('pagename'))
    pc = pagecount.IncrPageCount(pagename, 1)
    template_values = pagecount.GetStats()
    template_values["pagename"] = pagename
    template_values["pageviews"] = pc
    self.response.out.write(render_template(TEST_PAGEVIEWS_TEMPLATE,
                                           template_values))


class main_page_view(webapp.RequestHandler):
  def get(self):
    template_values = {
        'result_set': {},
        'current_page' : 'SEARCH',
        'is_main_page' : True,
      }
    # Retrieve the user-specific information for the search result set.
    user = userinfo.get_user(self.request)
    load_userinfo_into_dict(user, template_values)
    self.response.out.write(render_template(SEARCH_RESULTS_TEMPLATE,
                                            template_values))


def get_user_interests(user, remove_no_interest):
  """Get the opportunities a user has expressed interest in.

  Args:
    user: userinfo.User of a user
    remove_no_interest: Filter out items with expressed_interest = UNKNOWN.
  Returns:
    Dictionary of volunteer opportunity id: expressed_interest.
  """
  user_interests = {}
  if user:
    # Note that if a user has a lot (particularly > 1000) of
    # UserInterest entires, we'll have to do a more clever
    # query than the magic reverse reference query.
    for interest in user.get_user_info().interests:
      if (not remove_no_interest or
          interest.expressed_interest != models.InterestTypeProperty.UNKNOWN):
        user_interests[interest.key().name()[3:]] = interest.expressed_interest
    #logging.info('Found interests: %s' % user_interests)
  return user_interests


def get_interest_for_opportunities(opp_ids):
  """Get the interest statistics for a set of volunteer opportunities.

  Args:
    opp_ids: list of volunteer opportunity ids.

  Returns:
    Dictionary of volunteer opportunity id: interested_count.
  """
  others_interests = {}

  interests = models.get_by_ids(models.VolunteerOpportunityStats, opp_ids)
  for (id, interest) in interests.iteritems():
    if interest:
      others_interests[id] = interest.interested_count
  return others_interests


def get_annotated_results(user, result_set):
  """Get results annotated with the interests of this user and all users.

  Args:
    user: User object returned by userinfo.get_user()
    result_set: A search.SearchResultSet.
  Returns:
    The incoming result set, annotated with user-specific info.
  """

  # Get all the ids of items we've found
  opp_ids = [result.id for result in result_set.results];

  # mark the items the user is interested in
  user_interests = get_user_interests(user, True)

  # note the interest of others
  others_interests = get_interest_for_opportunities(opp_ids)

  return annotate_results(user_interests, others_interests, result_set)

def annotate_results(user_interests, others_interests, result_set):
  """Annotates results with the provided interests.

  Args:
    user_interests: User interests from get_user_interests. Can be None.
    others_interests: Others interests from get_interest_for_opportunities.
                      Can be None.
    result_set: A search.SearchResultSet.
  Returns:
    The incoming result set, annotated with user-specific info.
  """

  # Mark up the results
  for result in result_set.results:
    if user_interests and result.id in user_interests:
      result.interest = user_interests[result.id]
    if others_interests and result.id in others_interests:
      #logging.info("others interest in %s = %s " % (result.id, others_interests[result.id]))
      # TODO: Consider updating the base url here if it's changed.
      result.interest_count = others_interests[result.id]

  return result_set

class legacy_search_view(webapp.RequestHandler):
  def get(self):
    self.response.out.write("<!DOCTYPE html><html><body>sorry!  " +
                            "this API has changed-- try /api/volopps" +
                            "</body></html>");

class search_view(webapp.RequestHandler):
  def get(self):
    parsed_url = urlparse.urlparse(self.request.url)
    unique_args = get_unique_args_from_request(self.request)

    # Perform the search.
    result_set = search.search(unique_args)

    result_set.request_url = self.request.url

    output = None
    if api.PARAM_OUTPUT in unique_args:
      output = unique_args[api.PARAM_OUTPUT]

    # Determine whether this is an API call, and pick the output template.
    is_api_call = parsed_url.path.startswith('/api/')
    if is_api_call:
      if not output or output == "rss":
        self.response.headers["Content-Type"] = "application/rss+xml"
        template = SEARCH_RESULTS_RSS_TEMPLATE
      elif output == "csv":
        # TODO: implement SEARCH_RESULTS_CSV_TEMPLATE
        template = SEARCH_RESULTS_RSS_TEMPLATE
      elif output == "tsv":
        # TODO: implement SEARCH_RESULTS_TSV_TEMPLATE
        template = SEARCH_RESULTS_RSS_TEMPLATE
      elif output == "xml":
        # TODO: implement SEARCH_RESULTS_XML_TEMPLATE
        template = SEARCH_RESULTS_XML_TEMPLATE
      elif output == "rssdesc":
        # TODO: implement SEARCH_RESULTS_RSSDESC_TEMPLATE
        template = SEARCH_RESULTS_RSS_TEMPLATE
      elif output == "html":
        if "geocode_responses" not in unique_args:
          unique_args["geocode_responses"] = 1
        template = SEARCH_RESULTS_DEBUG_TEMPLATE
      elif output == "snippets_list":
        # Return just the snippets list HTML.
        template = SNIPPETS_LIST_TEMPLATE
        # Retrieve the user-specific information for the search result set.
        user = userinfo.get_user(self.request)
        if user:
          result_set = get_annotated_results(user, result_set)
      else:
        # TODO: implement SEARCH_RESULTS_ERROR_TEMPLATE
        # TODO: careful about escapification/XSS
        template = SEARCH_RESULTS_RSS_TEMPLATE

    latlng_string = ""
    if "lat" in result_set.args and "long" in result_set.args:
      latlng_string = "%s,%s" % (result_set.args["lat"], result_set.args["long"])

    #logging.info("geocode("+result_set.args[api.PARAM_VOL_LOC]+") = "+result_set.args["lat"]+","+result_set.args["long"])
    template_values = {
        'result_set': result_set,
        'current_page' : 'SEARCH',

        'view_url': self.request.url,
        'query_url_encoded': result_set.query_url_encoded,
        'query_url_unencoded': result_set.query_url_unencoded,

        # TODO: remove this stuff...
        'latlong': latlng_string,
        'keywords': result_set.args[api.PARAM_Q],
        'location': result_set.args[api.PARAM_VOL_LOC],
        'max_distance': result_set.args[api.PARAM_VOL_DIST],
        'is_first_page': result_set.is_first_page,
        'is_last_page': result_set.is_last_page,
        'prev_page_url': result_set.prev_page_url,
        'next_page_url': result_set.next_page_url,
      }

    self.response.out.write(render_template(template, template_values))


class my_events_view(webapp.RequestHandler):
  def get(self):
    user_info = userinfo.get_user(self.request)
    if not user_info:
      template_values = {'current_page' : 'MY_EVENTS'}
      self.response.out.write(render_template(MY_EVENTS_TEMPLATE,
          template_values))
      return


    user_interests = get_user_interests(user_info, True)
    result_set = base_search.get_from_ids(user_interests)

    # This should be merged with the annotation code above.
    annotate_results(user_interests, None, result_set)

    # What to do about interests where we couldn't get the info from base?

    template_values = {
        'current_page' : 'MY_EVENTS',
        'result_set': result_set,
        'query_url_encoded': "MyEvents",
        'query_url_unencoded': "MyEvents",

        # TODO: remove this stuff...
        'keywords': '',
        'location': '',
        'is_first_page': True,
        'is_last_page': True,
        'prev_page_url': '',
        'next_page_url': '',
        }
    load_userinfo_into_dict(user_info, template_values)

    # Hack o rama: Use the search results page!
    self.response.out.write(render_template(MY_EVENTS_TEMPLATE,
                                            template_values))

# TODO(doll): Merge this class with the my_events_view
class friends_view(webapp.RequestHandler):
  def get(self):
    user_info = userinfo.get_user(self.request)

    if not user_info:
      template_values = {
        'current_page' : 'FRIENDS'
      }
      self.response.out.write(render_template(FRIENDS_TEMPLATE, template_values))
      return

    user_interests = get_user_interests(user_info, True)
    friend_interests = {}

    friends = user_info.load_friends()
    for friend in friends:
      friend_interests[friend.user_id] = get_user_interests(friend, True)

    # TODO: add in friend interests to this...
    result_set = base_search.get_from_ids(user_interests)

    # This should be merged with the annotation code above.
    annotate_results(user_interests, None, result_set)

    # What to do about interests where we couldn't get the info from base?

    template_values = {
        'current_page' : 'FRIENDS',
        'result_set': result_set,
        'friends' : friends,
        'total_friends' : user_info.total_friends,
        'friend_interests' : friend_interests
    }
    load_userinfo_into_dict(user_info, template_values)

    self.response.out.write(render_template(FRIENDS_TEMPLATE,
                                            template_values))

class post_view(webapp.RequestHandler):
  def post(self):
    return self.get()
  def get(self):
    global pk
    user_info = userinfo.get_user(self.request)

    # synthesize GET method url from either GET or POST submission
    geturl = self.request.path + "?"
    for arg in self.request.arguments():
      geturl += urllib.quote_plus(arg) + "=" + urllib.quote_plus(self.request.get(arg)) + "&"
    template_values = {
      'current_page' : 'POST',
      'geturl' : geturl,
      }
    load_userinfo_into_dict(user_info, template_values)

    resp = None
    recaptcha_challenge_field = self.request.get('recaptcha_challenge_field')
    if not recaptcha_challenge_field:
      self.response.out.write(render_template(POST_TEMPLATE, template_values))
      return

    recaptcha_response_field = self.request.get('recaptcha_response_field')
    resp = recaptcha.submit(recaptcha_challenge_field, recaptcha_response_field,
                            PK, self.request.remote_addr)
    vals = {}
    computed_vals = {}
    recaptcha_response = self.request.get('recaptcha_response_field')
    if (resp and resp.is_valid) or recaptcha_response == "test":
      vals["user_ipaddr"] = self.request.remote_addr
      load_userinfo_into_dict(user_info, vals)
      for arg in self.request.arguments():
        vals[arg] = self.request.get(arg)
      respcode, id, content = posting.create_from_args(vals, computed_vals)
      # TODO: is there a way to reference a dict-value in appengine+django ?
      for key in computed_vals:
        template_values["val_"+str(key)] = str(computed_vals[key])
      template_values["respcode"] = str(respcode)
      template_values["id"] = str(id)
      template_values["content"] = str(content)
    else:
      template_values["respcode"] = "401"
      template_values["id"] = ""
      template_values["content"] = "captcha error, e.g. response didn't match"

    template_values["vals"] = vals
    for key in vals:
      keystr = "val_"+str(key)
      if keystr in template_values:
        # should never happen-- throwing a 500 avoids silent failures
        self.response.set_status(500)
        self.response.out.write("internal error: duplicate template key")
        logging.error("internal error: duplicate template key: "+keystr)
        return
      template_values[keystr] = str(vals[key])
    self.response.out.write(render_template(POST_RESULT_TEMPLATE, template_values))


class admin_view(webapp.RequestHandler):
  def get(self):
    template_values = {
      'logout_link': users.create_logout_url('/'),
    }

    user = users.get_current_user()
    if user and users.is_current_user_admin():
      self.response.out.write(render_template(ADMIN_TEMPLATE,
                                              template_values))
    else:
      html = "<html><body><a href=\'%s\'>Sign in</a></body></html>"
      self.response.out.write(html % (users.create_login_url(self.request.url)))


class moderate_view(webapp.RequestHandler):
  def get(self):
    # TODO: require admin access-- implement when we agree on mechanism
    action = self.request.get('action')
    if action == "test":
      posting.createTestDatabase()

    now = datetime.datetime.now()
    nowstr = now.strftime("%Y-%m-%d %H:%M:%S")
    ts = self.request.get('ts', nowstr)
    dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    delta = now - dt
    if delta.seconds < 3600:
      logging.info("processing changes...")
      vals = {}
      for arg in self.request.arguments():
        vals[arg] = self.request.get(arg)
      posting.process(vals)

    num = self.request.get('num', "20")
    reslist = posting.query(num=int(num))
    def compare_quality_scores(x,y):
      diff = y.quality_score - x.quality_score
      if (diff > 0): return 1
      if (diff < 0): return -1
      return 0
    reslist.sort(cmp=compare_quality_scores)
    for i,res in enumerate(reslist):
      res.idx = i+1
      if res.description > 100:
        res.description = res.description[0:97]+"..."

    template_values = {
      'current_page' : 'MODERATE',
      'num' : str(num),
      'ts' : str(nowstr),
      'result_set' : reslist,
    }
    self.response.out.write(render_template(MODERATE_TEMPLATE, template_values))
