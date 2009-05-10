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
from datetime import datetime
import os
import urllib
import logging
import re

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch

from fastpageviews import pagecount

import recaptcha

import api
import models
import modelutils
import posting
import search
import urls
import userinfo
import view_helper

TEMPLATE_DIR = 'templates/'

HOMEPAGE_TEMPLATE = 'homepage.html'
TEST_PAGEVIEWS_TEMPLATE = 'test_pageviews.html'
SEARCH_RESULTS_TEMPLATE = 'search_results.html'
SEARCH_RESULTS_DEBUG_TEMPLATE = 'search_results_debug.html'
SEARCH_RESULTS_RSS_TEMPLATE = 'search_results.rss'
SEARCH_RESULTS_MISSING_KEY_TEMPLATE = 'search_results_missing_key.html'
SNIPPETS_LIST_TEMPLATE = 'snippets_list.html'
SNIPPETS_LIST_MINI_TEMPLATE = 'snippets_list_mini.html'
SNIPPETS_LIST_RSS_TEMPLATE = 'snippets_list.rss'
MY_EVENTS_TEMPLATE = 'my_events.html'
POST_TEMPLATE = 'post.html'
POST_RESULT_TEMPLATE = 'post_result.html'
ADMIN_TEMPLATE = 'admin.html'
MODERATE_TEMPLATE = 'moderate.html'
STATIC_CONTENT_TEMPLATE = 'static_content.html'

DATAHUB_LOG = \
    "http://google1.osuosl.org/~footprint/datahub/dashboard/load_gbase.log"

DEFAULT_NUM_RESULTS = 10

