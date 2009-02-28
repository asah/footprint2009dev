google.friendconnect.container.loadOpenSocialApi({site: SITE_ID, onload: function() {}});

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

function expressInterest(div, eventUrl, interest) {
  if (div.interest != undefined) {
    interest = div.interest;
  }
  interest = 0 + interest;
  // hack!
  newinterest = 1;
  if (interest > 0) {
    newinterest = 0;
  }
  div.interest = newinterest;

  // This escaping code is unsafe!
  div.childNodes[1].src='/test/interest?i=' + newinterest
                        + '&oid=' + escape(eventUrl)
                        + '&zx=' + Math.random();
  function fixit() {
    if (newinterest) {
      div.childNodes[1].src='images/markers/red-dot.png';
    } else {
      div.childNodes[1].src='images/markers/red.png';
    }
  }
  window.setTimeout(fixit, 10);
}
