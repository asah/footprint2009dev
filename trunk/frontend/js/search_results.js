/* Copyright 2009 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

var map;
var NUM_PER_PAGE = 10;
var searchResults = [];

/** Get the IP geolocation given by the Common Ajax Loader.
 * Note: this function caches its own result.
 * @return {string} the current geolocation of the client, if it is known,
 *     otherwise an empty string.
 */
getClientLocation = function() {
  var clientLocationString;
  return function() {
    if (clientLocationString === undefined) {
      try {
        var loc = google.loader.ClientLocation;
        lat = loc.latitude;
        lon = loc.longitude;
        if (lat > 0) {
          lat = '+' + lat;
        }
        if (lon > 0) {
          lon = '+' + lon;
        }
        clientLocationString = lat + lon;

        var address = '';
        if (loc.address.city) {
          address = loc.address.city;
          if (loc.address.region) {
            address += ', ' + loc.address.region;
          }
          el('location').value = address;
        }
      } catch (err) {
        clientLocationString = '';
      }
    }
    return clientLocationString;
  };
}(); // executed inline to close over the 'clientLocationString' variable.


/** Query params for backend search, based on frontend parameters.
 *
 * @constructor
 * @param {string} keywords Search keywords.
 * @param {string|GLatLng} location Location in either string form (address) or
 *      a GLatLng object.
 * @param {number} start The start index for results.  Must be integer.
 * @param {string} timePeriod The time period.
 * @param {Object} opt_filters Filters for this query.
 *      Maps 'filtername':value.
 */
function Query(keywords, location, pageNum, timePeriod, opt_filters) {
  var me = this;
  me.keywords_ = keywords;
  me.location_ = location;
  me.pageNum_ = pageNum;
  me.timePeriod_ = timePeriod;
  me.filters_ = opt_filters || {};
};

Query.prototype.clone = function() {
  var me = this;
  return jQuery.extend(true, new Query(), me);
};

Query.prototype.setPageNum = function(pageNum) {
  this.pageNum_ = pageNum;
};

Query.prototype.getPageNum = function() {
  return this.pageNum_;
};

Query.prototype.getKeywords = function() {
  return this.keywords_;
};

Query.prototype.setKeywords = function(keywords) {
  this.keywords_ = keywords;
};

Query.prototype.getLocation = function() {
  return this.location_;
};

Query.prototype.setLocation = function(location) {
  this.location_ = location;
};

Query.prototype.getTimePeriod = function() {
  return this.timePeriod_;
};

Query.prototype.setTimePeriod = function(period) {
  this.timePeriod_ = period;
};

Query.prototype.getFilter = function(name) {
  if (name in this.filters_) {
    return this.filters_[name];
  } else {
    return undefined;
  }
}

Query.prototype.setFilter = function(name, value) {
  this.filters_[name] = value;
}

Query.prototype.getUrlQuery = function() {
  var me = this;
  urlQuery = '';
  function addQueryParam(name, value) {
    if (urlQuery.length > 0) {
      urlQuery += '&';
    }
    urlQuery += name + '=' + escape(value);
  }

  // Keyword search
  var keywords = me.getKeywords();
  if (keywords && keywords.length > 0) {
    addQueryParam('q', keywords);
  }

  // Pagination
  addQueryParam('num', NUM_PER_PAGE)
  addQueryParam('start', (me.getPageNum() * NUM_PER_PAGE));

  // Location
  var location = me.getLocation();
  if (location && location.length > 0) {
    addQueryParam('vol_loc', location);
  }

  // Time period
  var period = me.getTimePeriod();
  if (period) {
    addQueryParam('timeperiod', period)
  }

  // Add additional filters to query URL.
  for (var name in me.filters_) {
    var value = me.getFilter(name);
    if (value) {
      addQueryParam(name, value);
    }
  }

  return urlQuery;
};

function NewQueryFromUrlParams() {
  var keywords = getHashOrQueryParam('q', '');

  var location = getHashOrQueryParam('vol_loc', getClientLocation());

  var start = Number(getHashOrQueryParam('start', '0'));
  start = Math.max(start, 0);

  var numPerPage = Number(getHashOrQueryParam('num', NUM_PER_PAGE));
  numPerPage = Math.max(numPerPage, 1);

  var pageNum = start / numPerPage;

  var timePeriod = getHashOrQueryParam('timeperiod');

  var filters = {};

  // Read in the other filters from the URL, and place them in
  // 'filters' object.
  function getNamedFilterFromUrl(name) {
    filters[name] = getHashOrQueryParam(name, '');
  }
  getNamedFilterFromUrl('who_filter');
  getNamedFilterFromUrl('activity_filter');

  return new Query(keywords, location, pageNum, timePeriod, filters);
}


/** Perform a search using the current URL parameters and IP geolocation.
 */
function onLoadSearch() {
  executeSearch(NewQueryFromUrlParams());
  executeSearchFromHashParams();
  $(window).hashchange(executeSearchFromHashParams);
}
asyncLoadManager.addCallback('bodyload', onLoadSearch);

/** Updates the location.hash with the given query.
 * @param {Query} query Query parameters.
 */
function executeSearch(query) {
  var urlQueryString = query.getUrlQuery();
  // Set the URL hash, but only if the query string is not empty.
  // Setting hash to an empty string causes a page reload.
  if (urlQueryString.length > 0 && urlQueryString != window.location.hash) {
    window.location.hash = urlQueryString;
  }
}


/** Asynchronously execute a search based on the current parameters.
 */
