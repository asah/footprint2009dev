var map;var clientLocationString;

function initCalendar() {
  var events = {
    '20090228': 'something',
    '20090301': 'something else',
    '20090305': 'one more thing',
    '20090315': 'and one last thing'
  };
  var element = el('calendar');
  var calendar = new vol.Calendar(element, events);
  calendar.render();

  function nextMonth() { calendar.nextMonth(); }
  function previousMonth() { calendar.previousMonth(); }

  forEachElementOfClass('calendar_month_previous', function(e) {
    addListener(e, 'click', previousMonth);
  }, element);
  forEachElementOfClass('calendar_month_next', function(e) {
    addListener(e, 'click', nextMonth);
  }, element);

  function unregisterEventListeners() {
    forEachElementOfClass('calendar_month_previous', function(e) {
      removeListener(e, 'click', previousMonth);
    }, element);
    forEachElementOfClass('calendar_month_next', function(e) {
      removeListener(e, 'click', nextMonth);
    }, element);
  }
  // TODO(oansaldi): cleanup event listeners on unload
  // unloadWorkQueue.addCallback(unregisterEventListeners);
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

/** Perform a search using the current URL parameters and IP geolocation.
 */
function runCurrentSearch() {
  readClientLocation();

  var q = getHashOrQueryParam('q');
  var location = getHashOrQueryParam('vol_loc');
  if (!location || !location.length) {
    // Not vol_loc param, so use IP geolocation (which defaults to '').
    location = clientLocationString;
  }

  doInlineSearch(q, location, '', true);
}
asyncLoadManager.addCallback('bodyload', runCurrentSearch);

/** Perform an inline search, meaning avoid round trip html fetch.
 * @param {string} keywords Search keywords.
 * @param {string|GLatLng} location Location in either string form (address) or
 *      a GLatLng object.
 * @param {string} date Date in string form (TBD).
 * @param {bool} updateMap Move the map to the new location?
 */
function doInlineSearch(keywords, location, date, updateMap) {
  asyncLoadManager.addCallback('map', function() {
    // This code is dependent on MapsAPI being loaded, for GXmlHttp and
    // for setting the map position post-search.

    var xmlHttp = GXmlHttp.create();

    var url = '/api/search?output=snippets_list&';
    var query = '';

    function addQueryParam(name, value) {
      if (query.length > 0) {
        query += '&';
      }
      query += name + '=' + escape(value);
    }

    if (keywords && keywords.length > 0) {
      addQueryParam('q', keywords);
    }
    if (location && location.length > 0) {
      addQueryParam('vol_loc', location);
    }
    var callback = function(text) {
      if (updateMap) {
        map.setCenterGeocode(location);
      }
      el('snippets_pane').innerHTML = text;

      // Set the URL hash, but only if the query string is not empty.
      // Setting hash to an empty string causes a page reload.
      if (query.length > 0) {
        window.location.hash = query;
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

    xmlHttp.open('GET', url + query, true);
    xmlHttp.onreadystatechange = function() {
      if (this.readyState == 4 && this.status == 200) {
        callback(this.responseText);
      }
    }
    xmlHttp.send(null);
  });
}

/** Called from the "Refine" button's onclick, and the main form onsubmit.
 *
 * @param {string} fromWhere One of "map" or "keywords", indicating
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
  doInlineSearch(keywords, location, '', updateMap);
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
