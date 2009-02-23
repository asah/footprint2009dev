function el(node) {
  return document.getElementById(node);
}

function GetUrlParams(paramString) {
  // Decode URL hash params.
  var params = {};
  var pairs = paramString.split('&');
  for (var i = 0; i < pairs.length; i++) {
    var p = pairs[i].split('=');
    var paramval = undefined;
    if (p.length > 1) {
      paramval = decodeURIComponent(p[1]);
    }
    params[decodeURIComponent(p[0])] = paramval;
  }
  return params;
}

function GetQueryParams() {
  return GetUrlParams(document.location.search.replace(/(^\?)/,''));
}

function GetHashParams() {
  return GetUrlParams(document.location.hash.replace(/(^#)/,''));
}

/* Queues up a series of JS callbacks, which are executed when execute()
  is called. */
function WorkQueue() {
  this.queue_ = [];
}

WorkQueue.prototype.execute = function() {
  for (var i = 0; i < this.queue_.length; i++) {
    this.queue_[i]();
  }
  // Clear the queue.
  this.queue_ = [];
}

WorkQueue.prototype.addCallback = function(callback) {
  this.queue_.push(callback);
}