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

var isMapsApiInited = false;
var map;
var calendar;
var clientLocationString;
var NUM_PER_PAGE = 10;
var lastSearchQuery;

function initCalendar() {
  var element = el('calendar');
  calendar = new vol.Calendar(element);
  calendar.render();

  function nextMonth() {
    calendar.nextMonth();
    submitForm('calendar');
  }
  function previousMonth() {
    calendar.previousMonth();
    submitForm('calendar');
  }
  function changePeriod() {
    calendar.clearMarks();
    submitForm('calendar');
  }

  forEachElementOfClass('calendar_month_previous', function(e) {
    addListener(e, 'click', previousMonth);
  }, element);
  forEachElementOfClass('calendar_month_next', function(e) {
    addListener(e, 'click', nextMonth);
  }, element);
  addListener(calendar.periodSelector, 'change', changePeriod);

  function unregisterEventListeners() {
    forEachElementOfClass('calendar_month_previous', function(e) {
      removeListener(e, 'click', previousMonth);
    }, element);
    forEachElementOfClass('calendar_month_next', function(e) {
      removeListener(e, 'click', nextMonth);
    }, element);
    removeListener(calendar.periodSelector, 'change', changePeriod);
  }
  onUnloadWorkQueue.addCallback(unregisterEventListeners);
}
asyncLoadManager.addCallback('bodyload', initCalendar);

function mapApiLoadComplete() {
  map = new SimpleMap(el('map'));
}

/** Get the IP geolocation given by the Common Ajax Loader.
 */
function readClientLocation() {
  try {
    lat = google.loader.ClientLocation.latitude;
    lon = google.loader.ClientLocation.longitude;
    if (lat > 0) {
      lat = '+' + lat;
    }
    if (lon > 0) {
      lon = '+' + lon;
    }
    clientLocationString = lat + lon;
  } catch (err) {
    clientLocationString = '';
  }
}

/** Query params for backend search, based on frontend parameters.
 *
 * @constructor
 * @param {string} keywords Search keywords.
 * @param {string|GLatLng} location Location in either string form (address) or
 *      a GLatLng object.
 * @param {number} start The start index for results.  Must be integer.
 * @param {Array.<Date>} dateRange The date range for the search, as a two
 *     element array of dates.
 */
function Query(keywords, location, pageNum, dateRange) {
  var me = this;

  me.keywords_ = keywords;
  me.location_ = location;
  me.pageNum_ = pageNum;
  me.dateRange_ = dateRange;
}

Query.prototype.setPageNum = function(pageNum) {
  this.pageNum_ = pageNum;
}

Query.prototype.getPageNum = function() {
  return this.pageNum_;
}

Query.prototype.getKeywords = function() {
  return this.keywords_;
}

Query.prototype.getLocation = function() {
  return this.location_;
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

  if (me.keywords_ && me.keywords_.length > 0) {
    addQueryParam('q', me.keywords_);
  }

  addQueryParam('num', NUM_PER_PAGE)
  addQueryParam('start', (me.pageNum_ * NUM_PER_PAGE));

  if (me.location_ && me.location_.length > 0) {
    addQueryParam('vol_loc', me.location_);
  }

  if (me.dateRange_ && me.dateRange_.length == 2) {
    addQueryParam('vol_startdate',
                  vol.Calendar.dateAsString(me.dateRange_[0]));
    addQueryParam('vol_enddate',
                  vol.Calendar.dateAsString(me.dateRange_[1]));
  }
  return urlQuery;
}


/** Perform a search using the current URL parameters and IP geolocation.
 */
function onLoadSearch() {
  readClientLocation();

  var q = getHashOrQueryParam('q');
  var location = getHashOrQueryParam('vol_loc');
  if (!location || !location.length) {
    // Not vol_loc param, so use IP geolocation (which defaults to '').
    location = clientLocationString;
  }

  var query = new Query(q, location, 0, calendar.getDateRange());
  doInlineSearch(query, true);
}
asyncLoadManager.addCallback('bodyload', onLoadSearch);