executeSearchFromHashParams = function() {
  /** The XMLHttpRequest of the current search, kept so it can be cancelled.
   * @type {XMLHttpRequest}
   */
  var currentXhr;

  return function() {
    // abort any currently running query
    if (currentXhr) {
      currentXhr.abort();
    }

    // reset hash params cache since we have a new hash.
    // (no need to refresh GET param cache.)
    hashParams = GetHashParams();

    var query = NewQueryFromUrlParams();
    el('no_results_message').style.display = 'none';
    el('snippets_pane').innerHTML = '<div id="loading">Loading...</div>';

    // TODO: eliminate the need for lastSearchQuery to be global

    var updateMap = false;
    if (!lastSearchQuery ||
        lastSearchQuery.getLocation() != query.getLocation()) {
      updateMap = true;
    }
    lastSearchQuery = query;

    var success = function(text, status) {
      el('keywords').value = query.getKeywords();
      el('timeperiod').value = query.getTimePeriod();
      var regexp = new RegExp('[a-zA-Z]')
      if (regexp.exec(query.getLocation())) {
        // Update location field in UI, but only if location text isn't
        // just a latlon geocode.
        el('location').value = query.getLocation();
      }
      if (updateMap) {
        asyncLoadManager.addCallback('map', function() {
          map.setCenterGeocode(query.getLocation());
        });
      }
      jQuery('#snippets_pane').html(text);
    };

    var error = function (XMLHttpRequest, textStatus, errorThrown) {
      // TODO: handle error
    };

    /* UI snippets URL.  We don't use '/api/search?' because the UI output
       contains application-specific formatting and inline JS, and has
       user-specific info. */
    var url;
    if (currentPageName == 'SEARCH') {
      url = '/ui_snippets?';
    } else if (currentPageName == 'PROFILE') {
      // TODO(Tim)
    }

    currentXhr = jQuery.ajax({
      url: url + query.getUrlQuery(),
      async: true,
      dataType: 'html',
      error: error,
      success: success
    });
  };
}(); // executed inline to close over the 'currentXhr' variable.


/** Called from the "Refine" button's onclick, the main form onsubmit,
 * and the time period filter.
 */
function submitForm() {
  var keywords = el('keywords').value;
  var location = el('location').value;
  var timePeriod = el('timeperiod').value;

  // TODO: strip leading/trailing whitespace.

  if (location == '') {
    location = getClientLocation();
  }

  var query = lastSearchQuery.clone();
  query.setKeywords(keywords);
  query.setLocation(location);
  query.setPageNum(0);
  query.setTimePeriod(timePeriod);
  executeSearch(query);
}


/** Called from the onclick in the "more" prompt of a snippet
 *
 * @param {string} id the element id of the "more", "less" div's
 *
 */
function showMoreDuplicates(id) {
  var it = document.getElementById(id);
  if (it) {
    it.style.display = 'inline';
  }
  it = document.getElementById('s' + id);
  if (it) {
    it.style.display = 'none';
  }
}

/** Called from the onclick in the "less" prompt of a snippet
 *
 * @param {string} id the element id of the "more", "less" div's
 *
 */
function showLessDuplicates(id) {
  var it = document.getElementById(id);
  if (it) {
    it.style.display = 'none';
  }
  it = document.getElementById('s' + id);
  if (it) {
    it.style.display = 'inline';
  }
}

function goToPage(pageNum) {
  if (pageNum < 0) {
    return;
  }
  if (lastSearchQuery) {
    // Change page number, and re-do the last search.
    lastSearchQuery.setPageNum(pageNum);
    executeSearch(lastSearchQuery);
  }
}

function renderPaginator(div, totalNum) {
  if (!lastSearchQuery || searchResults.length == 0 || totalNum == 0) {
    return;
  }

  var numPages = parseInt(Math.ceil(totalNum / NUM_PER_PAGE));
  if (numPages == 1) {
    return;
  }
  if (numPages > 20) {
    numPages = 20;
  }

  var html = [];

  function renderLink(pageNum, text) {
    html.push('<a href="javascript:goToPage(', pageNum, ');void(0);">',
        text, '</a> ');
  }

  var currentPageNum = lastSearchQuery.getPageNum();
  if (currentPageNum > 0) {
    renderLink(currentPageNum - 1, 'Previous');
  }
  for (var i = 0; i < numPages; i++) {
    if (i == currentPageNum) {
      html.push('' + (i+1) + ' ');
    } else {
      renderLink(i, i+1);
    }
  }
  if (currentPageNum != numPages - 1) {
    renderLink(currentPageNum + 1, 'Next');
  }

  div.innerHTML = html.join('');
}


/** Loads the Maps API asynchronously and notifies the asynchronous load
 * manager on completion.
 */
initMap = function() {
  var initialized = false;
  return function() {
    if (!initialized) {
      google.load('maps', '2',
          { 'callback' : function() {
              // Maps API is now loaded.  First initialize
              // the map object, then execute any
              // map-dependent functions that are queued up.
              map = new SimpleMap(el('map'));
              asyncLoadManager.doneLoading('map');
           }});
      initialized = true;
    }
  };
}(); // executed inline to close over the 'initialized' variable.


/** A single search result.
 * @constructor
 * @param {string} url a url.
 * @param {string} title a title.
 * @param {string} location a location.
 * @param {string} snippet a snippet.
 * @param {Date} startdate a start date.
 * @param {Date} enddate an end date.
 */
function SearchResult(url, title, location, snippet, startdate, enddate,
                      itemId, baseUrl, liked) {
  this.url = url;
  this.title = title;
  this.location = location;
  this.snippet = snippet;
  this.startdate = startdate;
  this.enddate = enddate;
  this.itemId = itemId;
  this.baseUrl = baseUrl;
  this.liked = liked;
}

var lastSearchQuery = new Query('', '', 0, {});
