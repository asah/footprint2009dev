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
  var elements;
  if (root.getElementsByClassName) {
    elements = root.getElementsByClassName(classname);
  } else {
    // Dustin Diaz's implementation.
    // http://ejohn.org/blog/getelementsbyclassname-speed-comparison
    var elements = new Array();
    var tag = '*';
    var els = root.getElementsByTagName(tag);
    var elsLen = els.length;
    var pattern = new RegExp("(^|\\s)" + classname + "(\\s|$)");
    for (i = 0; i < elsLen; i++) {
      if (pattern.test(els[i].className)) {
        elements.push(els[i]);
      }
    }
  }
  forEach(elements, fn);
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
function getHashOrQueryParam(paramName) {
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

/**
 * Class to manage the asynchronous loading of components at runtime.
 * When this class is created, give it an array of strings, where
 * each string corresponds to a load eventname.  Register functions for
 * each eventname.  Later, when appropriate, call the function
 * doneLoading(eventName) to trigger each registered function for that
 * eventname.  Now, this is almost exactly like a regular event registration
 * system, except: (1) if a particular load type already occurred
 * BEFORE a function callback is registered, that callback will be
 * triggered immediately; and (2) each load-event is only ever triggered once.
 * The first point above is a reason to use AsyncLoadManager instead of
 * body.onload or the equivalent events in jQuery or other toolkits:
 * this class guarantees that the callback dispatches even if it is
 * registered after the event fires.
 *
 * @param {Array} eventNamesArray Array of strings, the load eventnames.
 **/
function AsyncLoadManager(eventNamesArray) {
  this.callbacks_ = {};
  this.loadStatus_ = {};

  for (var i = 0; i < eventNamesArray.length; i++) {
    var eventName = eventNamesArray[i]
    this.loadStatus_[eventName] = false;
    this.callbacks_[eventName] = new WorkQueue();
  }
}

/** Register a callback for a given load type (eventName).
 * The eventName must have been part of eventNamesArray in the class ctor.
 */
AsyncLoadManager.prototype.addCallback = function(eventName, callback) {
  if ((eventName in this.loadStatus_) && (eventName in this.callbacks_)) {
    if (this.loadStatus_[eventName] == true) {
      // This load event already completed.  Execute the callback immediately.
      callback();
    } else {
      // Load event hasn't yet completed.  Queue it up.
      this.callbacks_[eventName].addCallback(callback);
    }
  }
}

/** Mark a load event as having completed.  This executes all pending
 * callbacks for that event.
 */
AsyncLoadManager.prototype.doneLoading = function(eventName) {
  if ((eventName in this.loadStatus_) && (eventName in this.callbacks_)) {
    if (this.loadStatus_[eventName] == false) {
      this.loadStatus_[eventName] = true;
      this.callbacks_[eventName].execute();
    }
  }
}

// Globals
var queryParams = GetQueryParams();
var hashParams = GetHashParams();
