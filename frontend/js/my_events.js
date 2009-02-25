google.friendconnect.container.loadOpenSocialApi({site: SITE_ID, onload: function() { initAllData(); }});

function initAllData() {
  // See if the viewer is logged in.
  // Get the owner's friends to display

  // TODO(doll): use the fcauth token to do restful calls with the current user info - right off the bat
  var req = opensocial.newDataRequest();
  req.add(req.newFetchPersonRequest('VIEWER'), 'viewer');
  req.add(req.newFetchPeopleRequest(new opensocial.IdSpec({'userId' : 'OWNER', 'groupId' : 'FRIENDS'})), 'ownerFriends');
  req.add(req.newFetchActivitiesRequest(new opensocial.IdSpec({'userId' : 'OWNER', 'groupId' : 'FRIENDS'})), 'allActivities');
  req.send(setupData);
}

var viewer, ownerFriends, activities;
function setupData(data) {
  ownerFriends = data.get('ownerFriends').getData().asArray();
  var html = "<div class='pane_title'>Active members:</div>";
  for (var i = 0; i < ownerFriends.length; i++) {
    var person = ownerFriends[i];
    var divClass = 'member_row' + (i % 2);
    html += "<div class='" + divClass + "'>";
    html += "<img class='member_photo' src='" + person.getField("thumbnailUrl")  + "'/>";
    html += person.getDisplayName() + "</div>";
  };

  document.getElementById('activeMemberPane').innerHTML = html;

  viewer = data.get('viewer').getData();
  if (viewer) {
    html = "<div class='pane_title'> Your profile:</div>";
    html += "<img class='member_photo' src='" + viewer.getField("thumbnailUrl")  + "'/>";
    html += viewer.getDisplayName() + "<br/><br/>";

    html += "<a href='#' onclick='google.friendconnect.requestSettings()'>Settings</a><br>";
    html += "<a href='#' onclick='google.friendconnect.requestInvite()'>Invite</a><br>";
    html += "<a href='#' onclick='google.friendconnect.requestSignOut(); location.href=\"friends\";'>Sign out</a><br>";

    html += "<b>userId: " + document.fcUserId + "</b>";
    html += "Joined " + document.days_since_joined + " days ago."

    document.getElementById('signInPane').innerHTML = html;
  }

  html = "<div class='pane_title'>All Activity:</div>";

  activities = data.get('allActivities').getData().asArray();
  for (var i in activities) {
    var activity = activities[i];
    html += "<div class='activity'>";
    html += activity.getField('title', {escapeType : 'none'});
    var body = activity.getField('body', {escapeType : 'none'});
    if (body.indexOf('<br /><span class="ot-activity-metadata"') != 0) {
      html += "<div class='activity_body'>" + body + "</div>";
    }
    html += "</div>";
  }

  document.getElementById('activitiesPane').innerHTML = html;
}
