# Copyright 2009 Google Inc.  All Rights Reserved.
#

class SearchResult(object):
  def __init__(self, url, title, snippet):
    self.url = url
    self.title = title
    self.snippet = snippet


class SearchResultSet(object):
  def __init__(self, query_url_unencoded, query_url_encoded, results):
    self.query_url_unencoded = query_url_unencoded
    self.query_url_encoded = query_url_encoded
    self.results = results
