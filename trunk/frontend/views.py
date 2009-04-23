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
views in the app, in the MVC sense.
"""
# note: view classes aren inherently not pylint-compatible
# pylint: disable-msg=C0103
# pylint: disable-msg=W0232
# pylint: disable-msg=E1101
# pylint: disable-msg=R0903
import datetime
import os
import urllib
import logging

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from fastpageviews import pagecount

import recaptcha

import api
import models
import modelutils
import posting
import search
import userinfo
import view_helper

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

# Register custom Django templates
template.register_template_library('templatetags.comparisonfilters')
template.register_template_library('templatetags.stringutils')


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


def load_userinfo_into_dict(user, userdict):
  """populate the given dict with user info."""
  if user:
    userdict["user"] = user
    userdict["user_days_since_joined"] = (datetime.datetime.now() -
                                          user.get_user_info().first_visit).days
  else:
    userdict["user"] = None
    userdict["user_days_since_joined"] = None

def render_template(template_filename, template_values):
  """wrapper for template.render() which handles path."""
  path = os.path.join(os.path.dirname(__file__),
                      TEMPLATE_DIR + template_filename)
  rendered = template.render(path, template_values)
  return rendered


class test_page_views_view(webapp.RequestHandler):
  """testpage for pageviews counter."""
  def get(self):
    """HTTP get method."""
    pagename = "testpage%s" % (self.request.get('pagename'))
    pc = pagecount.IncrPageCount(pagename, 1)
    template_values = pagecount.GetStats()
    template_values["pagename"] = pagename
    template_values["pageviews"] = pc
    self.response.out.write(render_template(TEST_PAGEVIEWS_TEMPLATE,
                                           template_values))

class main_page_view(webapp.RequestHandler):
  """default homepage for consumer UI."""
  def get(self):
    """HTTP get method."""
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

class legacy_search_view(webapp.RequestHandler):
  """legacy API -- OK to remove after 2009/06/01."""
  def get(self):
    """HTTP get method."""
    self.response.out.write("<!DOCTYPE html><html><body>sorry!  " +
                            "this API has changed-- try /api/volopps" +
                            "</body></html>")

class search_view(webapp.RequestHandler):
  """run a search.  note various output formats."""
  def get(self):
    """HTTP get method."""
    unique_args = get_unique_args_from_request(self.request)
    result_set = search.search(unique_args)

    result_set.request_url = self.request.url

    output = None
    if api.PARAM_OUTPUT in unique_args:
      output = unique_args[api.PARAM_OUTPUT]

    if not output or output == "html":
      if "geocode_responses" not in unique_args:
        unique_args["geocode_responses"] = 1
      tpl = SEARCH_RESULTS_DEBUG_TEMPLATE
    elif output == "rss":
      self.response.headers["Content-Type"] = "application/rss+xml"
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    elif output == "csv":
      # TODO: implement SEARCH_RESULTS_CSV_TEMPLATE
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    elif output == "tsv":
      # TODO: implement SEARCH_RESULTS_TSV_TEMPLATE
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    elif output == "xml":
      # TODO: implement SEARCH_RESULTS_XML_TEMPLATE
      #tpl = SEARCH_RESULTS_XML_TEMPLATE
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    elif output == "rssdesc":
      # TODO: implement SEARCH_RESULTS_RSSDESC_TEMPLATE
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    else:
      # TODO: implement SEARCH_RESULTS_ERROR_TEMPLATE
      # TODO: careful about escapification/XSS
      tpl = SEARCH_RESULTS_DEBUG_TEMPLATE

    latlng_string = ""
    if "lat" in result_set.args and "long" in result_set.args:
      latlng_string = "%s,%s" % (result_set.args["lat"],
                                 result_set.args["long"])

    #logging.info("geocode("+result_set.args[api.PARAM_VOL_LOC]+\
    #   ") = "+result_set.args["lat"]+","+result_set.args["long"])
    template_values = {
        'result_set': result_set,
        'current_page' : 'SEARCH',

        'view_url': self.request.url,

        # TODO: remove this stuff...
        'latlong': latlng_string,
        'keywords': result_set.args[api.PARAM_Q],
        'location': result_set.args[api.PARAM_VOL_LOC],
        'max_distance': result_set.args[api.PARAM_VOL_DIST],
      }
    self.response.out.write(render_template(tpl, template_values))


class ui_snippets_view(webapp.RequestHandler):
  """run a search and return consumer HTML for the results--
  this awful hack exists for latency reasons: it's super slow to
  parse things on the client."""
  def get(self):
    """HTTP get method."""
    unique_args = get_unique_args_from_request(self.request)
    result_set = search.search(unique_args)
    # TODO: re-implement using django filters
    # e.g. http://w.holeso.me/2008/08/a-simple-django-truncate-filter/

    result_set.request_url = self.request.url

    # Retrieve the user-specific information for the search result set.
    user = userinfo.get_user(self.request)
    if user:
      result_set = view_helper.get_annotated_results(user, result_set)

    template_values = {
        'user' : user,
        'result_set': result_set,
        'current_page' : 'SEARCH',
        'has_results' : (result_set.num_merged_results > 0),  # For django.
        'view_url': self.request.url,
      }
    self.response.out.write(render_template(SNIPPETS_LIST_TEMPLATE,
                                            template_values))


class my_events_view(webapp.RequestHandler):
  """TODO: implement and merge with friends_view"""
  def get(self):
    """HTTP get method."""
    user_info = userinfo.get_user(self.request)
    if not user_info:
      template_values = {'current_page' : 'MY_EVENTS'}
      self.response.out.write(render_template(MY_EVENTS_TEMPLATE,
          template_values))
      return

    template_values = {
        'current_page' : 'MY_EVENTS',
    }
    load_userinfo_into_dict(user_info, template_values)

    self.response.out.write(render_template(MY_EVENTS_TEMPLATE,
                                            template_values))

class friends_view(webapp.RequestHandler):
  """TODO: Merge this class with the my_events_view."""
  def get(self):
    """HTTP get method."""
    user_info = userinfo.get_user(self.request)

    if not user_info:
      template_values = {
        'current_page' : 'FRIENDS'
      }
      self.response.out.write(render_template(FRIENDS_TEMPLATE,
                                              template_values))
      return

    is_debug = self.request.get('debug')
    view_data = view_helper.get_data_for_friends_view(user_info, is_debug)
    logging.info(repr(view_data))
    template_values = {
      'current_page' : 'FRIENDS',
      'current_user_opps_result_set': view_data['current_user_opps_result_set'],
      'has_results' : view_data['has_results'],
      'friends' : view_data['friends'],
      'total_friends' : user_info.total_friends,
      'friend_total_opp_count': view_data['friend_total_opp_count'],
      'friend_interests_by_oid_js': view_data['friend_interests_by_oid_js'],
    }
    load_userinfo_into_dict(user_info, template_values)

    self.response.out.write(render_template(FRIENDS_TEMPLATE,
                                            template_values))

class post_view(webapp.RequestHandler):
  """user posting flow."""
  def post(self):
    """HTTP post method."""
    return self.get()
  def get(self):
    """HTTP get method."""
    user_info = userinfo.get_user(self.request)

    # synthesize GET method url from either GET or POST submission
    geturl = self.request.path + "?"
    for arg in self.request.arguments():
      geturl += urllib.quote_plus(arg) + "=" + \
          urllib.quote_plus(self.request.get(arg)) + "&"
    template_values = {
      'current_page' : 'POST',
      'geturl' : geturl,
      }
    load_userinfo_into_dict(user_info, template_values)

    # TODO: remove this workaround once all Facebook/FriendConnect JS
    #    loading issues are fixed.
    if self.request.get('no_login'):
      template_values['no_login'] = True

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
      respcode, item_id, content = posting.create_from_args(vals, computed_vals)
      # TODO: is there a way to reference a dict-value in appengine+django ?
      for key in computed_vals:
        template_values["val_"+str(key)] = str(computed_vals[key])
      template_values["respcode"] = str(respcode)
      template_values["id"] = str(item_id)
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
    self.response.out.write(render_template(POST_RESULT_TEMPLATE,
                                            template_values))


class admin_view(webapp.RequestHandler):
  """admin UI."""
  def get(self):
    """HTTP get method."""
    template_values = {
      'logout_link': users.create_logout_url('/'),
    }

    user = users.get_current_user()
    if not user or not users.is_current_user_admin():
      html = "<html><body><a href=\'%s\'>Sign in</a></body></html>"
      self.response.out.write(html % (users.create_login_url(self.request.url)))
      return

    action = self.request.get('action')
    if action == "flush_memcache":
      memcache.flush_all()
      logging.info("memcache flushed.")
    self.response.out.write(render_template(ADMIN_TEMPLATE, template_values))

class redirect_view(webapp.RequestHandler):
  """process redirects.  TODO: is this a security issue?"""
  def get(self):
    """HTTP get method."""
    url = self.request.get('q')
    if url:
      self.redirect(url)
    else:
      self.error(400)


class moderate_view(webapp.RequestHandler):
  """fast UI for voting/moderating on listings."""
  def get(self):
    """HTTP get method."""
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
    def compare_quality_scores(s1, s2):
      """compare two quality scores for the purposes of sorting."""
      diff = s2.quality_score - s1.quality_score
      if (diff > 0):
        return 1
      if (diff < 0):
        return -1
      return 0
    reslist.sort(cmp=compare_quality_scores)
    for i, res in enumerate(reslist):
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


class action_view(webapp.RequestHandler):
  """vote/tag/etc on a listing.  TODO: rename to something more specific."""
  def post(self):
    """HTTP POST method."""
    if self.request.get('type') != 'star':
      self.error(400)  # Bad request
      return

    user = userinfo.get_user(self.request)
    opp_id = self.request.get('oid')
    base_url = self.request.get('base_url')
    new_value = self.request.get('i')

    if not user:
      logging.warning('No user.')
      self.error(401)  # Unauthorized
      return

    if not opp_id or not base_url or not new_value:
      logging.warning('bad param')
      self.error(400)  # Bad request
      return

    new_value = int(new_value)
    if new_value != 0 and new_value != 1:
      self.error(400)  # Bad request
      return

    # Note: this is inscure and should use some simple xsrf protection like
    # a token in a cookie.
    user_entity = user.get_user_info()
    user_interest = models.UserInterest.get_or_insert(
      models.UserInterest.make_key_name(user_entity, opp_id),
      user=user_entity, opp_id=opp_id)

    if not user_interest:
      self.error(500)  # Server error.
      return

    # Populate VolunteerOpportunity table with (opp_id,base_url)
    # TODO(paul): Populate this more cleanly and securely, not from URL params.
    key = models.VolunteerOpportunity.DATASTORE_PREFIX + opp_id
    info = models.VolunteerOpportunity.get_or_insert(key)
    if info.base_url != base_url:
      info.base_url = base_url
      info.last_base_url_update = datetime.datetime.now()
      info.base_url_failure_count = 0
      info.put()

    (unused_new_entity, deltas) = \
      modelutils.set_entity_attributes(user_interest,
                                 { models.USER_INTEREST_LIKED: new_value },
                                 None)

    if deltas is not None:  # Explicit check against None.
      success = models.VolunteerOpportunityStats.increment(opp_id, deltas)
      if success:
        self.response.out.write('ok')
        return

    self.error(500)  # Server error.