# Register custom Django templates
template.register_template_library('templatetags.comparisonfilters')
template.register_template_library('templatetags.stringutils')
template.register_template_library('templatetags.dateutils')


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
    userdict["user_days_since_joined"] = (datetime.now() -
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

class home_page_view(webapp.RequestHandler):
  """default homepage for consumer UI."""
  def get(self):
    """HTTP get method."""
    user = userinfo.get_user(self.request)
    template_values = {
      'user' : user,
      'current_page' : 'HOMEPAGE',
    }
    self.response.out.write(render_template(HOMEPAGE_TEMPLATE,
                                           template_values))

class consumer_ui_search_view(webapp.RequestHandler):
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


class search_view(webapp.RequestHandler):
  """run a search.  note various output formats."""
  def get(self):
    """HTTP get method."""
    unique_args = get_unique_args_from_request(self.request)
    
    if "key" not in unique_args:
      tplresult = render_template(SEARCH_RESULTS_MISSING_KEY_TEMPLATE, {})
      self.response.out.write(tplresult)
      pagecount.IncrPageCount("key.missing", 1)
      return
    pagecount.IncrPageCount("key.%s.searches" % unique_args["key"], 1)
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

    result_set.request_url = self.request.url

    # Retrieve the user-specific information for the search result set.
    user = userinfo.get_user(self.request)
    if user:
      result_set = view_helper.get_annotated_results(user, result_set)
      view_data = view_helper.get_my_snippets_view_data(user)
    else:
      view_data = {
        'friends': [],
        'friends_by_event_id_js': '{}',
      }

    template_values = {
        'user' : user,
        'result_set': result_set,
        'current_page' : 'SEARCH',
        'has_results' : (result_set.num_merged_results > 0),  # For django.
        'last_result_index' :
            result_set.clip_start_index + len(result_set.clipped_results),
        'display_nextpage_link' : result_set.has_more_results,
        'view_url': self.request.url,
        'friends' : view_data['friends'],
        'friends_by_event_id_js': view_data['friends_by_event_id_js'],
      }
    # TODO!!!  replace with real admin check when bug #129 is fixed
    template_values['admin_mode'] = (user and user.get_user_info()
                                     and user.get_user_info().moderator)
    if self.request.get('minimal_snippets_list'):
      # Minimal results list for homepage.
      self.response.out.write(render_template(SNIPPETS_LIST_MINI_TEMPLATE,
                                              template_values))
    else:
      self.response.out.write(render_template(SNIPPETS_LIST_TEMPLATE,
                                              template_values))

class ui_my_snippets_view(webapp.RequestHandler):
  """The current spec for the My Events view (also known as "Profile")
  defines the following filters:
  * Filter on my own events
  * Filter on my own + my friends's events
  * Filter on various relative time periods
  * Filter on events that are still open (not past their completion dates)

  Furthermore the UI is spec'd such that each event displays a truncated list
  of friend names, along with a total count of friends.
  
  In order to collect that info, we seem to be stuck with O(n2) because
  I need to know *all* the events that *all* of my friends are interested in:
  1. Get the list of all events that I like or am doing.
  2. Get the list of all my friends.
  3. For each of my friends, get the list of all events that that friend likes
  or is doing.
  4. For each of the events found in step (3), associate the list of all
  interested users with that event.
  """
  def get(self):
    """HTTP get method."""
    unique_args = get_unique_args_from_request(self.request)
    
    user_info = userinfo.get_user(self.request)

    if user_info:
      view_data = view_helper.get_my_snippets_view_data(user_info)
      result_set = view_data['result_set']
      result_set.clipped_results = result_set.results
      template_values = {
          'current_page' : 'MY_EVENTS',
          'view_url': self.request.url,
          'user' : user_info,
          'result_set': result_set,
          'has_results' : view_data['has_results'],
          'friends' : view_data['friends'],
          'friends_by_event_id_js': view_data['friends_by_event_id_js'],
        }
    else:
      template_values = {
          'current_page' : 'MY_EVENTS',
          'view_url': self.request.url,
          'has_results' : False,
      }

    self.response.out.write(render_template(SNIPPETS_LIST_TEMPLATE,
                                            template_values))

class my_events_view(webapp.RequestHandler):
  """Shows events that you and your friends like or are doing."""
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
      'msg': "",
      'action': "",
    }
    
    # TODO!!!  add admin check when bug #129 is fixed
    # (leave open for now, for the dashboard/etc.)

    action = self.request.get('action')
    if not action or action == "":
      action = "mainmenu"
    template_values['action'] = action

    if action == "mainmenu":
      template_values['msg'] = ""
    elif action == "flush_memcache":
      memcache.flush_all()
      template_values['msg'] = "memcached flushed"
    elif action == "blacklist" or action == "unblacklist":
      key = self.request.get('key')
      if not key or key == "":
        self.response.out.write("<html><body>sorry: key required.</body></html>")
        return
      if action == "blacklist":
        if models.BlacklistedVolunteerOpportunity.is_blacklisted(key):
          undel_url = re.sub(r'action=blacklist', 'action=unblacklist',
                             self.request.url)
          html = "<html><body>"
          html += "key "+key+" is already blacklisted."
          html += " click <a href='%s'>here</a> to restore." % undel_url
          html += "</body></html>"
          self.response.out.write(html)
          return
        if self.request.get('areyousure') != "1":
          html = "<html><body>"
          html += "please confirm blacklisting of key "+key+" ?<br/>"
          # TODO: defend against xsrf
          html += "<a href='"+self.request.url+"&areyousure=1'>YES</a> I'm sure."
          html += "</body></html>"
          self.response.out.write(html)
          return
        models.BlacklistedVolunteerOpportunity.blacklist(key)
        if not models.BlacklistedVolunteerOpportunity.is_blacklisted(key):
          template_values['msg'] = "internal failure trying to add"
          template_values['msg'] += " key "+key+" to blacklist."
        else:
          # TODO: better workflow, e.g. email the deleted key to an address
          # along with an url to undelete it?
          undel_url = re.sub(r'action=blacklist', 'action=unblacklist',
                             self.request.url)
          template_values['msg'] = "deleted listing with key "+key+".<br/>"
          template_values['msg'] += "  To undo, click <a href='%s'>here</a>" %\
              undel_url
          template_values['msg'] += " (you may want to save this URL)."
      else:
        models.BlacklistedVolunteerOpportunity.unblacklist(key)
        if models.BlacklistedVolunteerOpportunity.is_blacklisted(key):
          template_values['msg'] = "internal failure trying to remove"
          template_values['msg'] += " key "+key+" from blacklist."
        else:
          template_values['msg'] = "un-deleted listing with key "+key
    elif action == "datahub_dashboard":
      url = self.request.get('datahub_log')
      if not url or url == "":
        url = DATAHUB_LOG
      fetch_result = urlfetch.fetch(url)
      if fetch_result.status_code != 200:
        template_values['msg'] = \
            "error fetching dashboard data: code %d" % fetch_result.status_code
      lines = fetch_result.content.split("\n")      
      # typical line
      # 2009-04-26 18:07:16.295996:STATUS:extraordinaries done parsing: output 
      # 7 organizations and 7 opportunities (13202 bytes): 0 minutes.
      statusrx = re.compile("(\d+-\d+-\d+ \d+:\d+:\d+)[.]\d+:STATUS:(.+?) "+
                            "done parsing: output (\d+) organizations and "+
                            "(\d+) opportunities .(\d+) bytes.: (\d+) minutes")
      def parse_date(datestr):
        """TODO: move to day granularity once we have a few weeks of data.
        At N=10 providers, 5 values, 12 bytes each, 600B per record.
        daily is reasonable for a year, hourly is not."""
        return re.sub(':.+', '', datestr) + ":00"

      js_data = ""
      known_dates = {}
      date_strings = []
      known_providers = {}
      provider_names = []
      for line in lines:
        match = re.search(statusrx, line)
        if match:
          hour = parse_date(match.group(1))
          known_dates[hour] = 0
          known_providers[match.group(2)] = 0
          #js_data += "// hour="+hour+" provider="+match.group(2)+"\n"
      template_values['provider_data'] = provider_data = []
      sorted_providers = sorted(known_providers.keys())
      for i, provider in enumerate(sorted_providers):
        known_providers[provider] = i
        provider_data.append([])
        provider_names.append(provider)
        #js_data += "// provider_names["+str(i)+"]="+provider_names[i]+"\n"
      sorted_dates = sorted(known_dates.keys())
      for i, hour in enumerate(sorted_dates):
        for j, provider in enumerate(sorted_providers):
          provider_data[j].append({})
        known_dates[hour] = i
        date_strings.append(hour)
      #js_data += "// date_strings["+str(i)+"]="+date_strings[i]+"\n"
      for line in lines:
        match = re.search(statusrx, line)
        if match:
          #recordts = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
          hour = parse_date(match.group(1))
          date_idx = known_dates[hour]
          provider = match.group(2)
          provider_idx = known_providers[provider]
          #js_data += "// date_idx="+str(date_idx)
          #js_data += " provider_idx="+str(provider_idx)+"\n"
          rec = provider_data[provider_idx][date_idx]
          rec['organizations'] = match.group(3)
          rec['listings'] = match.group(4)
          rec['bytes'] = match.group(5)
          rec['loadtimes'] = match.group(6)
      js_data += "function sv(row,col,val) {data.setValue(row,col,val);}\n"
      js_data += "function ac(typ,key) {data.addColumn(typ,key);}\n"
      js_data += "function acn(key) {data.addColumn('number',key);}\n"

      js_data += "data = new google.visualization.DataTable();\n"
      js_data += "data.addRows(1);"
      for provider_idx, provider in enumerate(sorted_providers):
        js_data += "acn('"+provider+"');"
        js_data += "sv(0,"+str(provider_idx)+",0);"
      js_data += "\n"
      js_data += "var chart = new google.visualization.ImageSparkLine("
      js_data += "  document.getElementById('provider_names'));\n"
      js_data += "chart.draw(data,{width:150,height:50,showAxisLines:false,"
      js_data += "  showValueLabels:false,labelPosition:'right'});\n"

      for key in ['organizations', 'listings', 'bytes', 'loadtimes']:
        js_data += "data = new google.visualization.DataTable();\n"
        js_data += "data.addRows("+str(len(sorted_dates))+");\n"
        colnum = 0
        for provider_idx, provider in enumerate(sorted_providers):
          try:
            # ignore errors where there's no data for this key
            #js_data += "//acn('str(provider_data["
            #js_data += "str(provider_idx)+"][-1]["+key+"])');\n"
            js_data += "acn('"+str(provider_data[provider_idx][-1][key])+"');"
            #js_data += "acn('"+provider+" "+key
            #js_data += " ("+str(provider_data[provider_idx][-1][key])+")');"
            for date_idx, hour in enumerate(sorted_dates):
              # doesn't work?!
              #if date_idx in provider_data[provider_idx]:
              val = ""
              try:
                rec = provider_data[provider_idx][date_idx]
                val = "sv("+str(date_idx)+","+str(colnum)
                val += ","+rec[key]+");"
              except:
                val = ""
              js_data += val
            colnum += 1
          except:
            # shutup pylint
            js_data += ""
        js_data += "\n"
        js_data += "var chart = new google.visualization.ImageSparkLine("
        js_data += "  document.getElementById('"+key+"_chart'));\n"
        js_data += "chart.draw(data,{width:200,height:50,showAxisLines:false,"
        js_data += "  showValueLabels:false,labelPosition:'right'});\n"
      template_values['datahub_dashboard_js_data'] = js_data

    logging.info("admin_view: "+template_values['msg'])
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

    now = datetime.now()
    nowstr = now.strftime("%Y-%m-%d %H:%M:%S")
    ts = self.request.get('ts', nowstr)
    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
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
      info.last_base_url_update = datetime.now()
      info.base_url_failure_count = 0
      info.put()

    # pylint: disable-msg=W0612
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


