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


function broadcastEvent(div, eventUrl, eventTitle, eventSnippet) {
  opensocial.requestCreateActivity(opensocial.newActivity(
      {title: document.userDisplayName
              + ' shared an event: <a href="' + eventUrl + '">' + eventTitle + '</a>',
        body: eventSnippet}));
  // TODO: This is a hack. We need to figure out the real ui here...
  div.childNodes[1].src="images/broadcasticon-on.png";
  div.setAttribute("onclick", "");
}

function shareEvent(div, eventUrl, eventTitle, eventSnippet) {
  google.friendconnect.requestInvite(document.userDisplayName +
                                     " wants you to check out this event! "
      + eventTitle + " " + eventUrl);
}

function addToCalendar(div, type, eventUrl, eventTitle, eventSnippet,
                       eventDate, eventLocation) {
  // TODO: Handle ical and outlook
  var url;

  if (type == 'GOOGLE') {
    url = "http://www.google.com/calendar/event?action=TEMPLATE"
        + "&text=" + eventTitle
        + "&dates=" + (eventDate + "/" + eventDate)
        + "&details=" + eventSnippet + "+" + eventUrl
        + "&location=" + eventLocation;

  } else if (type == 'YAHOO') {
    url = "http://calendar.yahoo.com?v=60"
        + "&ST=" + eventDate
        + "&TITLE=" + eventTitle
      //+ "&DUR=" + eventDuration TODO: Support duration once we have real dates
        + "&VIEW=d"
        + "&DESC=" + eventSnippet
        + "&in_loc=" + eventLocation;
  }

  window.open(url, 'calendar');
}

function toggleInterest(div, eventUrl, baseUrl) {
  // TODO: First need to check if the user is logged in

  var interest;
  if (div.className == 'snippet_button unstarred') {
    div.className = 'snippet_button starred';
    interest = 1;
  } else {
    div.className = 'snippet_button unstarred';
    interest = 0;
  }


  // TODO: This escaping code is unsafe!
  var path = '/test/interest?i=' + interest
                        + '&oid=' + escape(eventUrl)
                        + '&base_url=' + escape(baseUrl)
                        + '&zx=' + Math.random();

  var xmlHttp = GXmlHttp.create();
  xmlHttp.open('GET', path, true);
  xmlHttp.send(null);
}
