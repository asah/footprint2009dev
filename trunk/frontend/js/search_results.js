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
    addEventListener(e, 'click', previousMonth);
  }, element);
  forEachElementOfClass('calendar_month_next', function(e) {
    addEventListener(e, 'click', nextMonth);
  }, element);
  
  function unregisterEventListeners() {
    forEachElementOfClass('calendar_month_previous', function(e) {
      removeEventListener(e, 'click', previousMonth);
    }, element);
    forEachElementOfClass('calendar_month_next', function(e) {
      removeEventListener(e, 'click', nextMonth);
    }, element);
  }
  // TODO(oansaldi): cleanup event listeners on unload
  // unloadWorkQueue.addCallback(unregisterEventListeners);
});

function mapApiLoadComplete() {
  var queryParams = GetQueryParams();
  if (queryParams['loc']) {
    map = new SimpleMap(el('map'));
    map.setCenterGeocode(queryParams['loc']);
  }

  // Call any queued-up functions that needed to wait for
  // initialization to complete.
  workQueue.execute();
}
