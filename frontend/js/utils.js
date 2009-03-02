function el(node) {
  return document.getElementById(node);
}

function explode(obj) {
  var s = '';
  for (i in obj) {
    s += i + ':' + obj[i] + ' . . . ';
  }
  alert(s);
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

function addListener(element, type, callback) {
  if (element.addEventListener) {
    element.addEventListener(type, callback, false);
  } else if (element.attachEvent) {
    element.attachEvent('on' + type, callback);
  } else {
    element['on' + type] = callback;
  }
}

function removeListener(element, type, callback) {
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
    var decodedName = decodeURIComponent(p[0]);
    if (decodedName.length > 0) {
      if (p.length > 1) {
        paramval = decodeURIComponent(p[1]);
      }
      params[decodedName] = paramval;
    }
  }
  return params;
}

function GetQueryParams() {
  return GetUrlParams(document.location.search.replace(/(^\?)/,''));
}

function GetHashParams() {
  return GetUrlParams(document.location.hash.replace(/(^#)/,''));
}

/** Retrieve a parameter from the URL hashstring or querystring.
 * Hashstring takes precedence.
 * @param {string} paramName Parameter name
 */
function getParam(paramName) {
  if (hashParams[paramName]) {
    return hashParams[paramName];
  } else if (queryParams[paramName]) {
    return queryParams[paramName];
  }
  return null;
}

/** Count number of elements inside a JS object */
function getObjectLength(object) {
  var count = 0;
  for (i in object) {
    count++;
  }
  return count;
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

// Globals
var queryParams = GetQueryParams();
var hashParams = GetHashParams();
