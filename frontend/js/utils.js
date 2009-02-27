function el(node) {
  return document.getElementById(node);
}

function forEach(array, fn) {
  var l = array.length;
  for (var i = 0; i < l; i++) {
    fn(array[i], i);
  }
}

function forEachElementOfClass(classname, fn, opt_element) {
  var root = opt_element || document;
  forEach(root.getElementsByClassName(classname), fn);
}

function addEventListener(element, type, callback) {
  if (element.addEventListener) {
    element.addEventListener(type, callback, false);
  } else if (element.attachEvent) {
    element.attachEvent('on' + type, callback);
  } else {
    element['on' + type] = callback;
  }
}

function removeEventListener(element, type, callback) {
  if (element.removeEventListener) {
    element.removeEventListener(type, callback, false);
  } else if (element.detachEvent) {
    element.detachEvent('on' + type, callback);
  } else {
    element['on' + type] = callback;
  }
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