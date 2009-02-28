var map;
var workQueue = new WorkQueue();

workQueue.addCallback(function() {
  var events = {
    '20090228': 'something',
    '20090301': 'something else',
    '20090305': 'one more thing',
    '20090315': 'and one last thing'
  };
  var element = el('calendar');
  var calendar = new footprint.Calendar(element, events);
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
});

function mapApiLoadComplete() {
  map = new SimpleMap(el('map'));
  if (queryParams['vol_loc']) {
    map.setCenterGeocode(queryParams['vol_loc']);
  }

  // Call any queued-up functions that needed to wait for
  // initialization to complete.
  workQueue.execute();

  if (getObjectLength(hashParams) == 0 && getObjectLength(queryParams) == 0) {
    // Page wasn't given any search params.
    doInlineSearch('', '', '', false);
  }
}

/** Perform an inline search, meaning avoid round trip html fetch.
 * @param {string} keywords Search keywords.
 * @param {string|GLatLng} location Location in either string form (address) or
 *      a GLatLng object.
 * @param {string} date Date in string form (TBD).
 * @param {bool} updateMap Move the map to the new location?
 */
function doInlineSearch(keywords, location, date, updateMap) {
  var xmlHttp = GXmlHttp.create();

  var url = '/search?output=snippets_list';

  if (keywords && keywords.length > 0) {
    url += '&q=' + escape(keywords);
  }
  if (location && location.length > 0) {
    url += '&vol_loc=' + escape(location);
    if (updateMap) {
      map.setCenterGeocode(location);
    }
  }
  xmlHttp.open('GET', url, true);

  xmlHttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      el('snippets_pane').innerHTML = this.responseText;
    }
  }
  xmlHttp.send(null);
}

/** Called from the "Refine" button's onclick, and the main form onsubmit.
 *
 * @param {string} fromWhere One of "map" or "keywords", indicating
 *     which input form triggered this search
 */
function submitForm(fromWhere) {
  var keywords = el('keywords').value;
  var location = el('location').value;

  var updateMap = (fromWhere == "map");
  doInlineSearch(keywords, location, '', updateMap);
}