class static_content(webapp.RequestHandler):
  """Handles static content like privacy policy and 'About Us'

  The static content files are checked in SVN under /frontend/html.
  We want to be able to update these files without having to push the
  entire website.  The code here fetches the content directly from SVN,
  memcaches it, and serves that.  So once a static content file is
  submitted into SVN, it will go live on the site automatically (as soon
  as memcache entry expires) without requiring a full site push.
  """
  def get(self):
    """HTTP get method."""
    remote_url = (urls.STATIC_CONTENT_LOCATION +
        urls.STATIC_CONTENT_FILES[self.request.path])

    STATIC_CONTENT_MEMCACHE_TIME = 60 * 60  # One hour.
    STATIC_CONTENT_MEMCACHE_KEY = 'static_content:'

    text = memcache.get(STATIC_CONTENT_MEMCACHE_KEY + remote_url)
    if not text:
      result = urlfetch.fetch(remote_url)
      if result.status_code == 200:
        text = result.content
        memcache.set(STATIC_CONTENT_MEMCACHE_KEY + remote_url,
                     text,
                     STATIC_CONTENT_MEMCACHE_TIME)

    if text:
      user = userinfo.get_user(self.request)
      template_values = {
        'user' : user,
        'path' : self.request.path,
        'static_content' : text,
      }
      self.response.out.write(render_template(STATIC_CONTENT_TEMPLATE,
                                              template_values))
    else:
      self.error(404)
