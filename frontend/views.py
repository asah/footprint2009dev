# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi
import datetime
import os
import urllib
import urlparse
import logging
import posting

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import recaptcha

import base_search
import geocode
import models
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
POST_TEMPLATE = 'post.html'
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


def render_template(template_filename, template_values):
  path = os.path.join(os.path.dirname(__file__),
                      TEMPLATE_DIR + template_filename)
  return template.render(path, template_values)


class test_page_views_view(webapp.RequestHandler):
  def get(self):
    pagename = "testpage%s" % (self.request.get('pagename'))
    pc = pagecount.IncrPageCount(pagename, 1)
    template_values = pagecount.GetStats()
    template_values['pagename'] = pagename
    template_values['pageviews'] = pc
    self.response.out.write(render_template(TEST_PAGEVIEWS_TEMPLATE,
                                           template_values))


class main_page_view(webapp.RequestHandler):
  def get(self):
    result_set = {}

    user_id = None
    user_display_name = None
    user_type = None

    # Retrieve the user-specific information for the search result set.
    user = userinfo.get_user(self.request)
    if user:
      user_id = user.user_id
      user_display_name = user.get_display_name()
      user_type = user.account_type

    template_values = {
        'result_set': result_set,
        'user_id' : user_id,
        'user_display_name' : user_display_name,
        'user_type' : user_type,

        'current_page' : 'SEARCH',
        'is_main_page' : True,
      }
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


class search_view(webapp.RequestHandler):
  def get(self):
    parsed_url = urlparse.urlparse(self.request.url)
    unique_args = get_unique_args_from_request(self.request)

    # Perform the search.
    result_set = search.search(unique_args)

    output = None
    if "output" in unique_args:
      output = unique_args["output"]

    # Determine whether this is an API call, and pick the output template.
    is_api_call = parsed_url.path.startswith('/api/')
    if is_api_call:
      if not output or output == "rss":
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

    #logging.info('%s id:%s name:%s' % (template, user_id, user_display_name))

    latlng_string = ""
    if "lat" in result_set.args and "long" in result_set.args:
      latlng_string = "%s,%s" % (result_set.args["lat"], result_set.args["long"])

    #logging.info("geocode("+result_set.args["vol_loc"]+")="+result_set.args["lat"]+","+result_set.args["long"])
    template_values = {
        'result_set': result_set,
        'current_page' : 'SEARCH',

        'query_url_encoded': result_set.query_url_encoded,
        'query_url_unencoded': result_set.query_url_unencoded,

        # TODO: remove this stuff...
        'latlong': latlng_string,
        'keywords': result_set.args["q"],
        'location': result_set.args["vol_loc"],
        'max_distance': result_set.args["vol_dist"],
        'is_first_page': result_set.is_first_page,
        'is_last_page': result_set.is_last_page,
        'prev_page_url': result_set.prev_page_url,
        'next_page_url': result_set.next_page_url,
      }

    self.response.out.write(render_template(template, template_values))


