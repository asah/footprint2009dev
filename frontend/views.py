# Copyright 2009 Google Inc.  All Rights Reserved.
#

import cgi
import datetime
import os
import urllib
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

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

DEFAULT_NUM_RESULTS = 10


def RenderTemplate(template_filename, template_values):
  path = os.path.join(os.path.dirname(__file__),
                      TEMPLATE_DIR + template_filename)
  return template.render(path, template_values)


class TestPageViewsView(webapp.RequestHandler):
  def get(self):
    pagename = "testpage%s" % (self.request.get('pagename'))
    pc = pagecount.IncrPageCount(pagename, 1)
    template_values = pagecount.GetStats()
    template_values['pagename'] = pagename
    template_values['pageviews'] = pc
    self.response.out.write(RenderTemplate(TEST_PAGEVIEWS_TEMPLATE,
                                           template_values))

class MainPageView(webapp.RequestHandler):
  def get(self):
    template_values = []
    self.response.out.write(RenderTemplate(MAIN_PAGE_TEMPLATE,
                                           template_values))

def RunSearch(req):
  return result_set

def get_user_interests(user):
  """Get the opportunities a user has expressed interest in.

  Args:
    user: userinfo.User of a user
  Returns:
    Dictionary of volunteer opportunity id: expressed_interest.
  """
  user_interests = {}
  if user:
    # Note that if a user has a lot (particularly > 1000) of
    # UserInterest entires, we'll have to do a more clever
    # query than the magic reverse reference query.
    for interest in user.get_user_info().interests:
      user_interests[interest.key().name()[3:]] = interest.expressed_interest
    #logging.info('Found interests: %s' % user_interests)
  return user_interests

def get_interest_for_opportunities(opp_id):
  """Get the interest statistics for a set of volunteer opportunities.

  Args:
    opp_id: volunteer opportunity id, or list of volunteer opportunity ids.

  Returns:
    Dictionary of volunteer opportunity id: interested_count.
  """
  others_interests = {}
  logging.info("oppids are %s" % opp_ids)
  for interest in models.VolunteerOpportunityStats.get_by_key_name(opp_ids):
    logging.info("interest is %s" % interest)
    if interest:
      others_interests[interest.key().name()[3:]] = interest.interested_count
  return others_interests

def get_annotated_results(search_args):
  """Get results annotated with the interests of this user and all users."""
  result_set = search.Search(search_args)

  # Get all the ids of items we've found
  opp_ids = []
  for result in result_set.results:
    opp_ids.append('id:' + result.id)

  # mark the items the user is interested in
  user_interests = userinfo.get_user()

  # note the interest of others
  others_interests = get_interest_for_opportunities(opp_ids)

  # Mark up the results
  for result in result_set.results:
    if result.id in users_interests:
      result.interest = users_interests[result.id]
    if result.id in others_interests:
      #logging.info("others interest in %s = %s " % (result.id, others_interests[result.id]))
      result.interest_count = others_interests[result.id]

  return result_set

# TODO: legacy consumer UI, to be removed
class SearchView(webapp.RequestHandler):
  def get(self):
    args = self.request.arguments()
    unique_args = {}
    for arg in args:
      allvals = self.request.get_all(arg)
      unique_args[arg] = allvals[len(allvals)-1]

    result_set = get_annotated_results(unique_args)

    template_values = {
        'query_url_encoded': result_set.query_url_encoded,
        'query_url_unencoded': result_set.query_url_unencoded,
        'result_set': result_set,
        'keywords': result_set.args["q"],
        'location': result_set.args["vol_loc"],
        'current_page' : 'SEARCH'
      }
    self.response.out.write(RenderTemplate(SEARCH_RESULTS_TEMPLATE,
                                           template_values))

class SearchAPIView(webapp.RequestHandler):
  def get(self):
    args = self.request.arguments()
    unique_args = {}
    for arg in args:
      allvals = self.request.get_all(arg)
      unique_args[arg] = allvals[len(allvals)-1]
    result_set = get_annotated_results(unique_args)

    user_info = userinfo.get_user()
    user_id = ""
    user_display_name = ""
    if user_info:
      user_id = user_info.user_id
      user_display_name = user_info.get_display_name()

    template_values = {
        'result_set': result_set,
        'currentPage' : 'SEARCH',
        'user_id' : user_id,
        'user_display_name' : user_display_name,

        # TODO: remove this stuff...
        'keywords': result_set.args["q"],
        'location': result_set.args["vol_loc"],
        'is_first_page': result_set.is_first_page,
        'is_last_page': result_set.is_last_page,
        'prev_page_url': result_set.prev_page_url,
        'next_page_url': result_set.next_page_url,
      }

    if "output" not in result_set.args:
      result_set.args["output"] = "html"
    output = result_set.args["output"]
    if output == "consumerui":
      tpl = SEARCH_RESULTS_TEMPLATE
    elif output == "rss":
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    elif output == "csv":
      # TODO: implement SEARCH_RESULTS_CSV_TEMPLATE
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    elif output == "tsv":
      # TODO: implement SEARCH_RESULTS_TSV_TEMPLATE
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    elif output == "xml":
      # TODO: implement SEARCH_RESULTS_XML_TEMPLATE
      tpl = SEARCH_RESULTS_XML_TEMPLATE
    elif output == "rssdesc":
      # TODO: implement SEARCH_RESULTS_RSSDESC_TEMPLATE
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    elif output == "html":
      tpl = SEARCH_RESULTS_DEBUG_TEMPLATE
    else:
      # TODO: implement SEARCH_RESULTS_ERROR_TEMPLATE
      # TODO: careful about escapification/XSS
      template_values["error"] = "no such output format."
      tpl = SEARCH_RESULTS_RSS_TEMPLATE
    self.response.out.write(RenderTemplate(tpl, template_values))

class MyEventsView(webapp.RequestHandler):
  def get(self):
    user_info = userinfo.get_user()
    user_id = ""
    days_since_joined = None
    if user_info:
      #we are logged in
      user_id = user_info.user_id
      display_name = user_info.get_display_name()
      thumbnail_url = user_info.get_thumbnail_url()

      days_since_joined = (datetime.datetime.now() -
                           user_info.get_user_info().first_visit).days

    template_values = {
        'current_page' : 'MY_EVENTS',
        'user_id': user_id,
        'days_since_joined': days_since_joined
      }

    self.response.out.write(RenderTemplate(MY_EVENTS_TEMPLATE,
                                           template_values))

class PostView(webapp.RequestHandler):
  def get(self):
    template_values = {
      'current_page' : 'POST'
    }

    self.response.out.write(RenderTemplate(POST_TEMPLATE, template_values))
