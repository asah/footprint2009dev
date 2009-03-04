var SITE_ID = '02962301966004179520';
google.friendconnect.container.setParentUrl('/');

google.friendconnect.container.loadOpenSocialApi({site: SITE_ID, onload: function() { checkForViewer(); }});

function checkForViewer() {
  // If the viewer is != null and the userId == null reload page.
  // This is a temporary placeholder until FC gives us an onSignIn callback
  var req = opensocial.newDataRequest();
  req.add(req.newFetchPersonRequest('VIEWER'), 'viewer');
  req.send(setupData);
}

function setupData(data) {
  var viewer = data.get('viewer').getData();
  if (viewer && !document.userId) {
    window.location.reload();
  }
}