/** Perform an inline search, meaning avoid round trip html fetch.
 * @param {Query} query Query parameters.
 * @param {bool} updateMap Move the map to the new location?
 */
function doInlineSearch(query, updateMap) {
  el('keywords').value = query.getKeywords();

  el('no_results_message').style.display = 'none';
  el('snippets_pane').innerHTML = '<div id="loading">Loading...</div>';

  /* UI snippets URL.  We don't use '/api/search?' because the UI output
     contains application-specific formatting and inline JS, and has
     user-specific info. */
  var url = '/ui_snippets?';

  lastSearchQuery = query;

  var urlQueryString = query.getUrlQuery();

  var callback = function(text) {
    if (updateMap) {
      asyncLoadManager.addCallback('map', function() {
        map.setCenterGeocode(query.getLocation());
      });
    }
    el('snippets_pane').innerHTML = text;

    // Set the URL hash, but only if the query string is not empty.
    // Setting hash to an empty string causes a page reload.
    if (urlQueryString.length > 0) {
      window.location.hash = urlQueryString;
    }

    // Inline scripts inside the html won't be invoked
    // when .innerHTML is set.  Here we iterate through each inline
    // <script> node and execute it directly (by creating a new
    // script node and replacing the old one).
    var scripts = el('snippets_pane').getElementsByTagName('script');
    forEach (scripts, function(script, index) {
        if (index >= 30) {
          // TODO: remove this once we retrieve geocoded search results, and
          // the too-many-search-results bug is fixed.

          // Force rendering of the calendar, since the last <script> won't be
          // executed.
          calendar.render();
          return;
        }
        var newScript = document.createElement('script');
        var scriptText = script.innerHTML;
        if (newScript.text) {
          newScript.text = scriptText;
          script.parentNode.replaceChild(newScript, script);
        } else {
          var textNode = document.createTextNode(scriptText);
          newScript.appendChild(textNode);
          script.parentNode.replaceChild(newScript, script);
        }
    });
  }

  var xmlHttp = window.ActiveXObject ?
      window.ActiveXObject('Microsoft.XMLHTTP') :
      new XMLHttpRequest();
  xmlHttp.open('GET', url + urlQueryString, true);
  xmlHttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      callback(this.responseText);
    }
  };
  xmlHttp.send(null);
}

/** Called from the "Refine" button's onclick, and the main form onsubmit.
 *
 * @param {string} fromWhere One of "map", "calendar" or "keywords", indicating
 *     which input form triggered this search
 */
function submitForm(fromWhere) {
  var keywords = el('keywords').value;
  var location = el('location').value;

  // TODO: strip leading/trailing whitespace.

  if (location == '') {
    location = clientLocationString;
  }

  var updateMap = (fromWhere == "map");
  calendar.clearMarks();
  calendar.render();
  var query = new Query(keywords, location, 0, calendar.getDateRange());
  doInlineSearch(query, updateMap);
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
    doInlineSearch(lastSearchQuery, false);
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

function initMap() {
  if (!isMapsApiInited) {
    google.load('maps', '2',
        { 'callback' : function() {
            // Maps API is now loaded.  First initialize
            // the map object, then execute any
            // map-dependent functions that are queued up.
            mapApiLoadComplete();
            asyncLoadManager.doneLoading('map');
         }});
    isMapsApiInited = true;
  }
}

/**
 * A single search result.
 * @constructor
 * @param {string} url a url.
 * @param {string} title a title.
 * @param {string} location a location.
 * @param {string} snippet a snippet.
 * @param {Date} startdate a start date.
 * @param {Date} enddate an end date.
 */
function SearchResult(url, title, location, snippet, startdate, enddate) {
  this.url = url;
  this.title = title;
  this.location = location;
  this.snippet = snippet;
  this.startdate = startdate;
  this.enddate = enddate;
}
