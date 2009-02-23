# Copyright 2009 Google Inc.  All Rights Reserved.
#

import re

class SearchResult(object):
  def __init__(self, url, title, snippet, location):
    self.url = url
    self.title = title
    self.snippet = snippet
    self.location = location
    # app engine does not currently support the escapejs filter in templates
    # so we have to do it our selves for now
    self.jsEscapedTitle = self.jsEscape(title)
    self.jsEscapedSnippet = self.jsEscape(snippet)

  def jsEscape(self, string):
    # TODO: This escape method is overly agressive and is messing some snippets
    # up.  We only need to escape single and double quotes.
    return re.escape(string)

class SearchResultSet(object):
  def __init__(self, query_url_unencoded, query_url_encoded, results):
    self.query_url_unencoded = query_url_unencoded
    self.query_url_encoded = query_url_encoded
    self.results = results
