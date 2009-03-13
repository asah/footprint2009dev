/**
 * Creates a interval set.
 * The set is stored as an ordered list of intervals. The addInterval operation
 * ensures the intervals do not overlap.
 * @constructor
 */
vol.IntervalSet = function() {
  this.intervals_ = [];
};


/**
 * Adds an interval to this set. Attempts to simplify the set as the new
 * interval is added. Examples:
 * [[0,1], [4,5]] + [2,2] = [[0,2],[4,5]]
 * [[0,1], [4,5]] + [0,5] = [0,5]
 *
 * TODO(oansaldi): since the array is actually sorted, we can use binary search
 *     to find the ideal place to insert the new interval in.
 *
 * @param {number} low the lower bound of the interval (inclusive).
 * @param {number} high the lower bound of the interval (inclusive).
 */
vol.IntervalSet.prototype.addInterval = function(low, high) {
  // TODO(oansaldi): binary search can be used to further improve performance
  for (var i = 0, l = this.intervals_.length; i < l; i++) {
    var interval = this.intervals_[i];
    if (high < interval[0]) {
      // case: [[4,6]] + [1,2] = [[1,2], [4,6]]
      this.intervals_.splice(i, 0, [low, high]);
      return;
    } else if (low < interval[0] && high <= interval[1]) {
      // case: [[2,4]] + [1,2] = [[1,4]]
      interval[0] = low;
      return;
    } else if (low >= interval[0] && high <= interval[1]) {
      // case: [[1,4]] + [2,3] = [[1,4]]
      return;
    } else if (low <= interval[1] && high > interval[1]) {
      // case: [[2,4]] + [3,5] = [[2,5]]
      interval[1] = high;
      // can we merge with next interval?
      if (i + 1 < l) {
        var nextInterval = this.intervals_[i + 1];
        // case: [[2,4], [5,6]] + [3,5] = [[2,6]]
        if (high >= nextInterval[0]) {
          interval[1] = nextInterval[1];
          this.intervals_.splice(i + 1, 1);
        }
      }
      return;
    }
  }
  // case: [[1,2]] + [4,5] = [[1,2], [4,5]]
  this.intervals_.push([low, high]);
};


/**
 * Checks whether the interval set contains the given value.
 * @param {number} value the value.
 * @return {boolean} whether the value is contained.
 */ 
vol.IntervalSet.prototype.contains = function(value) {
  for (var i = 0, l = this.intervals_.length; i < l; i++) {
    var interval = this.intervals_[i];
    if (value >= interval[0] && value <= interval[1]) {
      return true;
    }
  }
  return false;
};


/**
 * Creates a new calendar and attaches it to an element.
 * @param {Element} element the element to attach to.
 * @constructor
 */
vol.Calendar = function(element) {
  this.date_ = new Date();
  this.date_.setDate(1);
  this.events_ = new vol.IntervalSet();
  this.numRows_ = 0;

  // Grab the first <TABLE> inside element.  Assumes that's the calendar table.
  this.table_ = element.getElementsByTagName('table')[0];
  // Grab the first <SELECT> inside element. Assumes that's the period selector.
  this.periodSelector = element.getElementsByTagName('select')[0];
};


vol.Calendar.MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];


/**
 * Display this calendar's next month.
 */
vol.Calendar.prototype.nextMonth = function() {
  this.date_.setMonth(this.date_.getMonth() + 1);
  this.render();
};


/**
 * Display this calendar's previous month.
 */
vol.Calendar.prototype.previousMonth = function() {
  this.date_.setMonth(this.date_.getMonth() - 1);
  this.render();
};


/**
 * Highlights a range of date in the calendar.
 * @param {Date} fromDate start date of the the range (inclusive).
 * @param {Date} toDate end date fo the range (inclusive).
 */
vol.Calendar.prototype.markRange = function(fromDate, toDate) {
  this.events_.addInterval(
    vol.Calendar.copyDatePart(fromDate).getTime(),
    vol.Calendar.copyDatePart(toDate).getTime());
};


/**
 * Remove all highlighted days in the calendar.
 */
vol.Calendar.prototype.clearMarks = function() {
  this.events_ = new vol.IntervalSet();
};


/**
 * Retrieves the currently selected date range.
 * @return {Array.[Date]} an array of two dates representing the start date and
 *     end date of the selected date range.
 */
vol.Calendar.prototype.getDateRange = function() {
  var startDate, endDate;
  switch (this.periodSelector.value) {
    case 'month':
      startDate = vol.Calendar.copyDatePart(this.date_);
      endDate = new Date(startDate.getTime());
      endDate.setMonth(endDate.getMonth() + 1);
      break;
    case 'week':
      startDate = vol.Calendar.copyDatePart(new Date());
      endDate = new Date(startDate.getTime());
      endDate.setDate(endDate.getDate() + 7);
      break;
    case 'weekend':
      startDate = vol.Calendar.copyDatePart(new Date());
      var daysToNextSaturday = 6 - startDate.getDay();
      startDate.setDate(startDate.getDate() + daysToNextSaturday);
      endDate = new Date(startDate.getTime());
      endDate.setDate(endDate.getDate() + 1);
      break;
    case 'today':
      startDate = vol.Calendar.copyDatePart(new Date());
      endDate = startDate;
      break;
  }
  return [startDate, endDate];
};


/**
 * Renders the calendar.
 */
vol.Calendar.prototype.render = function() {
  // sets the title of the calendar
  var month = vol.Calendar.MONTH_NAMES[this.date_.getMonth()]
      + ' ' + this.date_.getFullYear();
  forEachElementOfClass('calendar_month', function(e) {
    e.innerHTML = month;
  }, this.table_);

  // sets the days

  // warning: getDay() returns 0 for Sunday
  var day = vol.Calendar.copyDatePart(this.date_);
  day.setDate(day.getDate() - (day.getDay() + 6) % 7);

  var tbody = this.table_.getElementsByTagName('tbody')[0];

  // Delete last five rows, if present (that is, after changing the
  // current month).
  var numRows = this.table_.rows.length;
  if (numRows >= 6) {
    for (var i = 0; i < 6; i++) {
      this.table_.deleteRow(this.table_.rows.length - 1);
    }
  }

  for (var row = 0; row < 6; row++) {
    var tr = document.createElement('tr');
    tbody.appendChild(tr);
    for (var col = 0; col < 7; col++) {
      var classes = [];
      // days cannot be marked as 'event' and 'weekend' at the same time
      // to avoid multi-class problems with IE.
      if (this.events_.contains(day.getTime())) {
        classes.push('calendar_days_event');
      } else if ((day.getDay() + 6) % 7 > 4) {
        classes.push('calendar_days_weekend');
      }
      if (vol.Calendar.isToday(day)) {
        classes.push('calendar_days_today');
      }
      var td = document.createElement('td');
      if (classes.length > 0) {
        td.className = classes.join(' ');
      }
      tr.appendChild(td);
      td.innerHTML = day.getDate();
      day.setDate(day.getDate() + 1);
    }
  }

  this.table_.style.display = '';
};


/**
 * Checks whether the given date is today (ignoring hours, minutes and seconds).
 * @param {Date} date a date.
 * @return {boolean} whether the given date is today.
 */
vol.Calendar.isToday = function(date) {
  var today = new Date();
  return date.getFullYear() == today.getFullYear()
      && date.getMonth() == today.getMonth()
      && date.getDate() == today.getDate();
};


/**
 * Copies the date part of a date.
 * @param {Date} date a date.
 * @return {Date} a new date whose year, month and day field are copied from the
 *     the argument.
 */
vol.Calendar.copyDatePart = function(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
};
