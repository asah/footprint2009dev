vol.Calendar = function(element, events) {
  this.date_ = new Date();
  this.date_.setDate(1);
  this.element_ = element;
  this.events_ = events;
  this.numRows_ = 0;

  // Grab the first <TABLE> inside element.  Assumes that's the calendar table.
  this.table_ = element.getElementsByTagName('table')[0];
};


vol.Calendar.MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];


vol.Calendar.prototype.nextMonth = function() {
  this.date_.setMonth(this.date_.getMonth() + 1);
  this.render();
};


vol.Calendar.prototype.previousMonth = function() {
  this.date_.setMonth(this.date_.getMonth() - 1);
  this.render();
};


vol.Calendar.prototype.render = function() {
  // sets the title of the calendar
  var month = vol.Calendar.MONTH_NAMES[this.date_.getMonth()]
      + ' ' + this.date_.getFullYear();
  forEachElementOfClass('calendar_month', function(e) {
    e.innerHTML = month;
  }, this.element_);

  // sets the days

  // warning: getDay() returns 0 for Sunday
  var day = vol.Calendar.copyDate(this.date_);
  day.setDate(day.getDate() - (day.getDay() + 6) % 7);

  var content = [];

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
      if (vol.Calendar.dateAsString(day) in this.events_) {
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
      } else {
      }
      tr.appendChild(td);
      td.innerHTML = day.getDate();
      day.setDate(day.getDate() + 1);
    }
  }

  this.table_.style.display = '';
};


vol.Calendar.dateAsString = function(date) {
  var str = [date.getFullYear()];

  // note: getMonth is 0 based!
  var m = date.getMonth();
  if (m < 9) {
    str.push('0');
  }
  str.push(m + 1);

  var d = date.getDate();
  if (d < 10) {
    str.push('0');
  }
  str.push(d);
  return str.join('');
};


vol.Calendar.isToday = function(date) {
  var today = new Date();
  return date.getFullYear() == today.getFullYear()
      && date.getMonth() == today.getMonth()
      && date.getDate() == today.getDate();
};


// Does not copy the time part of a javascript Date!
vol.Calendar.copyDate = function(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
};