class my_events_view(webapp.RequestHandler):
  def get(self):
    user_info = userinfo.get_user(self.request)
    user_id = ''
    user_display_name = ''
    if not user_info:
      # TODO: Nice page with login flow!
      self.response.out.write('You are not logged in. Sorry.')
      return

    user_id = user_info.user_id
    user_display_name = user_info.get_display_name()
    user_type = user_info.account_type
    thumbnail_url = user_info.get_thumbnail_url()

    days_since_joined = (datetime.datetime.now() -
                         user_info.get_user_info().first_visit).days

    user_interests = get_user_interests(user_info, True)
    result_set = base_search.get_from_ids(user_interests)

    # This should be merged with the annotation code above.
    annotate_results(user_interests, None, result_set)

    # What to do about interests where we couldn't get the info from base?

    template_values = {
        'current_page' : 'MY_EVENTS',
        'result_set': result_set,
        'user_id' : user_id,
        'user_display_name' : user_display_name,
        'user_type' : user_type,

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

    # Hack o rama: Use the search results page!
    self.response.out.write(render_template(MY_EVENTS_TEMPLATE,
                                            template_values))


class post_view(webapp.RequestHandler):
  def get(self):
    global pk
    user_info = userinfo.get_user(self.request)
    user_id = ''
    user_display_name = ''
    user_type = None
    if user_info:
      #we are logged in
      user_id = user_info.user_id
      user_type = user_info.account_type
      user_display_name = user_info.get_display_name()

    resp = None
    recaptcha_challenge_field = self.request.get('recaptcha_challenge_field')
    if recaptcha_challenge_field:
      user_ipaddr = self.request.remote_addr
      recaptcha_response_field = self.request.get('recaptcha_response_field')
      #self.response.out.write("<html><body>himom</body></html>")
      #return
      resp = recaptcha.submit(recaptcha_challenge_field, recaptcha_response_field,
                              PK, user_ipaddr)

      title = self.request.get('title')
      description = self.request.get("description")
      skills = self.request.get('skills')
      virtual = self.request.get('virtual')
      if virtual == "Yes":
        addr1 = addrname1 = ""
      else:
        addr1 = self.request.get('addr1')
        addrname1 = self.request.get('addrname1')
      sponsoringOrganizationsName = self.request.get('sponsoringOrganizationsName')
      openEnded = self.request.get('openEnded')
      if openEnded == "No":
        startDate = self.request.get('startDate')
        startTime = self.request.get('startTime')
        endTime = self.request.get('endTime')
        endDate = self.request.get('endDate')
      else:
        startTime = endTime = startDate = endDate = ""
        openEnded == "Yes"
      contactNoneNeeded = self.request.get("contactNoneNeeded")
      contactEmail = self.request.get("contactEmail")
      contactPhone = self.request.get("contactPhone")
      contactName = self.request.get("contactName")
      contactURL = self.request.get("contactURL")
      weeklySun = self.request.get("weeklySun") 
      weeklyMon = self.request.get("weeklyMon") 
      weeklyTue = self.request.get("weeklyTue") 
      weeklyWed = self.request.get("weeklyWed") 
      weeklyThu = self.request.get("weeklyThu") 
      weeklyFri = self.request.get("weeklyFri") 
      weeklySat = self.request.get("weeklySat") 
      biweeklySun = self.request.get("biweeklySun") 
      biweeklyMon = self.request.get("biweeklyMon") 
      biweeklyTue = self.request.get("biweeklyTue") 
      biweeklyWed = self.request.get("biweeklyWed") 
      biweeklyThu = self.request.get("biweeklyThu") 
      biweeklyFri = self.request.get("biweeklyFri") 
      biweeklySat = self.request.get("biweeklySat")
      recurrence = self.request.get("recurrence")
      audienceAll = self.request.get("audienceAll")
      audienceMinAge = self.request.get("audienceMinAge")
      audienceTeens = self.request.get("audienceTeens")
      audienceSeniors = self.request.get("audienceSeniors")
      audienceSexRestricted = self.request.get("audienceSexRestricted")
      sexRestrictedTo = self.request.get("sexRestrictedTo")

    if resp == None:
      template_values = {
        'current_page' : 'POST',
        'user_id' : user_id,
        'user_display_name' : user_display_name,
        'user_type' : user_type,
        }
      self.response.out.write(render_template(POST_TEMPLATE, template_values))
      return

    if resp.is_valid:
      #item_xml = ""
      #item_id = posting.create(item_xml)
      html = "<html><body>posting succeeded!</body></html>"
      self.response.out.write(html)
      return

    html = "<html><body>posting failed: "+resp.error_code+"</body></html>"
    self.response.out.write(html)

  def post(self):
    return self.get()



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
    user_info = userinfo.get_user(self.request)
    user_id = ''
    user_display_name = ''
    user_type = None

    if user_info:
      #we are logged in
      user_id = user_info.user_id
      user_type = user_info.account_type
      user_display_name = user_info.get_display_name()

    action = self.request.get('action')
    if action == "test":
      posting.createTestDatabase()

    reslist = posting.query()
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
      'user_id' : user_id,
      'user_display_name' : user_display_name,
      'user_type' : user_type,
      'item_id' : item_id,
      'item_xml' : item_xml,
      'result_set' : reslist,
    }

    self.response.out.write(render_template(MODERATE_TEMPLATE, template_values))
