# Copyright 2009 Google Inc.  All Rights Reserved.
#

import re
import urlparse

from google.appengine.api import memcache


class SearchResult(object):
  def __init__(self, url, title, snippet, location, id, base_url):
    # TODO: Consider using kwargs or something to make this more generic.
    self.url = url
    self.title = title
    self.snippet = snippet
    self.location = location
    self.id = id
    self.base_url = base_url
    # app engine does not currently support the escapejs filter in templates
    # so we have to do it our selves for now
    self.js_escaped_title = self.js_escape(title)
    self.js_escaped_snippet = self.js_escape(snippet)

    parsed_url = urlparse.urlparse(url)
    self.url_short = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)

    # user's expressed interest, models.InterestTypeProperty
    self.interest = None
    # stats from other users.
    self.interest_count = 0
    

  def js_escape(self, string):
    # TODO: This escape method is overly agressive and is messing some snippets
    # up.  We only need to escape single and double quotes.
    return re.escape(string)


class SearchResultSet(object):
  def __init__(self, query_url_unencoded, query_url_encoded, results):
    self.query_url_unencoded = query_url_unencoded
    self.query_url_encoded = query_url_encoded
    self.results = results
