var map;
var workQueue = new WorkQueue();
function init() {
  var queryParams = GetQueryParams();
  if (queryParams['loc']) {
    map = new SimpleMap(el('map'));
    map.setCenterGeocode(queryParams['loc']);
  }

  // Call any queued-up functions that needed to wait for
  // initialization to complete.
  workQueue.execute();
}