/* Copyright 2009 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/


function shareEvent(div, eventUrl, eventTitle, eventSnippet) {
  google.friendconnect.requestInvite(document.userDisplayName +
                                     " wants you to check out this event! "
      + eventTitle + " " + eventUrl);
}

/**
 * Formats a number as two digits. This function performs no range checking on
 * its input.
 * @param {number} n an integer between 0 and 99.
 * @returns {string} a two character long string.
 */
function formatAsTwoDigits(n) {
  return ((n < 10) ? '0' : '') + n;
}

/**
 * Formats a date object into YYYYMMDDTHHmmssZ.
 * @param {Date} date the date to be formatted.
 * @return {string} the formatted date.
 */
function formatDateAsUtc(date) {
  var buffer = [];
  buffer.push(date.getUTCFullYear());
  buffer.push(formatAsTwoDigits(date.getUTCMonth() + 1));
  buffer.push(formatAsTwoDigits(date.getUTCDate()));
  buffer.push('T');
  buffer.push(formatAsTwoDigits(date.getUTCHours()));
  buffer.push(formatAsTwoDigits(date.getUTCMinutes()));
  buffer.push(formatAsTwoDigits(date.getUTCSeconds()));
  buffer.push('Z');
  return buffer.join('');
};

/**
 * Formats a duration for use in the DUR parameter of the Yahoo! Calendar API.
 * @param {number} duration duration in ms.
 * @return {string} the duration, formatted as 'HHmm', for the Yahoo! Calendar
 *     API.
 */
function durationForYahooCalendar(duration) {
  /** Performs an integral division. */
  function div(numerator, denumerator) {
    return numerator / denumerator - numerator % denumerator / denumerator;
  }
  var durationInMinutes = div(duration, 1000*60);
  var durationInHours = div(durationInMinutes, 60);
  if (durationInHours >= 12) {
    // Yahoo! Calendar has issues displaying events longer than 12h.
    // note: this branch won't be executed unless the cap on duration is removed
    //     from addToCalendar.
    return '0030';
  } else {
    return formatAsTwoDigits(durationInHours) +
        formatAsTwoDigits(durationInMinutes % 60);
  }
}


/**
 * Formats a date and duration for use in the dates parameter of the Google
 * Calendar API.
 * @param {Date} startdate the start date of the calendar entry.
 * @param {number} duration the duration of the calendar entry in milliseconds.
 * @return {string} a string ready to be used by the Google Calendar API.
 */
function datesForGoogleCalendar(startdate, duration) {
  var enddate = new Date(startdate.getTime() + duration);
  return formatDateAsUtc(startdate) + "/" + formatDateAsUtc(enddate);
}

function addToCalendar(div, type, searchResult) {
  // TODO: Handle ical and outlook
  var duration = searchResult.enddate.getTime() -
      searchResult.startdate.getTime();
  if (duration > 12*60*60*1000) {
    // For events lasting longer than 12h, we are only interested in the start
    // date. Their length is trimmed to 30 minutes to ensure they remain visible
    // on all calendars. 
    duration = 30*60*1000;
  }
  var url;
  if (type == 'GOOGLE') {
    url = "http://www.google.com/calendar/event?action=TEMPLATE"
        + "&text=" + searchResult.title
        + "&dates=" + datesForGoogleCalendar(searchResult.startdate, duration)
        + "&details=" + searchResult.snippet + "+" + searchResult.url
        + "&location=" + searchResult.location;

  } else if (type == 'YAHOO') {
    url = "http://calendar.yahoo.com?v=60"
        + "&ST=" + formatDateAsUtc(searchResult.startdate)
        + "&TITLE=" + searchResult.title
        + "&DUR=" + durationForYahooCalendar(duration)
        + "&VIEW=d"
        + "&DESC=" + searchResult.snippet
        + "&in_loc=" + searchResult.location;
  }

  window.open(url, 'calendar');
}

function toggleInterest(resultIndex) {
  var result = searchResults[resultIndex];
  var div = el('like_' + resultIndex);

  // TODO: First need to check if the user is logged in
  var newInterest = result.liked ? 0 : 1;

  // TODO: This escaping code is unsafe!
  var path = '/action?type=star' +
                        '&i=' + newInterest +
                        '&oid=' + escape(result.itemId) +
                        '&base_url=' + escape(result.baseUrl) +
                        '&zx=' + Math.random();

  var success = function(data, textStatus) {
    result.liked = newInterest;
    div.style.display = result.liked ? 'none' : '';

    if (result.liked) {
      createLikesActivity(result.title, result.hostWebsite, result.url, result.url_sig);
    }

    updateInterestInfoDisplay(resultIndex);
  };

  var error = function(xhr, textStatus, errorThrown) {
    if (xhr.status == 401) {
      // Unauthorized
      alert("Please log in first");
    } else if (xhr.status == 400) {
    }
  };

  jQuery.ajax({
    type: 'POST',
    url: path,
    async: true,
    dataType: 'text',
    data : {},
    error: error,
    success: success
  });
}

/** Update the div displaying interest info for user and friends, for
 *  a particular search result.
 *  @param {number} resultIndex Index of result in searchResults global array.
 */
function updateInterestInfoDisplay(resultIndex) {
  var result = searchResults[resultIndex];
  var html = '';

  var friends = friendsByEventId[result.itemId] || [];

  if (result.liked || friends.length) {
    html += '<img class="like_icon" src="/images/like.gif">';
    
    var nameList = result.liked ? 'You ' : '';
  
    // Display friends' info, if any.
    if (friends.length) {
      for (var i = 0; i < friends.length; i++) {
        var friendId = friends[i];
        var info = friendsInfo[friendId];
        if (info) {
          if (i == 0) {
            nameList += ', ';
          }
          nameList += info.name;
          if (i < friends.length - 1) {
            nameList += ', ';
          }
        }
      }
    }

    var youAndFriendsCount = (friends ? friends.length : 0) +
        (result.liked ? 1 : 0);
    var strangerInterestCount = result.totalInterestCount - youAndFriendsCount;
    if (strangerInterestCount > 0) {
      nameList += ' and ' + strangerInterestCount + ' more';
    }

    html += nameList;
    html += ' like this (' +
        '<a href="javascript:toggleInterest(' + resultIndex +
        ');void(0);">undo</a>)';  
  }

  var div = el('interest_info_' + resultIndex);
  div.innerHTML = html;
  div.style.display = html.length ? '' : 'none';

}
